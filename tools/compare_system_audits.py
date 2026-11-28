#!/usr/bin/env python3
"""Compare target and donor system-tree audit inventories."""
import argparse,json,pathlib
def load(path):
 d=json.loads(pathlib.Path(path).read_text())
 if not isinstance(d.get('elf'),list):raise ValueError('Report lacks ELF inventory')
 return d
def idx(d):
 x={}
 for e in d['elf']:x.setdefault(e.get('soname') or pathlib.Path(e['path']).name,[]).append(e)
 return x
def compare(t,d):
 ti,di=idx(t),idx(d);req={n for e in t['elf'] for n in e.get('needed',[])}
 rows=[]
 for n in sorted(set(ti)&set(di)):
  rows.append({'soname':n,'target_paths':[e['path'] for e in ti[n]],'donor_paths':[e['path'] for e in di[n]],'abi_differences':[{'target':e['path'],'target_machine':e.get('machine'),'target_class':e.get('elf_class'),'donor':f['path'],'donor_machine':f.get('machine'),'donor_class':f.get('elf_class')} for e in ti[n] for f in di[n] if (e.get('machine'),e.get('elf_class'))!=(f.get('machine'),f.get('elf_class'))]})
 return {'schema':'a31-elf-report-comparison-v1','target_root':t.get('root'),'donor_root':d.get('root'),'missing_soname_names_in_donor':sorted(set(ti)-set(di)),'target_needed_names_missing_from_target_inventory':sorted(req-set(ti)),'target_needed_names_missing_from_donor_inventory':sorted(req-set(di)),'shared_soname_abi_evidence':rows,'interpretation':['Inventory only: not proof of loadability or incompatibility.','Android linker namespaces, partition visibility, symbol versions and runtime service wiring are not evaluated.'],'runtime_compatibility':'NOT ASSESSED'}
def main():
 p=argparse.ArgumentParser();p.add_argument('target');p.add_argument('donor');p.add_argument('--output',default='elf-compare.json');a=p.parse_args()
 r=compare(load(a.target),load(a.donor));pathlib.Path(a.output).write_text(json.dumps(r,indent=2)+'\\n');print('Wrote',a.output)
if __name__=='__main__':main()
