import json, pathlib, tempfile, unittest
from tools.compat_engine import analyze, apply_recipe

class CompatEngineTests(unittest.TestCase):
 def test_stage9_is_read_only_and_reports_missing_files(self):
  with tempfile.TemporaryDirectory() as d:
   s=pathlib.Path(d)/'s';v=pathlib.Path(d)/'v';s.mkdir();v.mkdir()
   (s/'liba.so').write_bytes(b'\x7fELF');(v/'libb.so').write_bytes(b'not ELF')
   before=(s/'liba.so').read_bytes()
   r=analyze(s,v)
   self.assertTrue(r['stage9_read_only']);self.assertIn('liba.so',r['system_elf_not_in_vendor_tree'])
   self.assertEqual((s/'liba.so').read_bytes(),before)
 def test_stage10_dry_run_and_apply_backup(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d)/'tree';root.mkdir();f=root/'build.prop';f.write_text('ro.foo=old\n')
   recipe=pathlib.Path(d)/'recipe.json';recipe.write_text(json.dumps({'schema':'a31-compat-recipe-v1','operations':[{'type':'set_property','path':'build.prop','key':'ro.foo','value':'new','expected_value':'old'}]}))
   dry=apply_recipe(root,recipe,pathlib.Path(d)/'backup',False);self.assertEqual(f.read_text(),'ro.foo=old\n')
   applied=apply_recipe(root,recipe,pathlib.Path(d)/'backup',True);self.assertTrue(applied['modified']);self.assertEqual(f.read_text(),'ro.foo=new\n')
   self.assertEqual((pathlib.Path(d)/'backup/build.prop').read_text(),'ro.foo=old\n')
 def test_rejects_path_escape(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d)/'tree';root.mkdir();recipe=pathlib.Path(d)/'r.json'
   recipe.write_text(json.dumps({'schema':'a31-compat-recipe-v1','operations':[{'type':'set_property','path':'../outside','key':'x','value':'y'}]}))
   with self.assertRaises(ValueError):apply_recipe(root,recipe,pathlib.Path(d)/'b',True)
if __name__=='__main__':unittest.main()
