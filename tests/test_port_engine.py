import json,pathlib,subprocess,tempfile,hashlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];TOOL=ROOT/'tools/port_engine.py';SIG=ROOT/'tools/boot-signatures.json'
class EngineTests(unittest.TestCase):
 def test_diagnosis_correlation(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);log=p/'log';log.write_text('CRITICAL FAILURE LOADING BPF PROGRAMS\nreboot,bpfloader-failed\n');r=p/'report.json'
   subprocess.run(['python3',str(TOOL),str(log),'--signatures',str(SIG),'--report',str(r)],check=True);d=json.loads(r.read_text())
   self.assertIn('netbpf-load-fail',d['matched_signature_ids']);self.assertIn('bpfloader-reboot',d['matched_signature_ids']);self.assertTrue(d['correlations'])
 def test_proposal_then_apply_and_rollback(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);tree=p/'tree';tree.mkdir();f=tree/'build.prop';f.write_text('ro.demo=old\n');recipe=p/'recipes.json'
   recipe.write_text(json.dumps({'recipes':[{'id':'fixture','type':'set_property','trigger_signatures':['netbpf-load-fail'],'path':'build.prop','key':'ro.demo','value':'new','expected_sha256':hashlib.sha256(f.read_bytes()).hexdigest()}]}));log=p/'log';log.write_text('CRITICAL FAILURE LOADING BPF PROGRAMS\n')
   args=['python3',str(TOOL),str(log),'--tree',str(tree),'--recipes',str(recipe),'--report',str(p/'r.json'),'--patch',str(p/'patch.json')]
   subprocess.run(args,check=True);self.assertEqual(f.read_text(),'ro.demo=old\n')
   subprocess.run(args+['--apply','--rollback-manifest',str(p/'rb.json')],check=True);self.assertEqual(f.read_text(),'ro.demo=new\n')
   subprocess.run(['python3',str(ROOT/'tools/system_patch.py'),'rollback',str(tree),str(p/'rb.json')],check=True);self.assertEqual(f.read_text(),'ro.demo=old\n')
 def test_stale_recipe_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);tree=p/'tree';tree.mkdir();f=tree/'x.prop';f.write_text('x=1\n');rec=p/'recipes.json'
   rec.write_text(json.dumps({'recipes':[{'id':'bad','type':'set_property','trigger_signatures':['netbpf-load-fail'],'path':'x.prop','key':'x','value':'2','expected_sha256':'wrong'}]}));log=p/'log';log.write_text('CRITICAL FAILURE LOADING BPF PROGRAMS\n')
   subprocess.run(['python3',str(TOOL),str(log),'--tree',str(tree),'--recipes',str(rec),'--report',str(p/'r.json')],check=True);d=json.loads((p/'r.json').read_text())
   self.assertFalse(d['repair_candidates']);self.assertTrue(d['rejected_recipes']);self.assertEqual(f.read_text(),'x=1\n')
if __name__=='__main__':unittest.main()
