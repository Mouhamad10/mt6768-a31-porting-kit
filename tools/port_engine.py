#!/usr/bin/env python3
"""Evidence-driven A31 GSI/system port engine: diagnose logs, audit evidence, and propose guarded property repairs.

This is deliberately conservative: it never invents property values or edits files without a
recipe, a matching signature, and (for --apply) an exact recipe SHA precondition.
"""
import argparse, hashlib, json, pathlib, re, subprocess, sys
def sha(b): return hashlib.sha256(b).hexdigest()
def load_json(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
def scan(text, db):
 hits=[]; ids=set()
 for s in db.get("signatures",[]):
  matches=list(re.finditer(s["regex"],text,re.I|re.M))
  if matches:
   ids.add(s["id"]);hits.append({"id":s["id"],"name":s.get("name",s["id"]),"severity":s.get("severity","info"),"count":len(matches),"samples":[text[m.start():m.end()+120].splitlines()[0][:240] for m in matches[:3]],"meaning":s.get("meaning",""),"action":s.get("action",""),"fix":s.get("fix")})
 correlations=[c for c in db.get("correlations",[]) if all(i in ids for i in c.get("all",[]))]
 return hits,correlations,ids
def recipe_ops(root, recipes, ids):
 ops=[]; rejected=[]
 for r in recipes.get("recipes",[]):
  if not set(r.get("trigger_signatures",[])).intersection(ids):continue
  path=r.get("path","");key=r.get("key","")
  if r.get("type")!="set_property" or not path or not re.fullmatch(r"[A-Za-z0-9_.-]+",key):
   rejected.append({"recipe":r.get("id"),"reason":"unsupported or malformed recipe"});continue
  p=(root/path).resolve()
  if not p.is_relative_to(root.resolve()) or not p.is_file():
   rejected.append({"recipe":r.get("id"),"reason":"target missing or path escapes tree"});continue
  before=p.read_bytes()
  if sha(before)!=r.get("expected_sha256"):
   rejected.append({"recipe":r.get("id"),"reason":"SHA precondition does not match current target; no proposal generated"});continue
  ops.append({"op":"set_property","path":path,"key":key,"value":str(r["value"]),"expected_sha256":sha(before),"recipe_id":r.get("id"),"why":r.get("why","")})
 return ops,rejected
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument("log");a.add_argument("--tree");a.add_argument("--signatures",default=str(pathlib.Path(__file__).with_name("boot-signatures.json")));a.add_argument("--recipes");a.add_argument("--report",default="port-engine-report.json");a.add_argument("--patch",default="port-engine-proposal.json");a.add_argument("--apply",action="store_true");a.add_argument("--rollback-manifest",default="port-engine-rollback.json");x=a.parse_args()
 if x.apply and (not x.tree or not x.recipes):a.error("--apply requires --tree and --recipes")
 text=pathlib.Path(x.log).read_text(encoding="utf-8",errors="replace");db=load_json(x.signatures);hits,corr,ids=scan(text,db);root=pathlib.Path(x.tree).resolve() if x.tree else None
 ops,rejected=recipe_ops(root,load_json(x.recipes),ids) if root and x.recipes else ([],[])
 patch={"schema":"a31-system-patch-v1","operations":[{k:v for k,v in o.items() if k in ("op","path","key","value","expected_sha256")} for o in ops]}
 report={"schema":"a31-port-engine-report-v1","log":str(pathlib.Path(x.log)),"matched_signature_ids":sorted(ids),"diagnoses":hits,"correlations":corr,"repair_candidates":ops,"rejected_recipes":rejected,"status":"REPAIR_CANDIDATES_READY" if ops else "DIAGNOSIS_ONLY","guardrails":["Unknown log signatures are not auto-fixed.","No recipe means no edit.","Exact file SHA preconditions are mandatory.","Only property operations are supported.","system_ext is merged beneath system; no separate system_ext partition is assumed."]}
 pathlib.Path(x.report).write_text(json.dumps(report,indent=2)+"\n")
 if ops:pathlib.Path(x.patch).write_text(json.dumps(patch,indent=2)+"\n")
 print(f"Diagnoses: {len(hits)}; correlations: {len(corr)}; guarded candidates: {len(ops)}; rejected recipes: {len(rejected)}")
 if x.apply and ops:subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name("system_patch.py")),"apply",str(root),x.patch,"--rollback-manifest",x.rollback_manifest],check=True)
 elif x.apply:print("Nothing eligible; tree unchanged.")
if __name__=="__main__":main()
