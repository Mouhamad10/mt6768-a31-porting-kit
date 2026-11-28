#!/usr/bin/env python3
"""Evidence-first analyzer for an extracted Android system-side tree (read-only)."""
import argparse, collections, json, pathlib, re, subprocess, hashlib
P=pathlib.Path
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def readelf(p,flag):
 return subprocess.run(['readelf',flag,str(p)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30).stdout
def main():
 ap=argparse.ArgumentParser();ap.add_argument('tree');ap.add_argument('--report',default='system-audit.json');ap.add_argument('--props-report',default='system-audit.txt');args=ap.parse_args()
 root=P(args.tree).resolve()
 if not root.is_dir(): raise SystemExit('Expected extracted system-side directory')
 files=[p for p in root.rglob('*') if p.is_file() or p.is_symlink()]; libs=[p for p in files if p.name.endswith('.so')]
 sonames=collections.defaultdict(list);elf=[];errors=[];props=[];init=[];init_services=[];init_imports=[];init_actions=[];apks=[];apex=[];overlays=[];ldconfig=[];hal_hints=[];fstab=[]
 for p in libs:
  try:
   if p.is_symlink() or p.read_bytes()[:4]!=b'\x7fELF':continue
   out=readelf(p,'-d');m=re.search(r'\(SONAME\).*\[(.*?)\]',out);soname=m.group(1) if m else p.name
   need=re.findall(r'\(NEEDED\).*\[(.*?)\]',out);hdr=readelf(p,'-h')
   machine=re.search(r'^\s*Machine:\s*(.+)$',hdr,re.M);cls=re.search(r'^\s*Class:\s*(.+)$',hdr,re.M);endian=re.search(r'^\s*Data:\s*(.+)$',hdr,re.M)
   ph=readelf(p,'-l');interp=re.search(r'\[Requesting program interpreter: (.*?)\]',ph)
   paths=re.findall(r'\((?:RPATH|RUNPATH)\).*\[(.*?)\]',out)
   item={'path':str(p.relative_to(root)),'soname':soname,'needed':need,'sha256':sha(p),'elf_class':cls.group(1).strip() if cls else None,'machine':machine.group(1).strip() if machine else None,'endianness':endian.group(1).strip() if endian else None,'interpreter':interp.group(1) if interp else None,'runpath_rpath':paths}
   sonames[soname].append(item['path']);elf.append(item)
  except Exception as e:errors.append({'path':str(p.relative_to(root)),'error':str(e)})
 for p in files:
  rel=str(p.relative_to(root))
  if p.is_symlink():continue
  try:
   if p.name.endswith('.prop'):
    for ln,line in enumerate(p.read_text(errors='ignore').splitlines(),1):
     s=line.strip()
     if s and not s.startswith('#') and '=' in s:
      key,val=s.split('=',1);props.append({'file':rel,'line':ln,'key':key.strip(),'value':val.strip()})
   if p.name=='init.rc' or p.name.startswith('init.') and p.name.endswith('.rc'):
    init.append(rel);txt=p.read_text(errors='ignore')
    for m in re.finditer(r'(?m)^\s*service\s+(\S+)\s+(.*)$',txt):init_services.append({'file':rel,'line':txt[:m.start()].count('\n')+1,'name':m.group(1),'command':m.group(2).strip()})
    for ln,line in enumerate(txt.splitlines(),1):
     im=re.match(r'\s*import\s+(\S+)',line)
     if im:init_imports.append({'file':rel,'line':ln,'target':im.group(1)})
     ac=re.match(r'\s*on\s+(.+)',line)
     if ac:init_actions.append({'file':rel,'line':ln,'trigger':ac.group(1)})
   if p.name.startswith('ld.config') or p.name.endswith('linker.config.json'):ldconfig.append({'path':rel,'sha256':sha(p)})
   if p.suffix=='.apk':apks.append(rel)
   if p.suffix=='.apex':apex.append(rel)
   if 'overlay' in p.parts:overlays.append(rel)
   if 'fstab' in p.name.lower():fstab.append(rel)
   if re.search(r'(?i)(\bhal\b|\bvendor\b|\bservice\b|\bdaemon\b|\bcodec\b|\btelephony\b|\baudio\b|\bcamera\b)',p.name) and (p.suffix in ('.rc','.xml','.json','.so') or p.name.endswith('.txt')):hal_hints.append(rel)
  except Exception as e:errors.append({'path':rel,'error':str(e)})
 duplicates={k:v for k,v in sonames.items() if len(v)>1};pg=collections.defaultdict(list)
 for x in props:pg[x['key']].append(x)
 conflicts={k:v for k,v in pg.items() if len({x['value'] for x in v})>1}
 report={'schema':'a31-system-audit-v3','root':str(root),'file_count':len(files),'elf_count':len(elf),'elf':elf,'duplicate_sonames':duplicates,'property_conflicts':conflicts,'properties':props,'init_rc':init,'init_services':init_services,'init_imports':init_imports,'init_actions':init_actions,'linker_config_files':ldconfig,'fstab_candidates':fstab,'hal_service_name_hints':sorted(set(hal_hints)),'apk_count':len(apks),'apks':apks,'apex_count':len(apex),'apex':apex,'overlay_paths':overlays,'errors':errors,'patches_applied':[],'boot_compatibility':'NOT ASSESSED','system_ext_layout_note':'system_ext may be merged beneath system; no separate system_ext partition/image is assumed.','notes':['Duplicate SONAMEs are findings, not proof of harmful duplication.','Property and init inventory is not runtime validation.','HAL filename hints are heuristic only.','No modifications are performed.']}
 P(args.report).write_text(json.dumps(report,indent=2)+'\n')
 lines=['System-side Tree Audit','===================== ',f'Files: {len(files)} | ELF: {len(elf)} | APK: {len(apks)} | APEX: {len(apex)} | init services: {len(init_services)}','','Duplicate SONAME candidates:']
 for k,v in duplicates.items():lines += [f'- {k}: '+', '.join(v)]
 lines+=['','Conflicting property values:']
 for k,v in conflicts.items():lines += [f'- {k}: '+', '.join(f"{x['value']} ({x['file']}:{x['line']})" for x in v)]
 lines+=['','Init RC files:']+['- '+x for x in init]+['','Init services:']+['- '+x['name']+' ('+x['file']+':'+str(x['line'])+') -> '+x['command'] for x in init_services]+['','Linker config files:']+['- '+x['path'] for x in ldconfig]+['','Fstab candidates:']+['- '+x for x in fstab]+['','Init imports:']+['- '+x['file']+':'+str(x['line'])+' -> '+x['target'] for x in init_imports]+['','Init triggers:']+['- '+x['file']+':'+str(x['line'])+' -> '+x['trigger'] for x in init_actions]+['','HAL/service name hints:']+['- '+x for x in sorted(set(hal_hints))]+['','APEX inventory:']+['- '+x for x in apex]+['','APK inventory:']+['- '+x for x in apks]+['','Boot compatibility: NOT ASSESSED','No files were modified.']
 P(args.props_report).write_text('\n'.join(lines)+'\n')
 print(f'Audit complete: {args.report}; {args.props_report}; ELF={len(elf)}, duplicates={len(duplicates)}, property conflicts={len(conflicts)}, init services={len(init_services)}')
if __name__=='__main__':main()
