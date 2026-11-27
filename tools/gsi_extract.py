#!/usr/bin/env python3
"""Bounded GSI payload extraction/normalization. Never expands archive paths."""
import argparse, gzip, hashlib, json, lzma, pathlib, shutil, subprocess, sys, tarfile, tempfile, zipfile
try:
 from .gsi_prepare import choose, fs_type
except ImportError:
 from gsi_prepare import choose, fs_type
MAX_BYTES=8*1024**3
MAX_STEPS=10
def sha256(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def copy_stream_bounded(src,dst,limit=MAX_BYTES):
 total=0
 with open(dst,'wb') as o:
  while True:
   b=src.read(1024*1024)
   if not b:break
   total+=len(b)
   if total>limit:raise ValueError('payload exceeds extraction size limit')
   o.write(b)
 return total
def bounded_copy(src,dst,limit=MAX_BYTES):
 with open(src,'rb') as i:return copy_stream_bounded(i,dst,limit)
def archive_member(src,dst):
 if zipfile.is_zipfile(src):
  with zipfile.ZipFile(src) as z:
   infos=[x for x in z.infolist() if not x.is_dir()];name=choose([x.filename for x in infos])
   matches=[x for x in infos if x.filename==name]
   if len(matches)!=1:raise ValueError('ambiguous or duplicate archive member')
   info=matches[0]
   if info.file_size>MAX_BYTES:raise ValueError('archive member exceeds size limit')
   with z.open(info) as i:copy_stream_bounded(i,dst)
   return name
 if tarfile.is_tarfile(src):
  with tarfile.open(src,'r:*') as t:
   infos=[m for m in t.getmembers() if m.isfile()];name=choose([m.name for m in infos])
   matches=[m for m in infos if m.name==name]
   if len(matches)!=1:raise ValueError('ambiguous or duplicate archive member')
   m=matches[0]
   if m.size>MAX_BYTES:raise ValueError('archive member exceeds size limit')
   i=t.extractfile(m)
   if i is None:raise ValueError('cannot read selected member')
   with i:copy_stream_bounded(i,dst)
   return name
 raise ValueError('unsupported archive')
def run_bounded(cmd,dst,limit=MAX_BYTES):
 p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
 try:
  with open(dst,'wb') as out:
   total=0
   while True:
    b=p.stdout.read(1024*1024)
    if not b:break
    total+=len(b)
    if total>limit:raise ValueError('payload exceeds extraction size limit')
    out.write(b)
  err=p.stderr.read();rc=p.wait()
  if rc:raise RuntimeError(cmd[0]+' failed: '+err.decode(errors='replace')[-2000:])
 except Exception:
  p.kill();p.wait();pathlib.Path(dst).unlink(missing_ok=True);raise
def sparse_size(p):
 with open(p,'rb') as f:h=f.read(28)
 if len(h)<28 or h[:4]!=bytes.fromhex('3aff26ed'):return None
 size=int.from_bytes(h[12:16],'little')*int.from_bytes(h[16:20],'little')
 if size>MAX_BYTES:raise ValueError('sparse image declared expanded size exceeds limit')
 return size
def normalize(src,outdir):
 src=pathlib.Path(src).resolve();outdir=pathlib.Path(outdir).resolve()
 if not src.is_file():raise ValueError('input is not a file')
 if outdir==src or src in outdir.parents:raise ValueError('output directory must not contain input')
 outdir.mkdir(parents=True,exist_ok=True);final=outdir/'system.img';report_path=outdir/'extract-report.json'
 work=pathlib.Path(tempfile.mkdtemp(prefix='.gsi-extract-',dir=outdir));current=work/'payload';member=None;steps=[]
 try:
  if zipfile.is_zipfile(src) or tarfile.is_tarfile(src):member=archive_member(src,current)
  else:bounded_copy(src,current)
  for idx in range(MAX_STEPS):
   with current.open('rb') as f:h=f.read(8)
   nxt=work/f'normalized_{idx}'
   if h.startswith(b'\xfd7zXZ\x00'):
    with lzma.open(current,'rb') as op:copy_stream_bounded(op,nxt)
    label='xz'
   elif h.startswith(b'\x1f\x8b'):
    with gzip.open(current,'rb') as op:copy_stream_bounded(op,nxt)
    label='gzip'
   elif h[:4]==bytes.fromhex('3aff26ed'):
    sparse_size(current)
    if not shutil.which('simg2img'):raise RuntimeError('simg2img unavailable')
    run_bounded(['simg2img',str(current),str(nxt)])
    label='sparse_to_raw'
   elif h[:4]==bytes.fromhex('04224d18'):
    if not shutil.which('lz4'):raise RuntimeError('lz4 unavailable')
    run_bounded(['lz4','-d','-f',str(current),str(nxt)])
    label='lz4'
   else:break
   if nxt.stat().st_size>MAX_BYTES:raise ValueError('payload exceeds extraction size limit')
   steps.append(label);current=nxt
  else:raise ValueError('normalization exceeded maximum transformation count')
  staged=work/'system.img';bounded_copy(current,staged)
  report={'source':str(src),'source_sha256':sha256(src),'selected_member':member,'transformations':steps,'output':str(final),'output_sha256':sha256(staged),'filesystem_hint':fs_type(staged),'extraction':'normalized_payload_only','filesystem_contents_extracted':False,'compatibility':'not_assessed','boot_test':'not_performed','size_limit_bytes':MAX_BYTES}
  staged.replace(final);tmpreport=work/'report.json';tmpreport.write_text(json.dumps(report,indent=2)+'\n');tmpreport.replace(report_path)
  return report
 finally:shutil.rmtree(work,ignore_errors=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('output_dir');a=p.parse_args()
 try:print(json.dumps(normalize(a.input,a.output_dir),indent=2))
 except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
