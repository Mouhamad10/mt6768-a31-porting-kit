#!/usr/bin/env python3
"""Bounded, fail-closed GSI normalization."""
import argparse, gzip, lzma, pathlib, shutil, subprocess, zipfile, sys, tarfile
MAX_OUTPUT=8*1024**3
MAX_LAYERS=6
IMAGE_NAMES={"system.img","system.img.xz","system.img.gz","system.img.lz4","system.img.7z"}

def fs_type(p):
 p=pathlib.Path(p)
 if p.stat().st_size<1100:return 'unknown'
 with p.open('rb') as f:
  f.seek(1080);ext=f.read(2);f.seek(1024);magic=f.read(4)
 if ext==bytes.fromhex('53ef'):return 'ext4'
 if magic==bytes.fromhex('e2e1f5e0'):return 'erofs'
 if magic==bytes.fromhex('1020f5f2'):return 'f2fs'
 return 'unknown'

def choose(names):
 candidates=[n for n in names if pathlib.PurePosixPath(n).name.lower() in IMAGE_NAMES]
 if candidates:return sorted(candidates,key=lambda n:(pathlib.PurePosixPath(n).name.lower()!='system.img',len(n)))[0]
 raise ValueError('archive does not contain a recognized system image')
select_image=choose

def bounded_copy(src,dst,limit=MAX_OUTPUT):
 total=0
 with open(src,'rb') as i,open(dst,'wb') as o:
  while b:=i.read(1024*1024):
   total+=len(b)
   if total>limit:raise ValueError('output exceeds size limit')
   o.write(b)

def normalize(src,dst,limit=MAX_OUTPUT):
 src=pathlib.Path(src).resolve();dst=pathlib.Path(dst).resolve()
 if src==dst or src in dst.parents or dst in src.parents:raise ValueError('input/output paths must not overlap')
 work=dst.parent/'.gsi-normalize-work'
 if work.exists():shutil.rmtree(work)
 work.mkdir(parents=True);cur=work/'payload'
 if zipfile.is_zipfile(src):
  with zipfile.ZipFile(src) as z:
   name=choose([i.filename for i in z.infolist() if not i.is_dir()]);info=z.getinfo(name)
   if info.file_size>limit:raise ValueError('archive entry exceeds limit')
   with z.open(info) as i,cur.open('wb') as o:
    total=0
    while b:=i.read(1024*1024):
     total+=len(b)
     if total>limit:raise ValueError('expanded archive entry exceeds limit')
     o.write(b)
 elif src.stat().st_size>limit:raise ValueError('source exceeds limit')
 else:bounded_copy(src,cur,limit)
 for layer in range(MAX_LAYERS):
  with cur.open('rb') as f:head=f.read(8)
  nxt=work/f'unpacked_{layer}'
  if head.startswith(b'\\xfd7zXZ\\x00'):opener=lzma.open;kind='stream'
  elif head.startswith(b'\\x1f\\x8b'):opener=gzip.open;kind='stream'
  elif head[:4]==bytes.fromhex('3aff26ed'):
   if not shutil.which('simg2img'):raise RuntimeError('simg2img missing')
   subprocess.run(['simg2img',str(cur),str(nxt)],check=True);kind='done'
  elif head[:4]==bytes.fromhex('04224d18'):
   if not shutil.which('lz4'):raise RuntimeError('lz4 missing')
   subprocess.run(['lz4','-d','-f',str(cur),str(nxt)],check=True);kind='done'
  else:break
  if kind=='stream':
   total=0
   with opener(cur) as i,nxt.open('wb') as o:
    while b:=i.read(1024*1024):
     total+=len(b)
     if total>limit:raise ValueError('decompression limit exceeded')
     o.write(b)
  if nxt.stat().st_size>limit:raise ValueError('normalized output exceeds limit')
  cur=nxt
 else:raise RuntimeError('transformation layer limit exceeded')
 typ=fs_type(cur)
 if typ=='unknown':raise ValueError('normalized image has unknown filesystem signature')
 dst.parent.mkdir(parents=True,exist_ok=True);bounded_copy(cur,dst,limit);shutil.rmtree(work,ignore_errors=True);return typ
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('destination');a=p.parse_args()
 try:print('FS='+normalize(a.source,a.destination))
 except Exception as e:print('ERROR: '+str(e),file=sys.stderr);sys.exit(2)
