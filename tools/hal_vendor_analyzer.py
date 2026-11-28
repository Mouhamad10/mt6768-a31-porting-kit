#!/usr/bin/env python3
"""Stage 11: evidence inventory of HAL/VINTF/vendor integration signals."""
import argparse,hashlib,json,pathlib,re,subprocess,shutil
PATTERNS={'vintf':['manifest*.xml','compatibility_matrix*.xml'],'hal':['*hal*.rc','*hal*.xml'],'linker':['ld.config*.txt','linker.config*.json'],'rc':['*.rc'],'sepolicy':['*.cil','*.te'],'lib':['*.so']}
def scan(root):
 root=pathlib.Path(root).resolve()
 if not root.is_dir():raise ValueError('tree must be a directory')
 files=[p for p in root.rglob('*') if p.is_file() and not p.is_symlink()]
 findings={'vintf':[],'hal_service_rc':[],'linker_config':[],'sepolicy':[],'libraries':[],'partition_and_mount_hints':[]}
 snippets=[]
 for p in files:
  rel=p.relative_to(root).as_posix();name=p.name.lower()
  try:text=p.read_text(errors='replace')
  except OSError:text=''
  if ('manifest' in name or 'compatibility_matrix' in name) and p.suffix.lower()=='.xml':findings['vintf'].append(rel)
  if p.suffix=='.rc' and re.search(r'(hal|vendor|service|camera|audio|radio|codec)',name,re.I):findings['hal_service_rc'].append(rel)
  if name.startswith('ld.config') or name.endswith('linker.config.json'):findings['linker_config'].append(rel)
  if p.suffix in ('.cil','.te'):findings['sepolicy'].append(rel)
  if p.suffix=='.so':
   try:
    data=p.read_bytes()
    if data[:4]==b'\x7fELF':findings['libraries'].append({'path':rel,'sha256':hashlib.sha256(data).hexdigest()})
   except OSError:pass
  if name.startswith('fstab') or 'mount' in name:findings['partition_and_mount_hints'].append(rel)
  if p.suffix.lower()=='.xml':
   for m in re.finditer(r'<\s*(hal|interface|name|version|fqname|instance|transport|service)\b[^>]*>',text,re.I):
    snippets.append({'file':rel,'line':text[:m.start()].count('\n')+1,'tag':m.group(1),'snippet':m.group(0)[:250]})
  elif p.suffix=='.rc':
   for m in re.finditer(r'(?m)^\s*(service|interface|import|on)\s+.*$',text):
    snippets.append({'file':rel,'line':text[:m.start()].count('\n')+1,'directive':m.group(0).strip()[:250]})
  elif p.suffix in ('.cil','.te'):
   for m in re.finditer(r'(?m)^\s*(type|typeattribute|allow|neverallow|permissive)\s+.*$',text):
    snippets.append({'file':rel,'line':text[:m.start()].count('\n')+1,'policy_statement':m.group(0).strip()[:250]})
 return {'root':str(root),'file_count':len(files),'evidence':findings,'xml_rc_policy_snippets':snippets,'assessment':'inventory_and_pattern_evidence_only','unknowns':['HAL service runtime registration','VINTF compatibility enforcement outcome','library ABI and symbol compatibility','SELinux policy compile and runtime behavior'],'no_changes_made':True}

def main():
 a=argparse.ArgumentParser();a.add_argument('tree');a.add_argument('--report',default='stage11-report.json');x=a.parse_args();r=scan(x.tree);pathlib.Path(x.report).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
