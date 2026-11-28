#!/usr/bin/env python3
"""Stages 9-10: read-only inventory and guarded, reversible property recipe edits."""
import argparse, collections, hashlib, json, pathlib, re, shutil, sys, tempfile

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def inventory(root):
    root=pathlib.Path(root).resolve()
    if not root.is_dir(): raise ValueError(f"not a directory: {root}")
    files=[p for p in root.rglob('*') if p.is_file() and not p.is_symlink()]
    props=collections.defaultdict(list); services=collections.defaultdict(list); sonames=collections.defaultdict(list); elf=[]
    for p in files:
        rel=p.relative_to(root).as_posix()
        if p.name.endswith('.prop'):
            for i,line in enumerate(p.read_text(errors='replace').splitlines(),1):
                s=line.strip()
                if s and not s.startswith('#') and '=' in s:
                    k,v=s.split('=',1);props[k.strip()].append({'file':rel,'line':i,'value':v.strip()})
        if p.name.endswith('.rc'):
            for i,line in enumerate(p.read_text(errors='replace').splitlines(),1):
                m=re.match(r'\s*service\s+(\S+)\s+(.*)',line)
                if m:services[m.group(1)].append({'file':rel,'line':i,'command':m.group(2)})
        if p.suffix=='.so' and p.read_bytes()[:4]==b'\x7fELF':
            sonames[p.name].append(rel);elf.append({'path':rel,'filename':p.name,'sha256':sha(p)})
    return {'root':str(root),'files':len(files),'properties':dict(props),'init_services':dict(services),'elf':elf,'elf_by_filename':dict(sonames)}

def analyze(system,vendor):
    s=inventory(system);v=inventory(vendor);sn=set(s['elf_by_filename']);vn=set(v['elf_by_filename'])
    conflicts={k:e for k,e in s['properties'].items() if len({x['value'] for x in e})>1}
    return {'schema':'a31-stage9-compat-analysis-v1','system':s,'vendor':v,'elf_filename_overlap':sorted(sn&vn),'system_elf_not_in_vendor_tree':sorted(sn-vn),'vendor_elf_not_in_system_tree':sorted(vn-sn),'system_property_conflicts':conflicts,'system_init_service_names':sorted(s['init_services']),'vendor_init_service_names':sorted(v['init_services']),'service_name_overlap':sorted(set(s['init_services'])&set(v['init_services'])),'assessment':'heuristic_inventory_only','unknowns':['ELF ABI and linker namespace compatibility','HAL protocol/runtime service compatibility','kernel/vendor ABI compatibility','SELinux compatibility','boot/device behavior'],'stage9_read_only':True,'stage10_patches_applied':False}

def safe_target(root,rel):
    root=pathlib.Path(root).resolve()
    if not isinstance(rel,str) or not rel or pathlib.Path(rel).is_absolute():raise ValueError('recipe path must be relative')
    candidate=root/rel
    # Reject symlinks in every path component, even if the final target stays inside root.
    cur=root
    for part in pathlib.Path(rel).parts:
        if part in ('','.', '..'):raise ValueError('recipe path contains traversal')
        cur=cur/part
        if cur.is_symlink():raise ValueError(f'symlink recipe target rejected: {rel}')
    p=candidate.resolve()
    if root not in p.parents:raise ValueError(f'path escapes tree: {rel}')
    if not p.is_file():raise ValueError(f'not a regular file: {rel}')
    return p

def apply_recipe(tree,recipe_path,backup_dir,apply=False):
    root=pathlib.Path(tree).resolve()
    if not root.is_dir():raise ValueError('tree directory required')
    recipe=json.loads(pathlib.Path(recipe_path).read_text())
    if recipe.get('schema')!='a31-compat-recipe-v1':raise ValueError('unsupported recipe schema')
    ops=recipe.get('operations')
    if not isinstance(ops,list):raise ValueError('operations must be a list')
    plans=[];seen=set()
    for op in ops:
        if not isinstance(op,dict) or op.get('type')!='set_property':raise ValueError('only set_property operation is supported')
        key=op.get('key');value=op.get('value');rel=op.get('path')
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9._-]+',key):raise ValueError('invalid property key')
        if not isinstance(value,str) or any(c in value for c in ('\n','\r','\x00')):raise ValueError('property value must be a single safe line')
        p=safe_target(root,rel);old=p.read_bytes();oldsha=hashlib.sha256(old).hexdigest()
        if op.get('expected_sha256') and op['expected_sha256']!=oldsha:raise ValueError(f'hash precondition failed for {rel}')
        text=old.decode('utf-8');lines=text.splitlines();matches=[i for i,l in enumerate(lines) if l.strip().startswith(key+'=')]
        if 'expected_value' in op and (not matches or lines[matches[0]].split('=',1)[1].strip()!=op['expected_value']):raise ValueError(f'value precondition failed for {rel}:{key}')
        if len(matches)>1:raise ValueError(f'multiple occurrences of {key} in {rel}')
        if matches:lines[matches[0]]=key+'='+value
        else:lines.append(key+'='+value)
        new=('\n'.join(lines)+'\n').encode()
        canonical=str(p)
        if canonical in seen:raise ValueError('duplicate resolved file target in recipe')
        seen.add(canonical)
        plans.append({'path':rel,'file':p,'before_sha256':oldsha,'after_sha256':hashlib.sha256(new).hexdigest(),'old':old,'new':new,'changed':old!=new,'mode':p.stat().st_mode})
    report={'schema':'a31-stage10-apply-report-v1','mode':'apply' if apply else 'dry_run','operations':[],'modified':False}
    if apply:
        bdir=pathlib.Path(backup_dir).resolve()
        if bdir==root or root in bdir.parents:raise ValueError('backup directory must be outside the target tree')
        bdir.mkdir(parents=True,exist_ok=True)
        # Preflight all backups before any mutation: never overwrite a prior backup.
        for plan in plans:
            if not plan['changed']:
                continue
            backup=bdir/plan['path']
            if backup.exists() or backup.is_symlink():raise ValueError(f'backup already exists; refusing overwrite: {backup}')
            if not backup.parent.resolve().is_relative_to(bdir):raise ValueError('backup path escapes backup directory')
        completed=[]
        try:
            for plan in plans:
                if plan['changed']:
                    backup=bdir/plan['path'];backup.parent.mkdir(parents=True,exist_ok=True)
                    backup.write_bytes(plan['old'])
                    plan['file'].write_bytes(plan['new'])
                    plan['file'].chmod(plan['mode'])
                    completed.append(plan)
                report['operations'].append({k:plan[k] for k in ('path','before_sha256','after_sha256','changed')})
        except Exception:
            # Restore files already modified if a subsequent write fails.
            for plan in reversed(completed):
                plan['file'].write_bytes(plan['old']);plan['file'].chmod(plan['mode'])
            raise
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
        pathlib.Path(args.report).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
    except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(2)
if __name__=='__main__':main()
