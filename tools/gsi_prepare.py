
#!/usr/bin/env python3
"""Permissive GSI intake/normalization for MT6768 A31 experiments; logs choices."""
import argparse,gzip,lzma,pathlib,shutil,subprocess,sys,zipfile
def fs_type(p):
 with p.open('rb') as f:
  f.seek(1080);ext=f.read(2);f.seek(1024);er=f.read(4);f.seek(1024);f2=f.read(4)
 if ext==bytes.fromhex('53ef'):return 'ext4'
 if er==bytes.fromhex('e2e1f5e0'):return 'erofs'\n if f2==bytes.fromhex('1020f5f2'):return 'f2fs'
 return 'unknown'
def choose(names):
 files=[n for n in names if not n.endswith('/')]
 if not files:return ''
 exact=[n for n in files if pathlib.PurePosixPath(n).name.lower() in ('system.img','system.img.xz','system.img.gz','system.img.lz4')]
 return sorted(exact,key=lambda n:(pathlib.PurePosixPath(n).name.lower()!='system.img',len(n)))[0] if exact else sorted(files,key=lambda n:(-len(n),n))[0]
def normalize(src,dst):
 src=pathlib.Path(src);dst=pathlib.Path(dst);w=dst.parent/'normalize-work'
 if w.exists():shutil.rmtree(w)
 w.mkdir(parents=True);cur=w/'candidate'
 if zipfile.is_zipfile(src):
  with zipfile.ZipFile(src) as z:
   name=choose(z.namelist());print('ZIP member chosen:',name)
   with z.open(name) as i,cur.open('wb') as o:shutil.copyfileobj(i,o)
 elif shutil.which('7z') and subprocess.run(['7z','t',str(src)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
  info=subprocess.run(['7z','l','-slt',str(src)],capture_output=True,text=True,check=True).stdout
  names=[line[7:] for line in info.splitlines() if line.startswith('Path = ')][1:]
  name=choose(names);print('Archive member chosen:',name)
  subprocess.run(['7z','e','-y',str(src),name,'-o'+str(w)],check=True,stdout=subprocess.DEVNULL)
  cur=w/pathlib.Path(name).name
  if not cur.exists():cur=next(w.iterdir())
 else:shutil.copyfile(src,cur)
 for _ in range(8):
  with cur.open('rb') as f:head=f.read(8)
  nxt=w/'unpacked'
  if head.startswith(b'\xfd7zXZ\x00'):
   with lzma.open(cur) as i,nxt.open('wb') as o:shutil.copyfileobj(i,o)
  elif head.startswith(b'\x1f\x8b'):
   with gzip.open(cur) as i,nxt.open('wb') as o:shutil.copyfileobj(i,o)
  elif head[:4]==bytes.fromhex('3aff26ed'):subprocess.run(['simg2img',str(cur),str(nxt)],check=True)
  elif head.startswith(b'\x04\x22\x4d\x18'):subprocess.run(['lz4','-d','-f',str(cur),str(nxt)],check=True)
  else:break
  cur=nxt
 typ=fs_type(cur);print('Filesystem:',typ);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(cur,dst);return typ
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('destination');a=p.parse_args()
 try:print('FS='+normalize(a.source,a.destination))
 except Exception as e:
  print('WARN - keeping original payload as-is:',e,file=sys.stderr);shutil.copyfile(a.source,a.destination);print('FS=unknown')
