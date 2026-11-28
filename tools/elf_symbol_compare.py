#!/usr/bin/env python3
"""Static ELF dynamic-symbol inventory/comparison using readelf output; review only."""
import argparse,json,pathlib,subprocess

def read_symbols(path):
 try: out=subprocess.run(["readelf","--dyn-syms","--wide",str(path)],capture_output=True,text=True,check=True).stdout
 except (OSError,subprocess.CalledProcessError): return {"error":"readelf unavailable or failed","symbols":[]}
 symbols=[]
 for line in out.splitlines():
  parts=line.split()
  if len(parts)<8 or not parts[0].rstrip(":").isdigit(): continue
  # readelf columns: Num Value Size Type Bind Vis Ndx Name
  typ,bind,vis,ndx,name=parts[3],parts[4],parts[5],parts[6],parts[7]
  if name=="":continue
  version=None
  if "@@" in name: name,version=name.split("@@",1)
  elif "@" in name:name,version=name.split("@",1)
  symbols.append({"name":name,"version":version,"type":typ,"binding":bind,"visibility":vis,"defined":ndx!="UND","index":ndx})
 return {"symbols":symbols}

def scan(root):
 root=pathlib.Path(root);items=[]
 for p in sorted(root.rglob("*")):
  if p.is_file() and not p.is_symlink():
   try: data=p.open("rb").read(4)
   except OSError:continue
   if data!=b"\x7fELF":continue
   r=read_symbols(p)
   if "error" in r:items.append({"path":str(p.relative_to(root)),"error":r["error"]});continue
   items.append({"path":str(p.relative_to(root)),"symbols":r["symbols"]})
 return items

def compare(target,donor):
 t=scan(target);d=scan(donor);tmap={x["path"]:x for x in t};dmap={x["path"]:x for x in d};results=[]
 for path in sorted(tmap.keys()&dmap.keys()):
  if "symbols" not in tmap[path] or "symbols" not in dmap[path]:continue
  ts=tmap[path]["symbols"];ds=dmap[path]["symbols"]
  # Focus on defined global/weak symbols; raw exports are a static clue only.
  key=lambda s:(s["name"],s["version"],s["type"])
  te={key(s) for s in ts if s["defined"] and s["binding"] in ("GLOBAL","WEAK")}
  de={key(s) for s in ds if s["defined"] and s["binding"] in ("GLOBAL","WEAK")}
  missing=sorted(de-te)
  if missing:results.append({"path":path,"donor_exports_absent_in_target":[{"name":x[0],"version":x[1],"type":x[2]} for x in missing]})
 return {"schema":"a31-elf-symbol-compare-v1","target_files":len(t),"donor_files":len(d),"matched_paths":len(set(str(p.relative_to(target)) for p in pathlib.Path(target).rglob("*") if p.is_file() and not p.is_symlink()) & set(str(p.relative_to(donor)) for p in pathlib.Path(donor).rglob("*") if p.is_file() and not p.is_symlink())),"symbol_gaps":results,"limitations":["Only compares files with identical relative paths; renamed or differently packaged libraries are not matched.","readelf dynsym inventory is static; symbol ABI, calling conventions, namespace visibility, relocation behavior and runtime loading are not validated.","A donor export absent in target is not necessarily required by the target ROM.","Not a substitute for linker/runtime testing."]}

def main():
 p=argparse.ArgumentParser();p.add_argument("target");p.add_argument("donor");p.add_argument("--json",default="elf-symbol-compare.json");a=p.parse_args()
 r=compare(a.target,a.donor);pathlib.Path(a.json).write_text(json.dumps(r,indent=2)+"\n");print("Matched paths:",r["matched_paths"],"files with symbol gaps:",len(r["symbol_gaps"]))
if __name__=="__main__":main()
