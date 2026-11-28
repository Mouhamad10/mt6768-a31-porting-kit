#!/usr/bin/env python3
"""Integrated read-only GSI intake: normalize, inspect, optionally extract/audit.
No mounting, image writes, or automatic compatibility conclusions.
"""
import argparse, hashlib, json, pathlib, subprocess, sys

def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def audit_tree(tree,out):
 audit_path=out/'system-tree-audit.json';audit_text=out/'system-tree-audit.txt'
 audit_run=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('system_tree_audit.py')),str(tree),'--report',str(audit_path),'--props-report',str(audit_text)],capture_output=True,text=True)
 if audit_run.returncode:raise RuntimeError(audit_run.stderr.strip() or audit_run.stdout.strip() or 'tree audit failed')
 audit=json.loads(audit_path.read_text())
 return {'root':audit['root'],'file_count':audit['file_count'],'elf_count':audit['elf_count'],'apk_count':audit['apk_count'],'apex_count':audit['apex_count'],'init_service_count':len(audit['init_services']),'errors':len(audit['errors']),'boot_compatibility':audit.get('boot_compatibility','NOT ASSESSED'),'report':'system-tree-audit.json','text_report':'system-tree-audit.txt'}

def run_pipeline(src,out,limit,system_tree=None,extract_tree=False):
 src=pathlib.Path(src).resolve();out=pathlib.Path(out).resolve()
 if not src.is_file():raise ValueError('input file missing')
 if src==out or src in out.parents or out in src.parents:raise ValueError('input/output paths must not overlap')
 tree=pathlib.Path(system_tree).resolve() if system_tree else None
 if tree and (tree==src or tree in out.parents or out in tree.parents):raise ValueError('system-tree and output paths must not overlap')
 if tree and not tree.is_dir():raise ValueError('system-tree must be a directory')
 if extract_tree and tree:raise ValueError('choose supplied system-tree OR extraction, not both')
 out.mkdir(parents=True,exist_ok=True)
 normdir=out/'normalized'
 norm=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('gsi_extract.py')),str(src),str(normdir),'--max-bytes',str(limit)],capture_output=True,text=True)
 if norm.returncode:raise RuntimeError(norm.stderr.strip() or norm.stdout.strip() or 'normalization failed')
 normalized=normdir/'system.img'
 ins=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('gsi_fs_inspect.py')),str(normalized),'--json',str(out/'filesystem-inspection.json')],capture_output=True,text=True)
 if ins.returncode:raise RuntimeError(ins.stderr.strip() or 'filesystem inspection failed')
 inspect=json.loads((out/'filesystem-inspection.json').read_text())
 extract=json.loads((normdir/'extract-report.json').read_text())
 tree_summary=None;tree_source=None
 if extract_tree:
  tree=out/'extracted-tree'
  tree.mkdir(exist_ok=False)
  extraction=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('system_image_extract.py')),str(normalized),str(tree)],capture_output=True,text=True)
  if extraction.returncode:raise RuntimeError(extraction.stderr.strip() or extraction.stdout.strip() or 'filesystem extraction failed')
  tree_summary=audit_tree(tree,out);tree_source='normalized_image_read_only_extraction'
 elif tree:
  tree_summary=audit_tree(tree,out);tree_source='user_supplied_tree'
 report={
  'schema':'a31-gsi-pipeline-report-v3',
  'input':{'path':str(src),'bytes':src.stat().st_size,'sha256':digest(src)},
  'normalization':extract,
  'filesystem_inspection':inspect,
  'system_tree_audit':tree_summary,
  'tree_source':tree_source,
  'readiness':{'input_normalized':True,'filesystem_metadata_inspected':inspect.get('inspection') not in ('signature_only',None),'filesystem_contents_inventory':bool(tree_summary),'vendor_and_device_context_supplied':False,'elf_inventory_available':bool(tree_summary),'elf_and_vintf_comparisons':False,'compatibility_assessment':'insufficient_evidence','boot_test':'not_performed'},
  'evidence_gaps':['No A31 vendor/device baseline or VINTF comparison supplied.','No runtime boot, hardware, or service validation performed.'],
  'safe_next_inputs':['A31 vendor/odm and VINTF/ELF baseline data','Target device build and partition context'],
  'safety':['Input preserved; normalization creates a separate output.','No image mounting or writes. Extraction uses the read-only helper into a new empty output directory.','No compatibility verdict or boot claim.']
 }
 (out/'pipeline-report.json').write_text(json.dumps(report,indent=2)+'\n')
 return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('output');p.add_argument('--max-bytes',type=int,default=8*1024**3);p.add_argument('--system-tree',help='Optional separately extracted system-side directory to audit');p.add_argument('--extract-tree',action='store_true',help='Explicitly extract normalized filesystem to output/extracted-tree, then audit');a=p.parse_args()
 try:
  if a.max_bytes<=0:raise ValueError('max-bytes must be positive')
  r=run_pipeline(a.input,a.output,a.max_bytes,a.system_tree,a.extract_tree);print(json.dumps(r,indent=2))
 except Exception as e:print('ERROR: '+str(e),file=sys.stderr);sys.exit(2)
if __name__=='__main__':main()
