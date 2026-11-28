#!/usr/bin/env python3
"""Build non-applicable, review-only guarded patch recipe drafts from tree paths."""
import argparse,hashlib,json,pathlib
def draft(root,paths):
 root=pathlib.Path(root).resolve();items=[]
 for rel in paths:
  p=(root/rel).resolve()
  if not p.is_relative_to(root):raise ValueError("path escapes tree: "+rel)
  if not p.is_file():raise ValueError("not a regular file: "+rel)
  b=p.read_bytes()
  try:b.decode("utf-8")
  except UnicodeDecodeError:raise ValueError("drafts only support UTF-8 text files: "+rel)
  items.append({"path":rel,"expected_sha256":hashlib.sha256(b).hexdigest(),"op":"replace_exact","before_text":"","after_text":"","why":"REQUIRES HUMAN EVIDENCE AND REVIEW","status":"INCOMPLETE_NOT_APPLICABLE"})
 return {"schema":"a31-system-patch-draft-v1","status":"draft_only","tree":str(root),"operations":items,"instructions":["Fill before_text and after_text with exact intended text.","Ensure before_text is unique and appropriate; apply tool will check uniqueness.","Do not apply until reviewed and validated against the relevant Android subsystem.","Draft schema is deliberately incompatible with apply schema until manually converted.","No files changed."]}
def main():
 p=argparse.ArgumentParser();p.add_argument("tree");p.add_argument("paths",nargs="+");p.add_argument("--output",default="patch-draft.json");a=p.parse_args()
 r=draft(a.tree,a.paths);pathlib.Path(a.output).write_text(json.dumps(r,indent=2)+"\n");print("Created incomplete review-only draft:",a.output)
if __name__=="__main__":main()
