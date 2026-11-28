#!/usr/bin/env python3
"""Integrated, read-only GSI intake pipeline: normalize, inspect and produce evidence gaps.
It deliberately does not mount images, modify source images, or infer boot compatibility.
"""
import argparse, hashlib, json, pathlib, shutil, subprocess, sys, time

def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def run_pipeline(src,out,limit):
 src=pathlib.Path(src).resolve();out=pathlib.Path(out).resolve()
 if not src.is_file():raise ValueError('input file missing')
 if src==out or src in out.parents or out in src.parents:raise ValueError('input/output paths must not overlap')
 out.mkdir(parents=True,exist_ok=True)
 normdir=out/'normalized'
 norm=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('gsi_extract.py')),str(src),str(normdir),'--max-bytes',str(limit)],capture_output=True,text=True)
 if norm.returncode:raise RuntimeError(norm.stderr.strip() or norm.stdout.strip() or 'normalization failed')
 normalized=normdir/'system.img'
 ins=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('gsi_fs_inspect.py')),str(normalized),'--json',str(out/'filesystem-inspection.json')],capture_output=True,text=True)
 if ins.returncode:raise RuntimeError(ins.stderr.strip() or 'filesystem inspection failed')
 inspect=json.loads((out/'filesystem-inspection.json').read_text())
 extract=json.loads((normdir/'extract-report.json').read_text())
 report={
  'schema':'a31-gsi-pipeline-report-v1',
  'input':{'path':str(src),'bytes':src.stat().st_size,'sha256':digest(src)},
  'normalization':extract,
  'filesystem_inspection':inspect,
  'readiness':{'input_normalized':True,'filesystem_metadata_inspected':inspect.get('inspection')!='signature_only' or inspect.get('filesystem')=='unknown','filesystem_contents_inventory':False,'vendor_and_device_context_supplied':False,'elf_and_vintf_audits':False,'compatibility_assessment':'insufficient_evidence','boot_test':'not_performed'},
  'evidence_gaps':['No extracted filesystem file inventory yet.','No A31 device/vendor baseline or VINTF/ELF comparison supplied to this run.','No runtime boot, hardware, or service validation performed.'],
  'safe_next_inputs':['A read-only filesystem tree inventory','A31 vendor/odm and VINTF/ELF audit datasets','Explicit target device build and partition context'],
  'safety':['Input preserved; normalization creates a separate output.','No mount or filesystem write operation.','No compatibility verdict or boot claim.']
 }
 (out/'pipeline-report.json').write_text(json.dumps(report,indent=2)+'\n')
 return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('output');p.add_argument('--max-bytes',type=int,default=8*1024**3);a=p.parse_args()
 try:
  if a.max_bytes<=0:raise ValueError('max-bytes must be positive')
  r=run_pipeline(a.input,a.output,a.max_bytes);print(json.dumps(r,indent=2))
 except Exception as e:print('ERROR: '+str(e),file=sys.stderr);sys.exit(2)
if __name__=='__main__':main()
