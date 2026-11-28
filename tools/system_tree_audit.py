#!/usr/bin/env python3
"""Evidence-first Android system-tree analyzer and conservative patch planner."""
import argparse, collections, json, os, pathlib, re, subprocess, hashlib
P=pathlib.Path
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('tree');ap.add_argument('--report',default='system-audit.json');ap.add_argument('--props-report',default='system-audit.txt');args=ap.parse_args()
 root=P(args.tree); assert root.is_dir(), 'Expected extracted system directory'
 files=[p for p in root.rglob('*') if p.is_file() or p.is_symlink()]
 libs=[p for p in files if p.name.endswith('.so')]
 sonames=collections.defaultdict(list); elf=[]; errors=[]; props=[]; init=[]; apks=[]; apex=[]; overlays=[]
 for p in libs:
  try:
   if p.is_symlink(): continue
   head=p.read_bytes()[:4]
   if head!=b'\\x7fELF': continue
   out=subprocess.run(['readelf','-d',str(p)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
   m=re.search(r'\\(SONAME\\).*\\[(.*?)\\]',out); soname=m.group(1) if m else p.name
   need=re.findall(r'\\(NEEDED\\).*\\[(.*?)\\]',out)
   sonames[soname].append(str(p.relative_to(root)))
   elf.append({'path':str(p.relative_to(root)),'soname':soname,'needed':need,'sha256':sha(p)})
  except Exception as e:errors.append({'path':str(p),'error':str(e)})
 for p in files:
  rel=str(p.relative_to(root))
  if p.name.endswith('.prop'):
   try:
    for ln,line in enumerate(p.read_text(errors='ignore').splitlines(),1):
     if line.strip() and not line.strip().startswith('#') and '=' in line:props.append({'file':rel,'line':ln,'key':line.split('=',1)[0].strip(),'value':line.split('=',1)[1].strip()})
   except Exception:pass
  if p.name in ('init.rc',) or p.name.startswith('init.') and p.name.endswith('.rc'):init.append(rel)
  if p.suffix=='.apk':apks.append(rel)
  if p.suffix=='.apex':apex.append(rel)
  if 'overlay' in p.parts: overlays.append(rel)
 duplicates={k:v for k,v in sonames.items() if len(v)>1}
 # Deliberately report evidence, don't auto-delete duplicate SONAMEs: ABI/namespace and partition precedence matter.
 propgroups=collections.defaultdict(list)
 for x in props:propgroups[x['key']].append(x)
 conflicts={k:v for k,v in propgroups.items() if len(set(x['value'] for x in v))>1}
 report={'schema':'a31-system-audit-v1','root':str(root),'file_count':len(files),'elf_count':len(elf),'elf':elf,'duplicate_sonames':duplicates,'property_conflicts':conflicts,'properties':props,'init_rc':init,'apk_count':len(apks),'apks':apks,'apex_count':len(apex),'apex':apex,'overlay_paths':overlays,'errors':errors,'patches_applied':[],'boot_compatibility':'NOT ASSESSED','notes':['Duplicate SONAMEs are findings, not proof of harmful duplication. No automatic library deletion.','Property collisions are partition/precedence dependent. No property was changed automatically.','HAL client/service inventory is informational; implementation availability must be checked against vendor and device logs.']}
 P(args.report).write_text(json.dumps(report,indent=2))
 lines=['A31 System-tree Audit','====================',f'Files: {len(files)} | ELF: {len(elf)} | APK: {len(apks)} | APEX: {len(apex)}','', 'Duplicate SONAME candidates:']
 for k,v in duplicates.items():lines += [f'- {k}: '+', '.join(v)]
 lines+=['','Conflicting property values:']
 for k,v in conflicts.items():lines += [f'- {k}: '+', '.join(f"{x['value']} ({x['file']}:{x['line']})" for x in v)]
 lines+=['','Init rc files:']+['- '+x for x in init]+['','APEX inventory:']+['- '+x for x in apex]+['','APK inventory:']+['- '+x for x in apks]+['','Boot compatibility: NOT ASSESSED','No auto-removal of libraries or service/HAL disabling. Findings require boot-log correlation and device/vendor context.']
 P(args.props_report).write_text('\\n'.join(lines)+'\\n')
 print(f'Audit complete: {args.report}; {args.props_report}; ELF={len(elf)}, duplicate SONAMEs={len(duplicates)}, property conflicts={len(conflicts)}')
if __name__=='__main__':main()
