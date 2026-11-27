#!/usr/bin/env python3
"""Read-only filesystem inspection for normalized Android system images.

No mounting, writes to image, or automatic compatibility conclusions.
"""
import argparse,json,pathlib,shutil,subprocess
try:
 from .gsi_prepare import fs_type
except ImportError:
 from gsi_prepare import fs_type

def inspect(image):
 p=pathlib.Path(image).resolve(); kind=fs_type(p); result={'image':str(p),'filesystem':kind,'inspection':'signature_only','tools':{},'compatibility':'not_assessed'}
 if kind=='ext4':
  tool=shutil.which('debugfs')
  result['tools']['debugfs']=bool(tool)
  if tool:
   run=subprocess.run([tool,'-R','stats',str(p)],capture_output=True,text=True)
   result['ext4_stats']=run.stdout if run.returncode==0 else run.stderr
   ls=subprocess.run([tool,'-R','ls -p /',str(p)],capture_output=True,text=True)
   result['root_listing']=ls.stdout[:12000] if ls.returncode==0 else ls.stderr
   result['inspection']='ext4_read_only_metadata_and_root_listing'
 elif kind=='erofs':
  tool=shutil.which('dump.erofs')
  result['tools']['dump.erofs']=bool(tool)
  if tool:
   run=subprocess.run([tool,str(p)],capture_output=True,text=True)
   result['erofs_metadata']=run.stdout[:12000] if run.returncode==0 else run.stderr
   result['inspection']='erofs_metadata'
 elif kind=='f2fs':
  tool=shutil.which('dump.f2fs')
  result['tools']['dump.f2fs']=bool(tool)
  if tool:
   run=subprocess.run([tool,str(p)],capture_output=True,text=True)
   result['f2fs_metadata']=run.stdout[:12000] if run.returncode==0 else run.stderr
   result['inspection']='f2fs_metadata'
 return result
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('image');a.add_argument('--json');args=a.parse_args()
 r=inspect(args.image);text=json.dumps(r,indent=2);print(text)
 if args.json:pathlib.Path(args.json).write_text(text+'\n')
