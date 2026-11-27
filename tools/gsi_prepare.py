#!/usr/bin/env python3
import argparse,gzip,lzma,pathlib,shutil,subprocess,sys,zipfile

def fs_type(p):
 with p.open('rb') as f:
  f.seek(1080); ext=f.read(2); f.seek(1024); er=f.read(4)
 if ext==bytes.fromhex('53ef'): return 'ext4'
 if er==bytes.fromhex('e2e1f5e0'): return 'erofs'
 return 'unknown'
def select_zip(z):
 c=[n for n in z.namelist() if not n.endswith('/') and pathlib.PurePosixPath(n).name.lower() in ('system.img','system.img.xz','system.img.gz','system.img.lz4')]
 if len(c)!=1: raise ValueError('Expected exactly one system image candidate, found: '+str(c))
 return c[0]
def normalize(src,dst):
 src=pathlib.Path(src); dst=pathlib.Path(dst); w=dst.parent/'normalize-work'
 if w.exists(): shutil.rmtree(w)
 w.mkdir(parents=True); cur=w/'candidate'
 if zipfile.is_zipfile(src):
  with zipfile.ZipFile(src) as z:
   n=select_zip(z)
   with z.open(n) as inp,cur.open('wb') as out: shutil.copyfileobj(inp,out)
 else: shutil.copyfile(src,cur)
 for _ in range(6):
  with cur.open('rb') as stream: head=stream.read(8)\n  nxt=w/'unpacked'
  if head.startswith(b'\xfd7zXZ\x00'):
   with lzma.open(cur) as inp,nxt.open('wb') as out: shutil.copyfileobj(inp,out)
  elif head.startswith(b'\x1f\x8b'):
   with gzip.open(cur) as inp,nxt.open('wb') as out: shutil.copyfileobj(inp,out)
  elif head[:4]==bytes.fromhex('3aff26ed'): subprocess.run(['simg2img',str(cur),str(nxt)],check=True)
  elif head.startswith(b'\x04\x22\x4d\x18'): subprocess.run(['lz4','-d','-f',str(cur),str(nxt)],check=True)
  else: break
  cur=nxt
 typ=fs_type(cur)
 if typ not in ('ext4','erofs'): raise ValueError('Unsupported/unknown filesystem: '+typ)
 dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(cur,dst); return typ
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('destination');a=p.parse_args()
 try: print('FS='+normalize(a.source,a.destination))
 except Exception as e: print('ERROR: '+str(e),file=sys.stderr);sys.exit(2)
