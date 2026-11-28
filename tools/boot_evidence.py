#!/usr/bin/env python3
"""Extract bounded, ordered evidence events from Android/Linux boot logs. No repairs."""
import argparse, json, pathlib, re
RULES=[
 ("kernel_fault",re.compile(r"Kernel panic - not syncing|Unable to handle kernel|Internal error: Oops|BUG: unable to handle kernel",re.I),"high"),
 ("tombstone",re.compile(r"Fatal signal [0-9]+|tombstoned|\bSIG(SEGV|ABRT|BUS|ILL)\b",re.I),"medium"),
 ("reboot",re.compile(r"reboot[, :]|shutdown_command|sys.powerctl|sec_reboot",re.I),"medium"),
 ("linker_missing",re.compile(r"cannot locate symbol|library .* not found|dlopen failed|CANNOT LINK EXECUTABLE",re.I),"medium"),
 ("selinux_denial",re.compile(r"avc: *denied|\bSELinux.*denied",re.I),"low"),
 ("init_service",re.compile(r"Service .* (exited with status|failed)|init: .*failed",re.I),"low"),
 ("apex_failure",re.compile(r"APEX.*(fail|error)|apexd.*(fail|error)",re.I),"low"),
]
def extract(text,limit=240):
 events=[]
 for i,line in enumerate(text.splitlines(),1):
  for kind,rx,confidence in RULES:
   if rx.search(line):
    events.append({"line":i,"type":kind,"confidence":confidence,"text":line[:limit]})
    break
 clusters={}
 for e in events:
  key=(e["type"],re.sub(r"\b(?:pid|PID)\s*[:=]?\s*\d+\b","PID",e["text"]))
  clusters.setdefault(key,[]).append(e["line"])
 summary=[{"type":k[0],"fingerprint":k[1][:180],"count":len(v),"first_line":v[0],"last_line":v[-1]} for k,v in clusters.items()]
 summary.sort(key=lambda x:x["first_line"])
 return {"schema":"a31-boot-evidence-v1","event_count":len(events),"events":events,"clusters":summary,
 "limitations":["Line-based extraction, not causal proof.","Log timestamps may be absent or incomparable; order uses input line numbers only.","An event is not necessarily a root cause; teardown events may be collateral.","No device changes or patch generation."]}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("log");p.add_argument("--output",default="boot-evidence.json");p.add_argument("--max-events",type=int,default=10000);a=p.parse_args()
 if a.max_events<1:p.error("--max-events must be positive")
 result=extract(pathlib.Path(a.log).read_text(encoding="utf-8",errors="replace"))
 if len(result["events"])>a.max_events:
  result["events"]=result["events"][:a.max_events];result["event_count"]=len(result["events"]);result["truncated"]=True
 pathlib.Path(a.output).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
 print("Evidence events: %d; clusters: %d"%(result["event_count"],len(result["clusters"])))
if __name__=="__main__":main()
