#!/usr/bin/env python3
"""Correlate boot-log events with system-tree audit evidence. Heuristic, read-only."""
import argparse,json,pathlib,re
def correlate(logdata,audit):
 events=logdata.get("events",[]);elf=audit.get("elf",[]);sonames={}
 for e in elf: sonames.setdefault(e.get("soname") or pathlib.Path(e["path"]).name,[]).append(e)
 services=audit.get("init_services",[]);props=audit.get("properties",[]);apex=audit.get("apex",[]);findings=[]
 for ev in events:
  typ=ev.get("type");line=ev.get("text","");matched=[]
  if typ in ("linker_missing","linker"):
   libs=re.findall(r"lib[\w.-]+\.so",line)
   for lib in libs:
    matched.append({"kind":"library_inventory" if lib in sonames else "missing_library_inventory_candidate","name":lib,"paths":[x["path"] for x in sonames[lib]] if lib in sonames else [],"evidence":"Inventory presence/absence only"})
   syms=re.findall(r"(?:cannot locate symbol|symbol)\s+['\"]?([\w@.-]+)",line,re.I)
   if syms:matched.append({"kind":"symbol_token","names":syms,"evidence":"Version/ABI resolution not assessed"})
  if typ in ("service_crash","init_service","init"):
   tokens=set(re.findall(r"[A-Za-z0-9_.-]+",line))
   for s in services:
    if s.get("name") in tokens or pathlib.Path(s.get("command","")).name in tokens:matched.append({"kind":"init_service_inventory","name":s["name"],"file":s["file"],"line":s["line"],"command":s["command"]})
  if typ in ("property","property_denial"):
   keys=re.findall(r"([A-Za-z0-9_.-]+)\s*=",line)
   for key in keys:
    vals=[p for p in props if p.get("key")==key]
    if vals:matched.append({"kind":"property_inventory","key":key,"entries":vals[:8]})
  if typ=="apex":
   names=[x for x in apex if any(t.lower() in x.lower() for t in re.findall(r"com\.[\w.]+",line))]
   if names:matched.append({"kind":"apex_path_match","paths":names})
  if matched:findings.append({"log_line":ev.get("line"),"event_type":typ,"log_excerpt":line[:300],"matches":matched})
 ranked=[]
 for f in findings:
  score=sum(3 if m["kind"]=="missing_library_inventory_candidate" else 2 for m in f["matches"])
  ranked.append({"score":score,"line":f["log_line"],"event_type":f["event_type"],"excerpt":f["log_excerpt"],"correlations":f["matches"],"ranking_note":"heuristic score only; chronology and correlation do not establish causality"})
 ranked.sort(key=lambda x:(-x["score"],x["line"] or 0))
 return {"schema":"a31-evidence-correlation-v1","event_count":len(events),"correlated_event_count":len(findings),"findings":findings,"ranked_review_candidates":ranked,"compatibility_status":"NOT ASSESSED","limitations":["Lexical/metadata correlations, not proof of runtime linkage.","No linker namespace or symbol-version resolution.","Init service matching uses name tokens.","No patch generated or files modified."]}
def main():
 p=argparse.ArgumentParser();p.add_argument("log_analysis");p.add_argument("system_audit");p.add_argument("--output",default="correlated-evidence.json");a=p.parse_args()
 r=correlate(json.loads(pathlib.Path(a.log_analysis).read_text()),json.loads(pathlib.Path(a.system_audit).read_text()))
 pathlib.Path(a.output).write_text(json.dumps(r,indent=2)+"\n");print(f"Correlated {r['correlated_event_count']} of {r['event_count']} events; review candidates: {len(r['ranked_review_candidates'])}")
if __name__=="__main__":main()
