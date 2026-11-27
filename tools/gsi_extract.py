#!/usr/bin/env python3
"""Safe, evidence-oriented GSI payload extraction and normalization.

Only extracts one selected system-image payload from an archive; never expands
archive paths onto disk. Decompression/conversion is bounded by iteration count,
and the original input is never modified.
"""
import argparse, gzip, hashlib, json, lzma, pathlib, shutil, subprocess, sys, tarfile, zipfile

try:\n from .gsi_prepare import choose, fs_type\nexcept ImportError:\n from gsi_prepare import choose, fs_type

def sha256(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
 return h.hexdigest()

def archive_member(src, dst):
 if zipfile.is_zipfile(src):
  with zipfile.ZipFile(src) as z:
   name=choose(z.namelist())
   if not name: raise ValueError('archive contains no files')
   with z.open(name) as i, open(dst,'wb') as o: shutil.copyfileobj(i,o)
   return name
 if tarfile.is_tarfile(src):
  with tarfile.open(src,'r:*') as t:
   files=[m.name for m in t.getmembers() if m.isfile()]
   name=choose(files)
   if not name: raise ValueError('archive contains no regular files')
   m=t.getmember(name)
   with t.extractfile(m) as i, open(dst,'wb') as o: shutil.copyfileobj(i,o)
   return name
 if shutil.which('7z'):
  test=subprocess.run(['7z','t',str(src)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  if test.returncode==0:
   listing=subprocess.run(['7z','l','-slt',str(src)],capture_output=True,text=True,check=True).stdout
   names=[line[7:] for line in listing.splitlines() if line.startswith('Path = ')][1:]
   name=choose(names)
   if not name: raise ValueError('archive contains no files')
   subprocess.run(['7z','e','-y',str(src),name,'-o'+str(pathlib.Path(dst).parent)],check=True,stdout=subprocess.DEVNULL)
   extracted=pathlib.Path(dst).parent/pathlib.Path(name).name
   if extracted!=pathlib.Path(dst): extracted.replace(dst)
   return name
 raise ValueError('unsupported archive type')

def normalize(src, outdir):
 src=pathlib.Path(src).resolve(); outdir=pathlib.Path(outdir).resolve()
 outdir.mkdir(parents=True,exist_ok=True)
 work=outdir/'.work'; shutil.rmtree(work,ignore_errors=True); work.mkdir()
 current=work/'payload'
 kind=None; member=None
 if zipfile.is_zipfile(src) or tarfile.is_tarfile(src) or (shutil.which('7z') and subprocess.run(['7z','t',str(src)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0):
  member=archive_member(src,current); kind='archive_member'
 else: shutil.copyfile(src,current)
 steps=[]
 for idx in range(10):
  with current.open('rb') as f: h=f.read(8)
  nxt=work/f'normalized_{idx}'
  if h.startswith(b'\\xfd7zXZ\\x00'): 
   with lzma.open(current) as i,nxt.open('wb') as o: shutil.copyfileobj(i,o)
   steps.append('xz')
  elif h.startswith(b'\\x1f\\x8b'):
   with gzip.open(current) as i,nxt.open('wb') as o: shutil.copyfileobj(i,o)
   steps.append('gzip')
  elif h[:4]==bytes.fromhex('3aff26ed'):
   if not shutil.which('simg2img'): raise RuntimeError('Android sparse image detected but simg2img is unavailable')
   subprocess.run(['simg2img',str(current),str(nxt)],check=True); steps.append('sparse_to_raw')
  elif h[:4]==bytes.fromhex('04224d18'):
   if not shutil.which('lz4'): raise RuntimeError('LZ4 payload detected but lz4 is unavailable')
   subprocess.run(['lz4','-d','-f',str(current),str(nxt)],check=True); steps.append('lz4')
  else: break
  current=nxt
 typ=fs_type(current)
 final=outdir/'system.img'; shutil.copyfile(current,final)
 report={'source':str(src),'source_sha256':sha256(src),'selected_member':member,'transformations':steps,'output':str(final),'output_sha256':sha256(final),'filesystem_hint':typ,'extraction':'normalized_payload_only','filesystem_contents_extracted':False,'compatibility':'not_assessed','boot_test':'not_performed'}
 (outdir/'extract-report.json').write_text(json.dumps(report,indent=2)+'\\n')
 shutil.rmtree(work,ignore_errors=True)
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('output_dir');a=p.parse_args()
 try: print(json.dumps(normalize(a.input,a.output_dir),indent=2))
 except Exception as e: print('ERROR:',e,file=sys.stderr);sys.exit(1)
