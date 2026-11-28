#!/usr/bin/env python3
"""Read-only orchestration pipeline for Android system-side port evidence."""
import argparse, json, pathlib, sys
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from port_log_analyzer import analyze
from evidence_correlator import correlate
from compatibility_evidence import report as compatibility_report
from subsystem_intelligence import inspect as subsystem_inspect
from vintf_compare import compare as vintf_compare
from elf_symbol_compare import compare as elf_symbol_compare
from linker_namespace_audit import scan as linker_namespace_scan

def run(log_text,target_audit,donor_audit=None):
 log=analyze(log_text);corr=correlate(log,target_audit)
 comp=compatibility_report(target_audit,donor_audit,corr) if donor_audit is not None else None
 ranked=[]
 for e in log.get("events",[]):
  matches=[f for f in corr.get("findings",[]) if f.get("log_line")==e.get("line")]
  score=(4 if e.get("severity")=="high" else 2 if e.get("severity")=="medium" else 1)+2*len(matches)
  ranked.append({"line":e.get("line"),"type":e.get("type"),"severity":e.get("severity"),"excerpt":e.get("text"),"action":e.get("action"),"correlations":matches,"priority_score":score,"ranking_note":"heuristic triage score, not causal attribution"})
 ranked.sort(key=lambda x:(-x["priority_score"],x["line"] or 0))
 return {"schema":"a31-port-evidence-pipeline-v3","log_analysis":log,"correlation":corr,"compatibility":comp,"subsystem_intelligence":subsystem_inspect(log,target_audit),"vintf_comparison":None,"elf_symbol_comparison":None,"linker_namespace_audit":None,"ranked_events":ranked,"patch_policy":{"status":"review_only","automatic_changes":False,"patches_generated":False},"limitations":["Scores and lexical correlations do not establish root cause.","Static VINTF, ELF and linker namespace inventories do not validate runtime compatibility or bootability.","Symbol comparison only compares files at identical relative paths.","No ROM files are modified."]}

def markdown(r):
 lines=["# Android Port Evidence Pipeline","> Read-only triage report. No changes or patches were applied.","","## Summary",f"- Log lines: {r['log_analysis']['line_count']}",f"- Events: {len(r['log_analysis']['events'])}",f"- Correlated events: {r['correlation']['correlated_event_count']}",f"- Donor audit: {'included' if r['compatibility'] else 'not supplied'}","","## Ranked events"]
 for x in r["ranked_events"]:lines.append(f"- **{x['priority_score']} | {x['severity']} | line {x['line']} | {x['type']}** — {x['excerpt']}\n  - Review: {x['action']}")
 v=r.get("vintf_comparison")
 if r.get("linker_namespace_audit"):
  ln=r["linker_namespace_audit"]; lines+=["","## Linker namespace config inventory",f"- Config files: {len(ln['config_files'])}",f"- Namespace sections: {len(ln['namespaces'])}"]
  for ns in ln["namespaces"]: lines.append(f"- {ns['file']} [{ns['section']}]")
 if v:
  lines+=["","## Static VINTF",f"- Donor-only: {len(v['donor_only_entries'])}",f"- Shared: {len(v['shared_entries'])}"]
  for x in v["donor_only_entries"]:lines.append(f"- {x['package']} / {x['interface']} / {x['instance']}")
 s=r.get("elf_symbol_comparison")
 if s:
  lines+=["","## Static ELF symbol comparison",f"- Matched paths: {s['matched_paths']}",f"- Files with symbol gaps: {len(s['symbol_gaps'])}"]
  for x in s["symbol_gaps"]:lines.append(f"- {x['path']}: {len(x['donor_exports_absent_in_target'])} donor exports absent in target")
 lines+=["","## Limitations","Review-only; heuristic correlations and static inventories are not proof of runtime compatibility. No patches applied."]
 return "\n".join(lines)+"\n"

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("log");p.add_argument("target_audit");p.add_argument("--donor-audit");p.add_argument("--tree",help="extracted target tree");p.add_argument("--donor-tree",help="extracted donor tree for static VINTF and ELF symbol comparison");p.add_argument("--json",default="port-evidence-pipeline.json");p.add_argument("--markdown",default="port-evidence-pipeline.md");a=p.parse_args()
 logtext=pathlib.Path(a.log).read_text(errors="replace");target=json.loads(pathlib.Path(a.target_audit).read_text());donor=json.loads(pathlib.Path(a.donor_audit).read_text()) if a.donor_audit else None
 r=run(logtext,target,donor)
 if a.tree:r["subsystem_intelligence"]=subsystem_inspect(r["log_analysis"],target,a.tree)
 if a.tree and a.donor_tree:
  r["vintf_comparison"]=vintf_compare(a.tree,a.donor_tree)
  r["elf_symbol_comparison"]=elf_symbol_compare(a.tree,a.donor_tree)
 pathlib.Path(a.json).write_text(json.dumps(r,indent=2)+"\n");pathlib.Path(a.markdown).write_text(markdown(r));print(f"Events: {len(r['log_analysis']['events'])} | ranked: {len(r['ranked_events'])}")
if __name__=="__main__":main()
