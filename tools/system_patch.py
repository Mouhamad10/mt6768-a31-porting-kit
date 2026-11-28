#!/usr/bin/env python3
"""Reversible, hash-guarded property patch helper for extracted Android system trees.

Patch schema:
{"schema":"a31-system-patch-v1","operations":[
 {"op":"set_property","path":"system/build.prop","key":"ro.foo","value":"bar","expected_sha256":"..."}
]}
Apply writes a JSON rollback manifest; rollback only restores files whose current
hash still matches the post-apply hash recorded in the manifest.
"""
import argparse, hashlib, json, pathlib, re, sys
def digest(b): return hashlib.sha256(b).hexdigest()
def safe(root, rel):
 p=(root/rel).resolve()
 if not p.is_relative_to(root.resolve()): raise ValueError("path escapes tree")
 return p
def apply(root, patch, manifest):
 root=pathlib.Path(root); data=json.loads(pathlib.Path(patch).read_text())
 if data.get('schema')!='a31-system-patch-v1': raise ValueError('unsupported patch schema')
 rollback=[]
 for op in data.get('operations',[]):
  if op.get('op')!='set_property': raise ValueError('unsupported operation')
  key=op.get('key','')
  if not re.fullmatch(r'[A-Za-z0-9_.-]+',key): raise ValueError('invalid property key')
  p=safe(root,op['path']); old=p.read_bytes()
  if digest(old)!=op.get('expected_sha256'): raise ValueError('hash precondition failed: '+op['path'])
  text=old.decode('utf-8')
  lines=text.splitlines(keepends=True); found=False; newlines=[]
  for line in lines:
   if line.lstrip().startswith(key+'='):
    if found: continue
    newlines.append(key+'='+op['value']+'\n'); found=True
   else:newlines.append(line)
  if not found:newlines.append(key+'='+op['value']+'\n')
  new=''.join(newlines).encode()
  p.write_bytes(new)
  rollback.append({'path':op['path'],'before':old.decode('utf-8'),'before_sha256':digest(old),'after_sha256':digest(new)})
 pathlib.Path(manifest).write_text(json.dumps({'schema':'a31-system-rollback-v1','items':rollback},indent=2))
 print('Applied',len(rollback),'operation(s); rollback manifest:',manifest)
def revert(root, manifest):
 root=pathlib.Path(root); data=json.loads(pathlib.Path(manifest).read_text())
 if data.get('schema')!='a31-system-rollback-v1':raise ValueError('unsupported rollback manifest')
 for item in reversed(data['items']):
  p=safe(root,item['path']); current=p.read_bytes()
  if digest(current)!=item['after_sha256']:raise ValueError('rollback hash guard failed: '+item['path'])
  before=item['before'].encode()
  if digest(before)!=item['before_sha256']:raise ValueError('manifest integrity mismatch')
  p.write_bytes(before)
 print('Rolled back',len(data['items']),'file(s)')
def main():
 a=argparse.ArgumentParser(); sub=a.add_subparsers(dest='mode',required=True)
 ap=sub.add_parser('apply');ap.add_argument('tree');ap.add_argument('patch');ap.add_argument('--rollback-manifest',default='rollback.json')
 rb=sub.add_parser('rollback');rb.add_argument('tree');rb.add_argument('manifest')
 x=a.parse_args()
 if x.mode=='apply':apply(x.tree,x.patch,x.rollback_manifest)
 else:revert(x.tree,x.manifest)
if __name__=='__main__':main()
