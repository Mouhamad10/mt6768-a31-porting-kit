#!/usr/bin/env python3
"""Evidence-driven system port triage with guarded, recipe-backed property edits only."""
import argparse, hashlib, json, pathlib, re, subprocess, sys
def sha(b): return hashlib.sha256(b).hexdigest()
def load_json(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
def scan(text,db):
 hits=[];ids=set()
 for s in db.get("signatures",[]):
  try: matches=list(re.finditer(s["regex"],text,re.I|re.M))
  except (KeyError,re.error) as e: raise ValueError("invalid signature entry/regex: "+str(e))
  if matches:
   sid=s.get("id")
   if sid: ids.add(sid)
   hits.append({"id":sid,"name":s.get("name",sid),"severity":s.get("severity","info"),"count":len(matches),"samples":[text[m.start():text.find("\n",m.start()) if text.find("\n",m.start())>=0 else len(text)][:240] for m in matches[:3]],"meaning":s.get("meaning",""),"action":s.get("action",""),"fix":s.get("fix")})
 correlations=[c for c in db.get("correlations",[]) if all(i in ids for i in c.get("all",[]))]
 return hits,correlations,ids
def recipe_ops(root,recipes,ids):
 ops=[];rejected=[];seen=set();root=root.resolve()
 for r in recipes.get("recipes",[]):
  rid=r.get("id","unnamed")
  try:
   if not set(r.get("trigger_signatures",[])).intersection(ids):continue
   path=r.get("path","");key=r.get("key","")
   typ=r.get("type")
   valid=(typ=="set_property" and re.fullmatch(r"[A-Za-z0-9_.-]+",key) and "value" in r) or (typ=="replace_exact" and isinstance(r.get("before_text"),str) and isinstance(r.get("after_text"),str) and r.get("before_text") and r.get("before_text")!=r.get("after_text"))
   if not valid or not path or not r.get("expected_sha256"):
    rejected.append({"recipe":rid,"reason":"malformed/unsupported; requires supported operation, relative path, SHA, trigger and operation fields"});continue
   p=(root/path).resolve()
   if not p.is_relative_to(root) or not p.is_file():
    rejected.append({"recipe":rid,"reason":"target missing or path escapes tree"});continue
   if p in seen:
    rejected.append({"recipe":rid,"reason":"duplicate target file; combine property operations in one recipe to avoid ambiguous preconditions"});continue
   before=p.read_bytes()
   if sha(before)!=r["expected_sha256"]:
    rejected.append({"recipe":rid,"reason":"SHA precondition mismatch"});continue
   seen.add(p);if typ=="set_property": op={"op":typ,"path":path,"key":key,"value":str(r["value"])}
   else:
    count=p.read_text(encoding="utf-8").count(r["before_text"])
    if count!=1:
     rejected.append({"recipe":rid,"reason":f"before_text must occur exactly once (found {count})"});continue
    op={"op":typ,"path":path,"before_text":r["before_text"],"after_text":r["after_text"]}
   op["expected_sha256"]=sha(before);op["recipe_id"]=rid;op["why"]=r.get("why","");ops.append(op)
  except (TypeError,ValueError,KeyError) as e: rejected.append({"recipe":rid,"reason":"invalid recipe data: "+str(e)})
 return ops,rejected
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument("log");a.add_argument("--tree");a.add_argument("--signatures",default=str(pathlib.Path(__file__).with_name("boot-signatures.json")));a.add_argument("--recipes");a.add_argument("--report",default="port-engine-report.json");a.add_argument("--patch",default="port-engine-proposal.json");a.add_argument("--apply",action="store_true");a.add_argument("--rollback-manifest",default="port-engine-rollback.json");x=a.parse_args()
 if x.apply and (not x.tree or not x.recipes):a.error("--apply requires --tree and --recipes")
 text=pathlib.Path(x.log).read_text(encoding="utf-8",errors="replace");db=load_json(x.signatures);hits,corr,ids=scan(text,db);root=pathlib.Path(x.tree).resolve() if x.tree else None
 ops,rejected=recipe_ops(root,load_json(x.recipes),ids) if root and x.recipes else ([],[])
 patch={"schema":"a31-system-patch-v1","operations":[{k:v for k,v in o.items() if k in ("op","path","key","value","before_text","after_text","expected_sha256")} for o in ops]}
 report={"schema":"a31-port-engine-report-v1","log":str(pathlib.Path(x.log)),"matched_signature_ids":sorted(ids),"diagnoses":hits,"correlations":corr,"repair_candidates":ops,"rejected_recipes":rejected,"status":"REPAIR_CANDIDATES_READY" if ops else "DIAGNOSIS_ONLY","guardrails":["Unknown signatures remain diagnostic-only.","Recipes must explicitly match and hash-lock files.","Supported edits: property set and unique literal text replacement; both SHA-locked.","Review generated reports/proposals before applying.","system_ext is merged beneath system; no separate system_ext partition assumed."]}
 pathlib.Path(x.report).write_text(json.dumps(report,indent=2)+"\n")
 if ops:pathlib.Path(x.patch).write_text(json.dumps(patch,indent=2)+"\n")
 print(f"Diagnoses: {len(hits)}; correlations: {len(corr)}; guarded candidates: {len(ops)}; rejected recipes: {len(rejected)}")
 if x.apply and ops:subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name("system_patch.py")),"apply",str(root),x.patch,"--rollback-manifest",x.rollback_manifest],check=True)
 elif x.apply:print("Nothing eligible; tree unchanged.")
if __name__=="__main__":main()
