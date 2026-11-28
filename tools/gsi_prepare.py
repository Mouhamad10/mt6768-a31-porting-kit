#!/usr/bin/env python3
"""Bounded, fail-closed GSI normalization. Never silently copies a failed input."""
import argparse, gzip, lzma, pathlib, shutil, subprocess, zipfile, sys
MAX_OUTPUT=8*1024**3
MAX_LAYERS=6
IMAGE_NAMES={"system.img","system.img.xz","system.img.gz","system.img.lz4","system.img.7z"}

def fs_type(p):
 p=pathlib.Path(p)
 if p.stat().st_size<1100:return 'unknown'
 with p.open('rb') as f:
  f.seek(1080);ext=f.read(2)
  f.seek(1024);magic=f.read(4)
 if ext==bytes.fromhex('53ef'):return 'ext4'
 if magic==bytes.fromhex('e2e1f5e0'):return 'erofs'
 if magic==bytes.fromhex('1020f5f2'):return 'f2fs'
 return 'unknown'

def select_image(names):
 matches=[n for n in names if pathlib.PurePosixPath(n).name.lower() in IMAGE_NAMES]
 if not matches:raise ValueError('archive contains no recognized system image candidate')
 return sorted(matches,key=lambda n:(pathlib.PurePosixPath(n).name.lower()!='system.img',len(n)))[0]

def bounded_copy(src,dst):
 total=0
 with open(src,'rb') as i,open(dst,'wb') as o:
  while True:
   b=i.read(1024*1024)
   if not b:break
   total+=len(b)
   if total>MAX_OUTPUT:raise ValueError('output exceeds 8 GiB safety limit')
   o.write(b)

def normalize(src,dst):
 src=pathlib.Path(src);dst=pathlib.Path(dst);work=dst.parent/'normalize-work'
 if work.exists():shutil.rmtree(work)
 work.mkdir(parents=True);cur=work/'payload'
 if zipfile.is_zipfile(src):
  with zipfile.ZipFile(src) as z:
   name=select_image(z.namelist());info=z.getinfo(name)
   if info.file_size>MAX_OUTPUT:raise ValueError('archive entry exceeds output limit')
   with z.open(name) as i,cur.open('wb') as o:
    total=0
    while b:=i.read(1024*1024):
     total+=len(b)
     if total>MAX_OUTPUT:raise ValueError('decompressed ZIP entry exceeds limit')
     o.write(b)
 elif shutil.which('7z') and subprocess.run(['7z','t',str(src)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
  listing=subprocess.run(['7z','l','-slt',str(src)],capture_output=True,text=True,check=True).stdout
  names=[line[7:] for line in listing.splitlines() if line.startswith('Path = ')][1:]
  name=select_image(names)
  # Extract selected member to a fresh directory, reject path traversal by basename-only.
  with subprocess.Popen(['7z','e','-so',str(src),name],stdout=subprocess.PIPE,stderr=subprocess.PIPE) as proc:
   total=0
   with cur.open('wb') as o:
    while b:=proc.stdout.read(1024*1024):
     total+=len(b)
     if total>MAX_OUTPUT:proc.kill();raise ValueError('archive output exceeds limit')
     o.write(b)
   if proc.wait()!=0:raise RuntimeError('7z extraction failed')
 else:bounded_copy(src,cur)
 for layer in range(MAX_LAYERS):
  with cur.open('rb') as f:head=f.read(8)
  nxt=work/f'unpacked_{layer}'
  if head.startswith(b'\\xfd7zXZ\\x00'):
   opener=lzma.open
  elif head.startswith(b'\\x1f\\x8b'):
   opener=gzip.open
  elif head[:4]==bytes.fromhex('3aff26ed'):
   if not shutil.which('simg2img'):raise RuntimeError('simg2img not installed for sparse image')
   subprocess.run(['simg2img',str(cur),str(nxt)],check=True)
  elif head[:4]==bytes.fromhex('04224d18'):
   if not shutil.which('lz4'):raise RuntimeError('lz4 not installed for LZ4 image')
   subprocess.run(['lz4','-d','-f',str(cur),str(nxt)],check=True)
  else:break
  if head.startswith((b'\\xfd7zXZ\\x00',b'\\x1f\\x8b')):
   total=0
   with opener(cur) as i,nxt.open('wb') as o:
    while b:=i.read(1024*1024):
     total+=len(b)
     if total>MAX_OUTPUT:raise ValueError('decompressed image exceeds limit')
     o.write(b)
  cur=nxt
 else:raise RuntimeError('too many compression/sparse layers')
 typ=fs_type(cur)
 if typ=='unknown':raise ValueError('normalized payload is not a recognized ext4/EROFS/F2FS image')
 dst.parent.mkdir(parents=True,exist_ok=True);bounded_copy(cur,dst);return typ
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('destination');a=p.parse_args()
 try:print('FS='+normalize(a.source,a.destination))
 except Exception as e:
  print('ERROR: normalization failed: '+str(e),file=sys.stderr);sys.exit(2)
