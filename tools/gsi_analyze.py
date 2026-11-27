#!/usr/bin/env python3
"""Evidence-first GSI image analyzer. Does not modify input or claim device compatibility."""
import argparse,hashlib,json,pathlib,subprocess,tarfile,zipfile
def sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def detect(path):
 p=pathlib.Path(path);size=p.stat().st_size
 with p.open('rb') as f:
  head=f.read(64)
  if head[:4]==bytes.fromhex('3aff26ed'):return 'android_sparse'
  f.seek(1024);er=f.read(4)
  if er==bytes.fromhex('e2e1f5e0'):return 'erofs'
  f.seek(1080);ext=f.read(2)
  if ext==bytes.fromhex('53ef'):return 'ext4'
  f.seek(1024);f2=f.read(4)
  if f2==bytes.fromhex('1020f5f2'):return 'f2fs'
  if head[:6]==b'\xfd7zXZ\x00':return 'xz'
  if head[:6]==bytes.fromhex('377abcaf271c'):return '7z'
  if head[:2]==b'\x1f\x8b':return 'gzip'
  if head[:4]==bytes.fromhex('04224d18'):return 'lz4'
  if head[:4]==b'PK\x03\x04':return 'zip'
  if size>262:
   f.seek(257)
   if f.read(5)==b'ustar':return 'tar'
 return 'unknown'
def archive_listing(p):
 names=[]
 try:
  if zipfile.is_zipfile(p):
   with zipfile.ZipFile(p) as z:names=[{'name':i.filename,'size':i.file_size} for i in z.infolist() if not i.is_dir()]
  elif tarfile.is_tarfile(p):
   with tarfile.open(p) as t:names=[{'name':i.name,'size':i.size} for i in t.getmembers() if i.isfile()]
  elif detect(p)=='7z' and shutil_7z(p):
   result=subprocess.run(['7z','l','-slt',str(p)],capture_output=True,text=True,check=True)
   records=[]
   for block in result.stdout.split('\n\n'):
    record={}
    for line in block.splitlines():
     if line.startswith('Path = '):record['name']=line[7:]
     elif line.startswith('Type = '):record['type']=line[7:]
     elif line.startswith('Size = '):
      try:record['size']=int(line[7:])
      except ValueError:record['size']=None
    if record.get('name') and record.get('type') != '7z' and pathlib.Path(record['name']).name != pathlib.Path(p).name:
     record.pop('type',None)
     records.append(record)
   names=records
 except Exception as e:return {'error':str(e)}
 return names
def shutil_7z(p):
 import shutil
 return bool(shutil.which('7z'))
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input');ap.add_argument('--json',dest='out');a=ap.parse_args()
 p=pathlib.Path(a.input);typ=detect(p);listing=archive_listing(p) if typ in ('zip','tar','7z') else []
 candidates=[]
 for item in listing:
  n=item['name'];base=pathlib.PurePosixPath(n).name.lower()
  if base in ('system.img','system.img.xz','system.img.gz','system.img.lz4') or ('system' in base and base.endswith('.img')):candidates.append(item)
 report={'input':str(p),'size_bytes':p.stat().st_size,'sha256':sha256(p),'type':typ,'archive_members':listing,'system_candidates':candidates,'assessment':'identified' if typ!='unknown' else 'unknown_preserved','compatibility':'not assessed','boot_test':'not performed'}
 text=json.dumps(report,indent=2);print(text)
 if a.out:pathlib.Path(a.out).write_text(text+'\n')
if __name__=='__main__':main()
