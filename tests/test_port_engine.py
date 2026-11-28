import json,pathlib,subprocess,tempfile,hashlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];TOOL=ROOT/'tools/port_engine.py';SIG=ROOT/'tools/boot-signatures.json'
class EngineTests(unittest.TestCase):
 def log(self,p):f=p/'log';f.write_text('CRITICAL FAILURE LOADING BPF PROGRAMS\nreboot,bpfloader-failed\n');return f
 def run_engine(self,p,log,tree=None,recipes=None,apply=False):
  cmd=['python3',str(TOOL),str(log),'--report',str(p/'r.json'),'--patch',str(p/'patch.json')]
  if tree:cmd+=['--tree',str(tree)]
  if recipes:cmd+=['--recipes',str(recipes)]
  if apply:cmd+=['--apply','--rollback-manifest',str(p/'rb.json')]
  subprocess.run(cmd,check=True);return json.loads((p/'r.json').read_text())
 def test_diagnosis_correlation(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);d=self.run_engine(p,self.log(p));self.assertIn('netbpf-load-fail',d['matched_signature_ids']);self.assertIn('bpfloader-reboot',d['matched_signature_ids']);self.assertTrue(d['correlations'])
 def test_proposal_apply_and_rollback(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);tree=p/'tree';tree.mkdir();f=tree/'build.prop';f.write_text('ro.demo=old\n');rec=p/'rec.json'
   rec.write_text(json.dumps({'recipes':[{'id':'fixture','type':'set_property','trigger_signatures':['netbpf-load-fail'],'path':'build.prop','key':'ro.demo','value':'new','expected_sha256':hashlib.sha256(f.read_bytes()).hexdigest()}]}));log=self.log(p)
   d=self.run_engine(p,log,tree,rec);self.assertEqual(f.read_text(),'ro.demo=old\n');self.assertEqual(len(d['repair_candidates']),1)
   self.run_engine(p,log,tree,rec,True);self.assertEqual(f.read_text(),'ro.demo=new\n')
   subprocess.run(['python3',str(ROOT/'tools/system_patch.py'),'rollback',str(tree),str(p/'rb.json')],check=True);self.assertEqual(f.read_text(),'ro.demo=old\n')
 def test_stale_hash_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);tree=p/'tree';tree.mkdir();f=tree/'x';f.write_text('x=1\n');rec=p/'rec.json';rec.write_text(json.dumps({'recipes':[{'id':'bad','type':'set_property','trigger_signatures':['netbpf-load-fail'],'path':'x','key':'x','value':'2','expected_sha256':'bad'}]}))
   d=self.run_engine(p,self.log(p),tree,rec);self.assertFalse(d['repair_candidates']);self.assertTrue(d['rejected_recipes']);self.assertEqual(f.read_text(),'x=1\n')
 def test_symlink_escape_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);tree=p/'tree';tree.mkdir();outside=p/'outside';outside.write_text('x=1\n');(tree/'link').symlink_to(outside);rec=p/'rec.json';rec.write_text(json.dumps({'recipes':[{'id':'escape','type':'set_property','trigger_signatures':['netbpf-load-fail'],'path':'link','key':'x','value':'2','expected_sha256':hashlib.sha256(outside.read_bytes()).hexdigest()}]}))
   d=self.run_engine(p,self.log(p),tree,rec);self.assertFalse(d['repair_candidates']);self.assertEqual(outside.read_text(),'x=1\n')
 def test_duplicate_file_recipes_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);tree=p/'tree';tree.mkdir();f=tree/'props';f.write_text('a=1\n');h=hashlib.sha256(f.read_bytes()).hexdigest();rec=p/'rec.json'
   base={'type':'set_property','trigger_signatures':['netbpf-load-fail'],'path':'props','expected_sha256':h}
   rec.write_text(json.dumps({'recipes':[dict(base,id='one',key='a',value='2'),dict(base,id='two',key='b',value='3')]}));d=self.run_engine(p,self.log(p),tree,rec)
   self.assertEqual(len(d['repair_candidates']),1);self.assertTrue(any('duplicate target' in x['reason'] for x in d['rejected_recipes']))

 def test_exact_replacement_proposal_and_apply_rollback(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);tree=p/'tree';tree.mkdir();f=tree/'init.rc';f.write_text('service demo /system/bin/demo\\n    disabled\\n');h=hashlib.sha256(f.read_bytes()).hexdigest()
   rec=p/'rec.json';rec.write_text(json.dumps({'recipes':[{'id':'replace','type':'replace_exact','trigger_signatures':['netbpf-load-fail'],'path':'init.rc','before_text':'    disabled\\n','after_text':'    oneshot\\n','expected_sha256':h}]}))
   log=self.log(p);d=self.run_engine(p,log,tree,rec);self.assertEqual(f.read_text(),'service demo /system/bin/demo\\n    disabled\\n');self.assertEqual(d['repair_candidates'][0]['op'],'replace_exact')
   self.run_engine(p,log,tree,rec,True);self.assertEqual(f.read_text(),'service demo /system/bin/demo\\n    oneshot\\n')
   subprocess.run(['python3',str(ROOT/'tools/system_patch.py'),'rollback',str(tree),str(p/'rb.json')],check=True);self.assertIn('disabled',f.read_text())
 def test_exact_replacement_ambiguous_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);tree=p/'tree';tree.mkdir();f=tree/'rc';f.write_text('x\\nx\\n');h=hashlib.sha256(f.read_bytes()).hexdigest();rec=p/'rec.json'
   rec.write_text(json.dumps({'recipes':[{'id':'amb','type':'replace_exact','trigger_signatures':['netbpf-load-fail'],'path':'rc','before_text':'x\\n','after_text':'y\\n','expected_sha256':h}]}))
   d=self.run_engine(p,self.log(p),tree,rec);self.assertFalse(d['repair_candidates']);self.assertTrue(d['rejected_recipes'])
if __name__=='__main__':unittest.main()
