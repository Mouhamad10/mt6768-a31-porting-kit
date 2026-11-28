import hashlib,json,pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]; TOOL=ROOT/'tools/system_patch.py'
class PatchTest(unittest.TestCase):
 def test_apply_rollback_hash_guard(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td); p=root/'system/build.prop';p.parent.mkdir();p.write_text('ro.foo=old\n')
   patch=root/'patch.json';patch.write_text(json.dumps({'schema':'a31-system-patch-v1','operations':[{'op':'set_property','path':'system/build.prop','key':'ro.foo','value':'new','expected_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}))
   manifest=root/'rollback.json'
   subprocess.run(['python3',str(TOOL),'apply',str(root),str(patch),'--rollback-manifest',str(manifest)],check=True)
   self.assertEqual(p.read_text(),'ro.foo=new\n')
   subprocess.run(['python3',str(TOOL),'rollback',str(root),str(manifest)],check=True)
   self.assertEqual(p.read_text(),'ro.foo=old\n')
 def test_hash_precondition(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);p=root/'build.prop';p.write_text('x=y\n')
   patch=root/'patch.json';patch.write_text(json.dumps({'schema':'a31-system-patch-v1','operations':[{'op':'set_property','path':'build.prop','key':'x','value':'z','expected_sha256':'wrong'}]}))
   self.assertNotEqual(subprocess.run(['python3',str(TOOL),'apply',str(root),str(patch)],capture_output=True).returncode,0)

 def test_preflight_failure_does_not_modify_first_file(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);a=root/'a.prop';b=root/'b.prop';a.write_text('a=1\\n');b.write_text('b=2\\n')
   patch=root/'patch.json';patch.write_text(json.dumps({'schema':'a31-system-patch-v1','operations':[{'op':'set_property','path':'a.prop','key':'a','value':'3','expected_sha256':hashlib.sha256(a.read_bytes()).hexdigest()},{'op':'set_property','path':'b.prop','key':'b','value':'4','expected_sha256':'bad'}]}))
   r=subprocess.run(['python3',str(TOOL),'apply',str(root),str(patch)],capture_output=True)
   self.assertNotEqual(r.returncode,0);self.assertEqual(a.read_text(),'a=1\\n')
 def test_duplicate_active_keys_collapse(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);p=root/'x.prop';p.write_text('x=old\\nx=stale\\n#x=comment\\n')
   patch=root/'patch.json';patch.write_text(json.dumps({'schema':'a31-system-patch-v1','operations':[{'op':'set_property','path':'x.prop','key':'x','value':'new','expected_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}))
   subprocess.run(['python3',str(TOOL),'apply',str(root),str(patch),'--rollback-manifest',str(root/'rb.json')],check=True)
   self.assertEqual(p.read_text(),'x=new\\n#x=comment\\n')

if __name__=='__main__':unittest.main()
