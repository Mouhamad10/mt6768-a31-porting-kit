#!/usr/bin/env python3
"""Evidence-driven system-side compatibility gap report; never declares boot compatibility."""
import argparse,json,pathlib
def report(target,donor,correlated=None):
 telf=target.get("elf",[]);delf=donor.get("elf",[]);tidx={e.get("soname") or pathlib.Path(e["path"]).name:e for e in telf};didx={}
 for e in delf:didx.setdefault(e.get("soname") or pathlib.Path(e["path"]).name,[]).append(e)
 required={n for e in telf for n in e.get("needed",[])}
 gaps=[]
 for n in sorted(required):
  if n not in tidx:gaps.append({"category":"target_dependency_inventory_gap","name":n,"severity":"high","note":"Needed dependency not represented in target ELF inventory; audit scope may be incomplete"})
  if n not in didx:gaps.append({"category":"donor_dependency_gap","name":n,"severity":"medium","note":"No donor SONAME candidate; donor tree may not provide this dependency"})
  else:
   for x in didx[n]:
    if x.get("machine") or x.get("elf_class"):
     targets=[e for e in telf if (e.get("soname") or pathlib.Path(e["path"]).name)==n]
     if targets and any((e.get("machine"),e.get("elf_class"))!=(x.get("machine"),x.get("elf_class")) for e in targets):
      gaps.append({"category":"abi_metadata_difference","name":n,"severity":"high","target":[{"machine":e.get("machine"),"class":e.get("elf_class")} for e in targets],"donor":{"machine":x.get("machine"),"class":x.get("elf_class")},"note":"Metadata mismatch; not a loadability verdict"})
 dup={k:v for k,v in target.get("duplicate_sonames",{}).items()}
 init_names={x.get("name") for x in target.get("init_services",[])}
 don_init={x.get("name") for x in donor.get("init_services",[])}
 return {"schema":"a31-system-compatibility-evidence-v1","target_root":target.get("root"),"donor_root":donor.get("root"),"required_dependency_count":len(required),"gap_findings":gaps,"duplicate_target_soname_candidates":dup,"init_service_names_target_only":sorted(init_names-don_init),"init_service_names_donor_only":sorted(don_init-init_names),"correlated_log_findings":(correlated or {}).get("findings",[]),"assessment":"EVIDENCE GAPS ONLY — runtime compatibility and bootability NOT ASSESSED","limitations":["ELF inventory cannot evaluate Android linker namespaces, symbol versions, SELinux, VINTF, HAL runtime or API behavior.","Init service name differences alone are not proof of incompatibility.","Donor presence does not establish suitability for copying or replacing.","Input audits may cover only selected partition trees."]}
def main():
 p=argparse.ArgumentParser();p.add_argument("target");p.add_argument("donor");p.add_argument("--correlated");p.add_argument("--output",default="compatibility-evidence.json");a=p.parse_args()
 t=json.loads(pathlib.Path(a.target).read_text());d=json.loads(pathlib.Path(a.donor).read_text());c=json.loads(pathlib.Path(a.correlated).read_text()) if a.correlated else None
 r=report(t,d,c);pathlib.Path(a.output).write_text(json.dumps(r,indent=2)+"\n");print("Wrote evidence-only compatibility report:",a.output)
if __name__=="__main__":main()
