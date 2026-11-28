#!/usr/bin/env python3
"""Read-only orchestration pipeline for Android system-side port evidence."""
import argparse, json, pathlib, sys
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from port_log_analyzer import analyze
from evidence_correlator import correlate
from compatibility_evidence import report as compatibility_report

def run(log_text,target_audit,donor_audit=None):
 log=analyze(log_text)
 corr=correlate(log,target_audit)
 comp=compatibility_report(target_audit,donor_audit,corr) if donor_audit is not None else None
 ranked=[]
 for e in log.get("events",[]):
  base={"line":e.get("line"),"type":e.get("type"),"severity":e.get("severity"),"excerpt":e.get("text"),"action":e.get("action")}
  matches=[f for f in corr.get("findings",[]) if f.get("log_line")==e.get("line")]
  base["correlations"]=matches
  base["priority_score"]=(4 if e.get("severity")=="high" else 2 if e.get("severity")=="medium" else 1)+sum(2 for m in matches)
  base["ranking_note"]="heuristic triage score, not causal attribution"
  ranked.append(base)
 ranked.sort(key=lambda x:(-x["priority_score"],x["line"] or 0))
 return {"schema":"a31-port-evidence-pipeline-v1","log_analysis":log,"correlation":corr,"compatibility":comp,"ranked_events":ranked,"patch_policy":{"status":"review_only","automatic_changes":False,"patches_generated":False},"limitations":["Scores prioritize review and do not prove root cause.","Correlations are lexical/inventory-based; runtime behavior is not validated.","Compatibility evidence is incomplete and is not a bootability verdict.","No ROM files are modified."]}

def markdown(r):
 lines=["# Android Port Evidence Pipeline","","> Read-only triage report. No changes or patches were applied.","","## Summary","",f"- Log lines: {r['log_analysis']['line_count']}",f"- Detected events: {len(r['log_analysis']['events'])}",f"- Correlated events: {r['correlation']['correlated_event_count']}",f"- Donor comparison: {'included' if r['compatibility'] else 'not supplied'}","","## Ranked events",""]
 for x in r["ranked_events"]:
  lines.append(f"- **Score {x['priority_score']} | {x['severity']} | line {x['line']} | {x['type']}** — {x['excerpt']}")
  lines.append("  - Review: "+x["action"])
 if r["compatibility"]:
  lines += ["","## Compatibility evidence",f"- Assessment: {r['compatibility']['assessment']}",f"- Gap findings: {len(r['compatibility']['gap_findings'])}",""]
  for g in r["compatibility"]["gap_findings"]: lines.append(f"- **{g['severity']} / {g['category']} / {g['name']}** — {g['note']}")
 lines += ["","## Safety and limitations","- Patch generation/application is deliberately excluded from this pipeline.","- Correlation and score are heuristic; confirm against device logs and subsystem documentation."]
 return "\n".join(lines)+"\n"

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("log");p.add_argument("target_audit");p.add_argument("--donor-audit");p.add_argument("--json",default="port-evidence-pipeline.json");p.add_argument("--markdown",default="port-evidence-pipeline.md");a=p.parse_args()
 log_text=pathlib.Path(a.log).read_text(errors="replace");target=json.loads(pathlib.Path(a.target_audit).read_text());donor=json.loads(pathlib.Path(a.donor_audit).read_text()) if a.donor_audit else None
 r=run(log_text,target,donor);pathlib.Path(a.json).write_text(json.dumps(r,indent=2)+"\n");pathlib.Path(a.markdown).write_text(markdown(r));print(f"Events: {len(r['log_analysis']['events'])} | ranked: {len(r['ranked_events'])} | donor: {'yes' if donor else 'no'}")
if __name__=="__main__":main()
