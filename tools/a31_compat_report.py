#!/usr/bin/env python3
"""Generate an evidence/unknowns compatibility report from a normalized image and optional tree scan."""
import argparse,json,pathlib
from gsi_prepare import fs_type
def report(image,tree=None):
 p=pathlib.Path(image);r={'device_target':'Samsung Galaxy A31 SM-A315F / MT6768','image':str(p),'size_bytes':p.stat().st_size,'filesystem':fs_type(p),'facts':[],'unknowns':['vendor HAL/API pairing','kernel ABI and driver compatibility','SELinux policy compatibility','boot behavior on hardware'],'tests':[],'status':'not_assessed','boot_test':'not_performed'}
 if tree:r['layout_scan']=str(pathlib.Path(tree))
 r['facts'].append('Filesystem signature detected by gsi_prepare.fs_type; this is not full filesystem validation.')
 return r
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('image');a.add_argument('--tree');a.add_argument('--json');x=a.parse_args();r=report(x.image,x.tree);s=json.dumps(r,indent=2);print(s)
 if x.json:pathlib.Path(x.json).write_text(s+'\n')
