#!/usr/bin/env python3
"""Opt-in EROFS rebuild restricted to standard LZ4 or no compression."""
import argparse,json,pathlib,shutil,subprocess,hashlib,sys
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def rebuild(tree,out,compression):
 tree=pathlib.Path(tree).resolve();out=pathlib.Path(out).resolve()
 tool=shutil.which('mkfs.erofs')
 if not tool:raise RuntimeError('mkfs.erofs not found')
 if not tree.is_dir():raise ValueError('tree must be a directory')
 if out==tree or tree in out.parents:raise ValueError('output must be outside the source tree')
 out.parent.mkdir(parents=True,exist_ok=True)
 cmd=[tool]
 if compression=='lz4':cmd+=['-zlz4']
 cmd+=[str(out),str(tree)]
 subprocess.run(cmd,check=True)
 check=shutil.which('fsck.erofs');validation={'available':bool(check),'returncode':None,'stdout':'','stderr':''}
 if check:
  r=subprocess.run([check,'--check',str(out)],capture_output=True,text=True)
  validation.update({'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
  if r.returncode:raise RuntimeError('fsck.erofs validation failed; see stderr')
 report={'tree':str(tree),'output':str(out),'compression':compression,'policy':'standard LZ4 only (-zlz4) or uncompressed; advanced features prohibited','size_bytes':out.stat().st_size,'sha256':sha(out),'fsck_erofs':validation,'boot_test':'not_performed'}
 out.with_suffix(out.suffix+'.report.json').write_text(json.dumps(report,indent=2)+'\n')
 return report
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('tree');a.add_argument('output');a.add_argument('--compression',choices=['lz4','none'],default='lz4');x=a.parse_args()
 try:print(json.dumps(rebuild(x.tree,x.output,x.compression),indent=2))
 except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
