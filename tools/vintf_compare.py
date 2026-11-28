#!/usr/bin/env python3
"""Compare static VINTF inventories extracted from manifest/matrix XML; review-only."""
import argparse,json,pathlib,xml.etree.ElementTree as ET

def inventory(root):
 items=[]
 for path in pathlib.Path(root).rglob("*.xml"):
  try: doc=ET.parse(path).getroot()
  except (OSError,ET.ParseError): continue
  for hal in doc.iter():
   if not hal.tag.endswith("hal"): continue
   name=hal.attrib.get("name")
   if not name: continue
   transport=hal.attrib.get("transport"); version=hal.attrib.get("version")
   for interface in hal.findall(".//interface"):
    iname=interface.attrib.get("name")
    if not iname: continue
    instances=[(x.text or "").strip() for x in interface.findall("instance") if (x.text or "").strip()]
    fqnames=[(x.text or "").strip() for x in interface.findall("fqname") if (x.text or "").strip()]
    for inst in instances or fqnames or ["(unspecified)"]:
     items.append({"package":name,"interface":iname,"instance":inst,"transport":transport,"version":version,"file":str(path.relative_to(root)),"root":doc.tag.split("}")[-1]})
 return items

def compare(target,donor):
 t=inventory(target);d=inventory(donor)
 keys=lambda x:(x["package"],x["interface"],x["instance"])
 tmap={keys(x):x for x in t};dmap={keys(x):x for x in d}
 missing=[dmap[k] for k in sorted(dmap.keys()-tmap.keys())]
 shared=[{"target":tmap[k],"donor":dmap[k],"metadata_difference":{f:{"target":tmap[k].get(f),"donor":dmap[k].get(f)} for f in ("transport","version") if tmap[k].get(f)!=dmap[k].get(f)}} for k in sorted(dmap.keys()&tmap.keys())]
 return {"schema":"a31-vintf-static-comparison-v1","target_entries":t,"donor_entries":d,"donor_only_entries":missing,"shared_entries":shared,"assessment":"static XML inventory comparison only","limitations":["Does not interpret full VINTF compatibility-matrix semantics, framework/device compatibility, SELinux, runtime service registration, or HAL implementation.","A donor-only entry is not proof the target must provide it; a shared entry is not proof compatibility. Review manifest and matrix context."]}

def main():
 p=argparse.ArgumentParser();p.add_argument("target_tree");p.add_argument("donor_tree");p.add_argument("--output",default="vintf-static-comparison.json");a=p.parse_args()
 r=compare(a.target_tree,a.donor_tree);pathlib.Path(a.output).write_text(json.dumps(r,indent=2)+"\n");print("Donor-only VINTF entries:",len(r["donor_only_entries"]))
if __name__=="__main__":main()
