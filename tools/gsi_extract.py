#!/usr/bin/env python3
"""Bounded GSI payload extraction/normalization. Never expands archive paths."""
import argparse, gzip, hashlib, json, lzma, pathlib, shutil, subprocess, sys, tarfile, zipfile
try:
 from .gsi_prepare import choose, fs_type
except ImportError:
 from gsi_prepare import choose, fs_type

MAX_BYTES=8*1024**3
MAX_STEPS=10

def sha256(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
 return h.hexdigest()

def bounded_copy(src,dst,limit=MAX_BYTES):
 total=0
 with open(src,'rb') as i,open(dst,'wb') as o:
  while True:
   b=i.read(1024*1024)
   if not b:break
   total+=len(b)
   if total>limit:raise ValueError('payload exceeds extraction size limit')
   o.write(b)

def archive_member(src,dst):
 if zipfile.is_zipfile(src):
  with zipfile.ZipFile(src) as z:
   infos=[x for x in z.infolist() if not x.is_dir()]
   name=choose([x.filename for x in infos])
   matches=[x for x in infos if x.filename==name]
   if len(matches)!=1:raise ValueError('ambiguous or duplicate archive member')
   info=matches[0]
   if info.file_size>MAX_BYTES:raise ValueError('archive member exceeds size limit')
   with z.open(info) as i,open(dst,'wb') as o:
    total=0
    while True:
     b=i.read(1024*1024)
     if not b:break
     total+=len(b)
     if total>MAX_BYTES:raise ValueError('payload exceeds extraction size limit')
     o.write(b)
   return name
 if tarfile.is_tarfile(src):
  with tarfile.open(src,'r:*') as t:
   infos=[m for m in t.getmembers() if m.isfile()]
   name=choose([m.name for m in infos])
   matches=[m for m in infos if m.name==name]
   if len(matches)!=1:raise ValueError('ambiguous archive member')
   m=matches[0]
   if m.size>MAX_BYTES:raise ValueError('archive member exceeds size limit')
   i=t.extractfile(m)
   if i is None:raise ValueError('cannot read selected member')
   total=0
   with i,open(dst,'wb') as o:
    while True:
     b=i.read(1024*1024)
     if not b:break
     total+=len(b)
     if total>MAX_BYTES:raise ValueError('payload exceeds extraction size limit')
     o.write(b)
   return name
 raise ValueError('supported archives: ZIP and TAR; other input treated as raw payload')

def normalize(src,outdir):
 src=pathlib.Path(src).resolve();outdir=pathlib.Path(outdir).resolve()
 if not src.is_file():raise ValueError('input is not a file')
 outdir.mkdir(parents=True,exist_ok=True)
 work=outdir/'.work'
 shutil.rmtree(work,ignore_errors=True);work.mkdir()
 current=work/'payload'; member=None;steps=[]
 try:
  if zipfile.is_zipfile(src) or tarfile.is_tarfile(src):member=archive_member(src,current)
  else:bounded_copy(src,current)
  for idx in range(MAX_STEPS):
   with current.open('rb') as f:h=f.read(8)
   nxt=work/f'normalized_{idx}'
   if h.startswith(b'\\xfd7zXZ\\x00'):
    op=lzma.open(current,'rb')
    label='xz'
   elif h.startswith(b'\\x1f\\x8b'):
    op=gzip.open(current,'rb');label='gzip'
   elif h[:4]==bytes.fromhex('3aff26ed'):
    if not shutil.which('simg2img'):raise RuntimeError('simg2img unavailable')
    subprocess.run(['simg2img',str(current),str(nxt)],check=True);steps.append('sparse_to_raw');current=nxt;continue
   elif h[:4]==bytes.fromhex('04224d18'):
    if not shutil.which('lz4'):raise RuntimeError('lz4 unavailable')
    subprocess.run(['lz4','-d','-f',str(current),str(nxt)],check=True);steps.append('lz4');current=nxt;continue
   else:break
   total=0
   with op, nxt.open('wb') as o:
    while True:
     b=op.read(1024*1024)
     if not b:break
     total+=len(b)
     if total>MAX_BYTES:raise ValueError('decompressed payload exceeds size limit')
     o.write(b)
   steps.append(label);current=nxt
  else:raise ValueError('normalization exceeded maximum transformation count')
  final=outdir/'system.img';bounded_copy(current,final)
  report={'source':str(src),'source_sha256':sha256(src),'selected_member':member,'transformations':steps,'output':str(final),'output_sha256':sha256(final),'filesystem_hint':fs_type(final),'extraction':'normalized_payload_only','filesystem_contents_extracted':False,'compatibility':'not_assessed','boot_test':'not_performed','size_limit_bytes':MAX_BYTES}
  (outdir/'extract-report.json').write_text(json.dumps(report,indent=2)+'\n')
  return report
 finally:shutil.rmtree(work,ignore_errors=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('output_dir');a=p.parse_args()
 try:print(json.dumps(normalize(a.input,a.output_dir),indent=2))
 except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
