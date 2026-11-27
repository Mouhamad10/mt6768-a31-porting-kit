#!/usr/bin/env python3
"""Opt-in EROFS rebuild restricted to standard LZ4 or no compression."""
import argparse,json,pathlib,shutil,subprocess,hashlib,sys,tempfile,os
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def rebuild(tree,out,compression):
 tree=pathlib.Path(tree).resolve();out=pathlib.Path(out).resolve()
 if compression not in ('lz4','none'):raise ValueError('compression must be lz4 or none')
 if not tree.is_dir():raise ValueError('tree must be a directory')
 if out==tree or tree in out.parents:raise ValueError('output must be outside the source tree')
 tool=shutil.which('mkfs.erofs')
 if not tool:raise RuntimeError('mkfs.erofs not found')
 out.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.erofs-build-',suffix='.img',dir=out.parent);os.close(fd);pathlib.Path(tmp).unlink();tmp=pathlib.Path(tmp)
 try:
  cmd=[tool]
  if compression=='lz4':cmd+=['-zlz4']
  cmd+=[str(tmp),str(tree)]
  subprocess.run(cmd,check=True)
  if not tmp.is_file() or tmp.stat().st_size==0:raise RuntimeError('mkfs.erofs produced no image')
  check=shutil.which('fsck.erofs');validation={'available':bool(check),'returncode':None,'stdout':'','stderr':'','performed':False}
  if check:
   r=subprocess.run([check,'--check',str(tmp)],capture_output=True,text=True)
   validation.update({'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'performed':True})
   if r.returncode:raise RuntimeError('fsck.erofs validation failed; staged output discarded')
  report={'tree':str(tree),'output':str(out),'compression':compression,'policy':'standard LZ4 only (-zlz4) or uncompressed; advanced features prohibited','size_bytes':tmp.stat().st_size,'sha256':sha(tmp),'fsck_erofs':validation,'boot_test':'not_performed'}
  tmp.replace(out)
  reporttmp=out.with_suffix(out.suffix+'.report.json.tmp')
  reporttmp.write_text(json.dumps(report,indent=2)+'\n')
  reporttmp.replace(out.with_suffix(out.suffix+'.report.json'))
  return report
 finally:tmp.unlink(missing_ok=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('tree');a.add_argument('output');a.add_argument('--compression',choices=['lz4','none'],default='lz4');x=a.parse_args()
 try:print(json.dumps(rebuild(x.tree,x.output,x.compression),indent=2))
 except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
