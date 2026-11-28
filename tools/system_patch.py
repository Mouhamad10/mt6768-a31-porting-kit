#!/usr/bin/env python3
"""Hash-guarded property edits on an extracted Android tree."""
import argparse, hashlib, json, pathlib, re, tempfile, os
def digest(b): return hashlib.sha256(b).hexdigest()
def safe(root, rel):
 p=(root/rel).resolve()
 if not p.is_relative_to(root.resolve()): raise ValueError("path escapes tree")
 return p
def transform(old,key,value):
 text=old.decode('utf-8'); lines=text.splitlines(keepends=True); found=False; out=[]
 for line in lines:
  stripped=line.lstrip()
  if stripped.startswith(key+'=') and not stripped.startswith('#'):
   if found: continue
   indent=line[:len(line)-len(stripped)]
   ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
   out.append(indent+key+'='+value+ending);found=True
  else:out.append(line)
 if not found:
  ending='\r\n' if any(x.endswith('\r\n') for x in lines) else '\n'
  if out and not out[-1].endswith(('\n','\r')):out[-1]+=ending
  out.append(key+'='+value+ending)
 return ''.join(out).encode()
def atomic_write(p,b):
 p.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix='.patchtmp-',dir=str(p.parent))
 try:
  with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
 except Exception:
  try:os.unlink(tmp)
  except OSError:pass
  raise
def replace_exact(old,before_text,after_text):
 text=old.decode('utf-8')
 if text.count(before_text)!=1:raise ValueError('before_text must occur exactly once')
 return text.replace(before_text,after_text,1).encode('utf-8')
def apply(root,patch,manifest):
 root=pathlib.Path(root).resolve();data=json.loads(pathlib.Path(patch).read_text())
 if data.get('schema')!='a31-system-patch-v1':raise ValueError('unsupported patch schema')
 ops=data.get('operations',[])
 if not ops:raise ValueError('patch contains no operations')
 staged=[];seen=set()
 for op in ops:
  kind=op.get('op')
  if kind not in ('set_property','replace_exact'):raise ValueError('unsupported operation')
  if kind=='set_property':
   key=op.get('key','')
   if not re.fullmatch(r'[A-Za-z0-9_.-]+',key):raise ValueError('invalid property key')
  elif not isinstance(op.get('before_text'),str) or not isinstance(op.get('after_text'),str) or not op['before_text'] or op['before_text']==op['after_text']:raise ValueError('invalid exact replacement fields')
  p=safe(root,op['path'])
  if p in seen:raise ValueError('multiple operations target same file; combine them')
  seen.add(p);old=p.read_bytes()
  if digest(old)!=op.get('expected_sha256'):raise ValueError('hash precondition failed: '+op['path'])
  after=transform(old,key,str(op['value'])) if kind=='set_property' else replace_exact(old,op['before_text'],op['after_text'])
  staged.append({'path':op['path'],'file':p,'before':old,'after':after})
 written=[]
 try:
  for item in staged:atomic_write(item['file'],item['after']);written.append(item)
 except Exception:
  for item in reversed(written):atomic_write(item['file'],item['before'])
  raise
 rb={'schema':'a31-system-rollback-v1','items':[{'path':x['path'],'before':x['before'].decode(),'before_sha256':digest(x['before']),'after_sha256':digest(x['after'])} for x in staged]}
 atomic_write(pathlib.Path(manifest),json.dumps(rb,indent=2).encode())
 print('Applied',len(staged),'operation(s); rollback manifest:',manifest)
def revert(root,manifest):
 root=pathlib.Path(root).resolve();data=json.loads(pathlib.Path(manifest).read_text())
 if data.get('schema')!='a31-system-rollback-v1':raise ValueError('unsupported rollback manifest')
 staged=[]
 for item in reversed(data['items']):
  p=safe(root,item['path']);current=p.read_bytes()
  if digest(current)!=item['after_sha256']:raise ValueError('rollback hash guard failed: '+item['path'])
  before=item['before'].encode()
  if digest(before)!=item['before_sha256']:raise ValueError('manifest integrity mismatch')
  staged.append((p,before))
 for p,b in staged:atomic_write(p,b)
 print('Rolled back',len(staged),'file(s)')
def main():
 a=argparse.ArgumentParser();s=a.add_subparsers(dest='mode',required=True)
 ap=s.add_parser('apply');ap.add_argument('tree');ap.add_argument('patch');ap.add_argument('--rollback-manifest',default='rollback.json')
 rb=s.add_parser('rollback');rb.add_argument('tree');rb.add_argument('manifest')
 x=a.parse_args()
 if x.mode=='apply':apply(x.tree,x.patch,x.rollback_manifest)
 else:revert(x.tree,x.manifest)
if __name__=='__main__':main()
