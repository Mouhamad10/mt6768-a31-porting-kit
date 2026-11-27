#!/usr/bin/env python3
"""Read-only scan of extracted system trees for partition/mount and fstab references."""
import argparse,json,pathlib,re
PATTERNS=(r'\b(system|system_ext|product|vendor|odm|vendor_dlkm|odm_dlkm)\b',r'first_stage_mount',r'logical',r'\bmount\b',r'\bfstab\b')
def scan(root):
 root=pathlib.Path(root); out=[]; rx=re.compile('|'.join(PATTERNS),re.I)
 for p in root.rglob('*'):
  if not p.is_file() or p.stat().st_size>2*1024*1024: continue
  try: lines=p.read_text(errors='replace').splitlines()
  except OSError: continue
  for n,line in enumerate(lines,1):
   if rx.search(line):out.append({'path':str(p.relative_to(root)),'line':n,'text':line[:500]})
 return {'root':str(root),'matches':out,'note':'heuristic textual references only; not a partition map or compatibility verdict'}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('root');a.add_argument('--json');x=a.parse_args();r=scan(x.root);s=json.dumps(r,indent=2);print(s)
 if x.json:pathlib.Path(x.json).write_text(s+'\n')
