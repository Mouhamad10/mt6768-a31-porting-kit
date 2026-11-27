#!/usr/bin/env python3
"""Inventory all image-like members of ZIP/TAR archives; never extract them."""
import argparse,json,pathlib,tarfile,zipfile
SUFFIXES=('.img','.img.xz','.img.gz','.img.lz4','.bin')
def inventory(p):
 p=pathlib.Path(p);items=[]
 if zipfile.is_zipfile(p):
  with zipfile.ZipFile(p) as z:
   items=[{'name':i.filename,'size':i.file_size,'compressed_size':i.compress_size,'kind':'zip'} for i in z.infolist() if not i.is_dir() and i.filename.lower().endswith(SUFFIXES)]
 elif tarfile.is_tarfile(p):
  with tarfile.open(p,'r:*') as t:
   items=[{'name':i.name,'size':i.size,'kind':'tar'} for i in t.getmembers() if i.isfile() and i.name.lower().endswith(SUFFIXES)]
 else:raise ValueError('supported inventory containers: ZIP and TAR')
 return {'archive':str(p),'image_candidates':items,'selection_required':len(items)>1}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('archive');a.add_argument('--json');x=a.parse_args();r=inventory(x.archive);s=json.dumps(r,indent=2);print(s)
 if x.json:pathlib.Path(x.json).write_text(s+'\n')
