#!/usr/bin/env python3
"""Structured subsystem triage: VINTF XML, linker config and event signatures (read-only)."""
import argparse,json,pathlib,re,xml.etree.ElementTree as ET

def inspect(log_data,audit,tree_root=None):
 events=log_data.get("events",[]);out={"schema":"a31-subsystem-intelligence-v1","vintf_inventory":[],"linker_config_inventory":[],"selinux_denials":[],"crash_signatures":[],"subsystem_hints":[],"limitations":["Static inventories and lexical log matching only.","No runtime service-manager, linker namespace, SELinux policy evaluation or VINTF compatibility check.","Findings are triage leads, not causal conclusions."]}
 root=pathlib.Path(tree_root).resolve() if tree_root else None
 if root and root.is_dir():
  for p in root.rglob("*.xml"):
   if p.is_file():
    try:
     txt=p.read_text(errors="replace")
     if any(x in txt.lower() for x in ("manifest","compatibility-matrix","hal")):
      try:
       doc=ET.fromstring(txt); entries=[]
       for node in doc.iter():
        if node.tag.endswith(("hal","interface","instance","fqname")):
         entries.append({"tag":node.tag.split("}")[-1],"name":node.attrib.get("name"),"value":(node.text or "").strip()[:160]})
       out["vintf_inventory"].append({"path":str(p.relative_to(root)),"root_tag":doc.tag.split("}")[-1],"entries":entries[:500],"parse_status":"ok"})
      except ET.ParseError as e:out["vintf_inventory"].append({"path":str(p.relative_to(root)),"parse_status":"error","error":str(e)})
    except OSError:pass
  for p in root.rglob("*"):
   if p.is_file() and ("ld.config" in p.name or p.name in ("linker.config.json","linker.config")):
    try:
     text=p.read_text(errors="replace");out["linker_config_inventory"].append({"path":str(p.relative_to(root)),"namespace_mentions":sorted(set(re.findall(r"(?m)^\s*(?:namespace\.[\w.-]+|\[namespace\.[\w.-]+\])",text))),"library_paths":sorted(set(re.findall(r"(?m)^\s*(?:search.paths|permitted.paths|namespace\.[\w.-]+\.search.paths)\s*=\s*(.+)$",text)))[:100],"sha256":__import__("hashlib").sha256(p.read_bytes()).hexdigest()})
    except OSError:pass
 for ev in events:
  line=ev.get("text","")
  if ev.get("type")=="selinux_denial" or re.search(r"avc:\\s*denied",line,re.I):
   tokens={}
   for key in ("scontext","tcontext","tclass","permissive"):
    m=re.search(r"\\b"+key+r"=([^\\s]+)",line);tokens[key]=m.group(1) if m else None
   perms=re.search(r"{([^}]+)}",line);tokens["permissions"]=perms.group(1).strip() if perms else None
   out["selinux_denials"].append({"line":ev.get("line"),"text":line[:500],"parsed":tokens})
  if ev.get("type") in ("service_crash","framework","zygote"):
   fp=ev.get("fingerprint") or line
   out["crash_signatures"].append({"line":ev.get("line"),"type":ev.get("type"),"fingerprint":fp[:200],"text":line[:400]})
  sub=None
  for token,subsystem in (("linker","linker/ELF"),("vintf","VINTF"),("apex","APEX"),("selinux","SELinux"),("zygote","Zygote/ART"),("system_server","Framework/System Server"),("init","Init")):
   if token in (ev.get("type","").lower()+" "+line.lower()):sub=subsystem;break
  if sub:out["subsystem_hints"].append({"line":ev.get("line"),"subsystem":sub,"event_type":ev.get("type"),"excerpt":line[:300]})
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument("log_analysis");p.add_argument("system_audit");p.add_argument("--tree");p.add_argument("--output",default="subsystem-intelligence.json");a=p.parse_args()
 r=inspect(json.loads(pathlib.Path(a.log_analysis).read_text()),json.loads(pathlib.Path(a.system_audit).read_text()),a.tree);pathlib.Path(a.output).write_text(json.dumps(r,indent=2)+"\n");print("Wrote subsystem evidence:",a.output)
if __name__=="__main__":main()
