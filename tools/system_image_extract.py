#!/usr/bin/env python3
"""Read-only extraction of ext4/EROFS system image into a fresh destination tree."""
import argparse, pathlib, subprocess, shutil, sys
def detect(p):
 b=p.read_bytes()[:4096]
 if len(b)>=1082 and b[1080:1082]==b'\x53\xef':return 'ext4'
 if len(b)>=1028 and b[1024:1028]==b'\xe2\xe1\xf5\xe0':return 'erofs'
 return 'unknown'
def main():
 a=argparse.ArgumentParser();a.add_argument('image');a.add_argument('destination');x=a.parse_args()
 image=pathlib.Path(x.image).resolve(); dest=pathlib.Path(x.destination).resolve()
 if not image.is_file():raise SystemExit('image file not found')
 if dest.exists() and any(dest.iterdir()):raise SystemExit('destination must be absent or empty')
 dest.mkdir(parents=True,exist_ok=True); fs=detect(image)
 if fs=='ext4':
  tool=shutil.which('debugfs')
  if not tool:raise SystemExit('debugfs missing; install e2fsprogs')
  cmd=[tool,'-R',f'rdump / {dest}',str(image)]
 elif fs=='erofs':
  tool=shutil.which('fsck.erofs')
  if not tool:raise SystemExit('fsck.erofs missing; install erofs-utils')
  cmd=[tool,'--extract='+str(dest),str(image)]
 else:raise SystemExit('unsupported/unknown filesystem; convert Android sparse/compressed image first')
 result=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if result.returncode:
  print(result.stdout);print(result.stderr,file=sys.stderr);raise SystemExit(result.returncode)
 print(f'Extracted read-only {fs} image tree to {dest}. Verify extraction output and permissions/xattrs before use.')
if __name__=='__main__':main()
