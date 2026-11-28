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
if __name__=='__main__':unittest.main()
