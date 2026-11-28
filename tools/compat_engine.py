#!/usr/bin/env python3
"""Stages 9-10: evidence-driven tree compatibility analysis and reversible recipe application.

Stage 9 is read-only. Stage 10 defaults to dry-run; --apply is explicit.
Recipes support only deterministic property edits, guarded by file hashes or old values.
"""
import argparse, collections, hashlib, json, pathlib, re, shutil, sys

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def inventory(root):
    root=pathlib.Path(root).resolve()
    if not root.is_dir(): raise ValueError(f"not a directory: {root}")
    files=[p for p in root.rglob('*') if p.is_file() and not p.is_symlink()]
    props=collections.defaultdict(list); init_services=collections.defaultdict(list); sonames=collections.defaultdict(list); elf=[]
    for p in files:
        rel=p.relative_to(root).as_posix()
        if p.name.endswith('.prop'):
            try: lines=p.read_text(errors='replace').splitlines()
            except OSError: lines=[]
            for i,line in enumerate(lines,1):
                s=line.strip()
                if s and not s.startswith('#') and '=' in s:
                    k,v=s.split('=',1);props[k.strip()].append({'file':rel,'line':i,'value':v.strip()})
        if p.name.endswith('.rc'):
            try: lines=p.read_text(errors='replace').splitlines()
            except OSError: lines=[]
            for i,line in enumerate(lines,1):
                m=re.match(r'\\s*service\\s+(\\S+)\\s+(.*)',line)
                if m:init_services[m.group(1)].append({'file':rel,'line':i,'command':m.group(2)})
        if p.suffix=='.so':
            try: data=p.read_bytes()[:4]
            except OSError: continue
            if data==b'\\x7fELF':
                sonames[p.name].append(rel);elf.append({'path':rel,'filename':p.name,'sha256':sha(p)})
    return {'root':str(root),'files':len(files),'properties':dict(props),'init_services':dict(init_services),'elf':elf,'elf_by_filename':dict(sonames)}

def analyze(system,vendor):
    s=inventory(system);v=inventory(vendor);vnames=set(v['elf_by_filename']);snames=set(s['elf_by_filename'])
    shared=snames&vnames
    propconf={k:entries for k,entries in s['properties'].items() if len({e['value'] for e in entries})>1}
    report={'schema':'a31-stage9-compat-analysis-v1','system':s,'vendor':v,
      'elf_filename_overlap':sorted(shared),'system_elf_not_in_vendor_tree':sorted(snames-vnames),
      'vendor_elf_not_in_system_tree':sorted(vnames-snames),'system_property_conflicts':propconf,
      'system_init_service_names':sorted(s['init_services']),'vendor_init_service_names':sorted(v['init_services']),
      'service_name_overlap':sorted(set(s['init_services'])&set(v['init_services'])),
      'assessment':'heuristic_inventory_only','unknowns':['ELF ABI and linker namespace compatibility','HAL protocol and runtime service compatibility','kernel/vendor ABI compatibility','SELinux policy compatibility','boot and device behavior'],
      'stage9_read_only':True,'stage10_patches_applied':False}
    return report

def safe_target(root,rel):
    root=pathlib.Path(root).resolve()
    if not isinstance(rel,str) or not rel or pathlib.Path(rel).is_absolute():raise ValueError('recipe path must be a relative path')
    p=(root/rel).resolve()
    if root not in p.parents:raise ValueError(f'path escapes tree: {rel}')
    if not p.is_file() or p.is_symlink():raise ValueError(f'not a regular file: {rel}')
    return p

def apply_recipe(tree,recipe_path,backup_dir,apply=False):
    root=pathlib.Path(tree).resolve();recipe=json.loads(pathlib.Path(recipe_path).read_text())
    if recipe.get('schema')!='a31-compat-recipe-v1':raise ValueError('unsupported recipe schema')
    ops=recipe.get('operations')
    if not isinstance(ops,list):raise ValueError('operations must be a list')
    plans=[];seen=set()
    for op in ops:
        if op.get('type')!='set_property':raise ValueError('only set_property operation is supported')
        key=op.get('key');value=op.get('value');rel=op.get('path')
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9._-]+',key):raise ValueError('invalid property key')
        if not isinstance(value,str) or '\\n' in value or '\\r' in value:raise ValueError('property value must be a single line')
        p=safe_target(root,rel);old=p.read_bytes();oldsha=hashlib.sha256(old).hexdigest()
        if op.get('expected_sha256') and op['expected_sha256']!=oldsha:raise ValueError(f'hash precondition failed for {rel}')
        text=old.decode('utf-8');lines=text.splitlines();matches=[i for i,l in enumerate(lines) if l.strip().startswith(key+'=')]
        if 'expected_value' in op and (not matches or lines[matches[0]].split('=',1)[1].strip()!=op['expected_value']):raise ValueError(f'value precondition failed for {rel}:{key}')
        if len(matches)>1:raise ValueError(f'multiple occurrences of {key} in {rel}; recipe must resolve ambiguity')
        if matches:lines[matches[0]]=key+'='+value
        else:lines.append(key+'='+value)
        new=('\\n'.join(lines)+'\\n').encode()
        if rel in seen:raise ValueError('multiple operations targeting the same file are not supported in one recipe')
        seen.add(rel);plans.append({'path':rel,'file':p,'before_sha256':oldsha,'after_sha256':hashlib.sha256(new).hexdigest(),'old':old,'new':new,'changed':old!=new})
    report={'schema':'a31-stage10-apply-report-v1','mode':'apply' if apply else 'dry_run','operations':[],'modified':False}
    if apply:
        bdir=pathlib.Path(backup_dir).resolve();bdir.mkdir(parents=True,exist_ok=True)
        for plan in plans:
            if plan['changed']:
                backup=bdir/plan['path'];backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(plan['old'])
                plan['file'].write_bytes(plan['new'])
            report['operations'].append({k:plan[k] for k in ('path','before_sha256','after_sha256','changed')})
        report['modified']=any(x['changed'] for x in plans);report['backup_dir']=str(bdir)
    else:
        report['operations']=[{k:plan[k] for k in ('path','before_sha256','after_sha256','changed')} for plan in plans]
    return report

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('analyze');a.add_argument('system_tree');a.add_argument('vendor_tree');a.add_argument('--report',default='stage9-report.json')
    p=sub.add_parser('apply');p.add_argument('tree');p.add_argument('recipe');p.add_argument('--backup-dir',default='compat-backups');p.add_argument('--apply',action='store_true');p.add_argument('--report',default='stage10-report.json')
    args=ap.parse_args()
    try:
        r=analyze(args.system_tree,args.vendor_tree) if args.cmd=='analyze' else apply_recipe(args.tree,args.recipe,args.backup_dir,args.apply)
        pathlib.Path(args.report).write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r,indent=2))
    except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(2)
if __name__=='__main__':main()
