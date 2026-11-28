#!/usr/bin/env python3
"""Static inventory of Android linker config namespace directives; review-only."""
import argparse,json,pathlib,re

def scan(root):
 root=pathlib.Path(root);configs=[];sections=[]
 for p in sorted(root.rglob("*")):
  if not p.is_file() or p.is_symlink() or not (p.name.startswith("ld.config") or p.name in ("linker.config.json",)):continue
  try: text=p.read_text(errors="replace")
  except OSError: continue
  configs.append(str(p.relative_to(root)))
  current=None
  for n,line in enumerate(text.splitlines(),1):
   s=line.strip()
   if not s or s.startswith("#"):continue
   m=re.match(r'^\[([^]]+)\]$',s)
   if m:
    current=m.group(1);sections.append({"file":str(p.relative_to(root)),"section":current,"line":n,"directives":[]});continue
   if current and "=" in s:
    k,v=s.split("=",1);sections[-1]["directives"].append({"key":k.strip(),"value":v.strip(),"line":n})
 return {"schema":"a31-linker-namespace-audit-v1","config_files":configs,"sections":sections,"namespaces":[x for x in sections if x["section"].startswith("namespace.")],"limitations":["Static config parsing only; property expansion and runtime selection are not resolved.","This parser inventories section directives and does not prove namespace accessibility or successful dynamic loading."]}

def main():
 p=argparse.ArgumentParser();p.add_argument("tree");p.add_argument("--json",default="linker-namespace-audit.json");a=p.parse_args()
 r=scan(a.tree);pathlib.Path(a.json).write_text(json.dumps(r,indent=2)+"\n");print("Configs:",len(r["config_files"]),"namespace sections:",len(r["namespaces"]))
if __name__=="__main__":main()
