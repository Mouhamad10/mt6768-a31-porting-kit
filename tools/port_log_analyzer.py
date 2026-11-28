#!/usr/bin/env python3
"""Multi-source Android port log analyzer and safe remediation planner.
Supports console, ramoops, pmsg/p-message, dmesg, logcat and mixed text.
It only creates reviewable patch plans; it never edits ROM trees itself.
"""
import argparse,json,pathlib,re,hashlib
PATTERNS=[
("selinux_denial",r"avc:\s*denied|\bSELinux.*denied", "SELinux","medium","Collect full denial context and map source/target contexts, class, permissions, and process domain. Avoid blanket permissive or allow-all rules."),
("linker_missing",r"cannot locate symbol|CANNOT LINK EXECUTABLE|dlopen failed|library .* not found|failed to load.*\.so", "Linker/ABI","high","Resolve the exact missing symbol/library against ABI, SONAME, DT_NEEDED and linker namespace. Do not copy arbitrary libraries."),
("duplicate_library",r"(duplicate|already loaded|conflict).*?(\.so|library)|same.*(SONAME|soname)", "ELF/Linker","low","Inventory paths, SONAME, hashes, namespaces and load order; duplicates are candidates, not proof of conflict."),
("service_crash",r"Fatal signal .* in .*|Service .* (crashed|died|exited)|pid .* (SIGSEGV|SIGABRT)|crash_dump", "Service crash","high","Correlate crash signature, process/service name, tombstone frames, restart count and dependency failures; don't disable essential services blindly."),
("apex",r"apexd.*(error|fail)|APEX.*(error|fail)|failed to activate.*apex", "APEX","medium","Check activation status, payload mount, manifest/version, dependencies, signatures and matching APEX init entries."),
("init",r"init:.*(failed|error)|cannot start .*service|service .* not found", "Init/service","medium","Check service definition, executable path, user/group, capabilities, rc import, property trigger and dependencies."),
("bootloop",r"reboot,bpfloader-failed|sys\.powerctl=.*reboot|shutdown_command|rebooting.*reason", "Reboot","high","Identify the earliest causal event before the reboot decision; treat teardown crashes as collateral."),
("mount",r"mount.*(failed|error)|fs_mgr.*(failed|error)|avb.*(fail|error)", "Mount/AVB","high","Check partition mapping, fstab flags, filesystem type, AVB chain and dynamic-partition metadata."),
("vintf",r"VINTF.*(mismatch|error|fail)|checkvintf.*(fail|error)|manifest.*matrix.*mismatch", "VINTF","medium","Compare framework/vendor manifests and compatibility matrix; confirm the exact interface instance and version."),
("property",r"property.*(denied|failed)|cannot set property|invalid property", "Property","medium","Validate property namespace, property_contexts, trigger consumer and runtime ownership."),
("zygote",r"zygote.*(fatal|crash|abort)|Zygote.*(fatal|crash)", "Zygote","high","Prioritize preceding linker, JNI, SELinux and runtime errors; preserve tombstone and stack context."),
("framework",r"system_server.*(fatal|crash|abort)|FATAL EXCEPTION IN SYSTEM SERVER", "Framework","high","Group repeated crashes by stack fingerprint; identify the first fatal exception and dependency chain."),
("storage",r"ENOSPC|no space left|inode.*(exhaust|full)|quota.*exceed", "Storage","medium","Check filesystem/inode capacity and logs before suggesting cleanup; avoid deleting user data."),
("permissions",r"Permission denied|EACCES", "Permissions","low","Determine whether denial is DAC, SELinux, namespace or mount policy; don't assume SELinux.")
]
SOURCE_TAGS=[
("pmsg",r"pmsg-ramoops|p-message|pmsg", "pmsg / p-message"),
("ramoops",r"ramoops|console-ramoops|dump_oops", "ramoops / console-ramoops"),
("console",r"console-ramoops|console log|kernel console", "console"),
("logcat",r"\b[VDIWEF]\s*[/(:]|\bAndroidRuntime\b|\bActivityManager\b", "logcat"),
("dmesg",r"\b(kernel:|\[\s*\d+\.\d+\]|Linux version|Call trace:)", "dmesg/kernel")
]
def analyze(text):
 lines=text.splitlines();events=[];sources=set();groups={}
 for n,line in enumerate(lines,1):
  for tag,rx,label in SOURCE_TAGS:
   if re.search(rx,line,re.I):sources.add(label)
  for typ,rx,area,sev,action in PATTERNS:
   if re.search(rx,line,re.I):
    fingerprint=re.sub(r"\b(?:pid|PID)\s*[:=]?\s*\d+\b","PID",line)
    fingerprint=re.sub(r"0x[0-9a-f]+","ADDR",fingerprint,flags=re.I)
    fingerprint=re.sub(r"\s+"," ",fingerprint).strip()[:180]
    events.append({"line":n,"type":typ,"area":area,"severity":sev,"text":line[:300],"action":action,"fingerprint":fingerprint})
    groups.setdefault((typ,fingerprint),[]).append(n);break
 clusters=[{"type":k[0],"fingerprint":k[1],"count":len(v),"first":v[0],"last":v[-1]} for k,v in groups.items()]
 clusters.sort(key=lambda x:(-x["count"],x["first"]))
 recommendations=[]
 for typ in sorted({e["type"] for e in events}):
  ev=[e for e in events if e["type"]==typ]
  recommendations.append({"category":typ,"occurrences":len(ev),"priority":"high" if any(e["severity"]=="high" for e in ev) else "review","next_step":ev[0]["action"]})
 return {"schema":"a31-port-log-analysis-v2","sources_detected":sorted(sources) or ["mixed/unknown text"],"line_count":len(lines),"events":events,"clusters":clusters,"recommendations":recommendations,"patch_plan":{"status":"review_only","proposals":[],"reason":"Analyzer emits evidence-based remediation plans; specific file edits require tree evidence, exact preconditions and validated recipes. No broad SELinux, service-disable or library-copy patches are generated from log text alone."},"limitations":["Source detection is heuristic; format tags may be absent or stripped.","A log line is evidence, not root-cause proof.","A crash may be collateral to an earlier reboot or dependency failure.","No files in the ROM are modified."]}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("log");p.add_argument("--json",default="port-log-analysis.json");p.add_argument("--markdown",default="port-log-analysis.md");a=p.parse_args()
 data=analyze(pathlib.Path(a.log).read_text(errors="replace"))
 pathlib.Path(a.json).write_text(json.dumps(data,indent=2)+"\n")
 md=["# Port Log Analysis","", "Sources detected: "+", ".join(data["sources_detected"]),"", "## Event clusters",""]
 for c in data["clusters"]:md.append(f"- **{c['type']}** ×{c['count']} (lines {c['first']}–{c['last']}): {c['fingerprint']}")
 md+=["","## Prioritized recommendations",""]
 for r in data["recommendations"]:md.append(f"- **{r['category']}** ({r['occurrences']} events; {r['priority']}): {r['next_step']}")
 md+=["","## Patch policy","Patch plan is review-only. Specific edits require inspected files, hash/path preconditions, rollback, and tests."]
 pathlib.Path(a.markdown).write_text("\n".join(md)+"\n")
 print(f"Lines: {data['line_count']} | Events: {len(data['events'])} | clusters: {len(data['clusters'])}")
if __name__=="__main__":main()
