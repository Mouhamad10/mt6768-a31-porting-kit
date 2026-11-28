#!/usr/bin/env python3
"""Stage 12: filesystem validation only; not a boot or image-build test."""
import argparse, hashlib, json, pathlib, re, collections

def validate(root):
 root=pathlib.Path(root).resolve()
 if not root.is_dir():raise ValueError('tree directory required')
 findings=[];counts=collections.Counter();hashes=[]
 for p in root.rglob('*'):
  rel=p.relative_to(root).as_posix()
  if p.is_symlink():
   target=p.resolve(strict=False)
   try:outside=not target.is_relative_to(root)
   except AttributeError:outside=root not in target.parents and target!=root
   if outside:findings.append({'severity':'error','kind':'symlink_escape','path':rel,'target':str(p.readlink())})
   if not target.exists():findings.append({'severity':'warning','kind':'dangling_symlink','path':rel})
   counts['symlinks']+=1;continue
  if p.is_file():
   counts['files']+=1
   try:data=p.read_bytes()
   except OSError as e:findings.append({'severity':'error','kind':'unreadable_file','path':rel,'detail':str(e)});continue
   hashes.append({'path':rel,'sha256':hashlib.sha256(data).hexdigest()})
   if p.suffix=='.prop':
    lines=data.decode('utf-8',errors='replace').splitlines();keys=collections.defaultdict(list)
    for i,line in enumerate(lines,1):
     t=line.strip()
     if t and not t.startswith('#') and '=' in t:
      k,v=t.split('=',1);keys[k.strip()].append({'line':i,'value':v.strip()})
    for k,vals in keys.items():
     if len(vals)>1:findings.append({'severity':'warning','kind':'duplicate_property','path':rel,'key':k,'lines':[v['line'] for v in vals],'values':[v['value'] for v in vals]})
   if p.suffix=='.rc':
    lines=data.decode('utf-8',errors='replace').splitlines()
    for i,line in enumerate(lines,1):
     if re.match(r'\s*(service|import)\s+',line) and '\x00' in line:findings.append({'severity':'error','kind':'invalid_init_line','path':rel,'line':i})
  elif p.is_dir():counts['directories']+=1
 errors=sum(f['severity']=='error' for f in findings);warnings=sum(f['severity']=='warning' for f in findings)
 return {'schema':'a31-stage12-tree-validation-v1','tree':str(root),'counts':dict(counts),'findings':findings,'errors':errors,'warnings':warnings,'file_hash_manifest':hashes,'result':'FAIL' if errors else 'PASS_WITH_WARNINGS' if warnings else 'PASS','boot_test':'NOT_PERFORMED','image_build_test':'NOT_PERFORMED','scope':'filesystem sanity, symlink boundaries, duplicate property inventory and hashes; not Android runtime validation'}

def main():
 a=argparse.ArgumentParser();a.add_argument('tree');a.add_argument('--report',default='stage12-report.json');x=a.parse_args();r=validate(x.tree);pathlib.Path(x.report).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
