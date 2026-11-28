import json, pathlib, tempfile, unittest
from tools.compat_engine import analyze, apply_recipe

class CompatEngineTests(unittest.TestCase):
 def recipe(self,root,base,ops):
  recipe=base/'recipe.json';recipe.write_text(json.dumps({'schema':'a31-compat-recipe-v1','operations':ops}));return recipe
 def test_stage9_read_only_and_reports_missing_files(self):
  with tempfile.TemporaryDirectory() as d:
   s=pathlib.Path(d)/'s';v=pathlib.Path(d)/'v';s.mkdir();v.mkdir()
   (s/'liba.so').write_bytes(b'\x7fELF');(v/'libb.so').write_bytes(b'not ELF')
   before=(s/'liba.so').read_bytes();r=analyze(s,v)
   self.assertTrue(r['stage9_read_only']);self.assertIn('liba.so',r['system_elf_not_in_vendor_tree']);self.assertEqual((s/'liba.so').read_bytes(),before)
 def test_stage10_dry_run_and_apply_backup(self):
  with tempfile.TemporaryDirectory() as d:
   base=pathlib.Path(d);root=base/'tree';root.mkdir();f=root/'build.prop';f.write_text('ro.foo=old\n')
   recipe=self.recipe(root,base,[{'type':'set_property','path':'build.prop','key':'ro.foo','value':'new','expected_value':'old'}])
   dry=apply_recipe(root,recipe,base/'backup',False);self.assertEqual(f.read_text(),'ro.foo=old\n')
   applied=apply_recipe(root,recipe,base/'backup',True);self.assertTrue(applied['modified']);self.assertEqual(f.read_text(),'ro.foo=new\n');self.assertEqual((base/'backup/build.prop').read_text(),'ro.foo=old\n')
 def test_rejects_path_escape(self):
  with tempfile.TemporaryDirectory() as d:
   base=pathlib.Path(d);root=base/'tree';root.mkdir();recipe=self.recipe(root,base,[{'type':'set_property','path':'../outside','key':'x','value':'y'}])
   with self.assertRaises(ValueError):apply_recipe(root,recipe,base/'b',True)
 def test_rejects_symlink_target_even_inside_tree(self):
  with tempfile.TemporaryDirectory() as d:
   base=pathlib.Path(d);root=base/'tree';root.mkdir();real=root/'real.prop';real.write_text('x=1\n');(root/'alias.prop').symlink_to(real)
   recipe=self.recipe(root,base,[{'type':'set_property','path':'alias.prop','key':'x','value':'2'}])
   with self.assertRaises(ValueError):apply_recipe(root,recipe,base/'b',True)
 def test_backup_collision_fails_before_mutation(self):
  with tempfile.TemporaryDirectory() as d:
   base=pathlib.Path(d);root=base/'tree';root.mkdir();f=root/'build.prop';f.write_text('x=1\n');b=base/'backup';b.mkdir();(b/'build.prop').write_text('old backup')
   recipe=self.recipe(root,base,[{'type':'set_property','path':'build.prop','key':'x','value':'2'}])
   with self.assertRaises(ValueError):apply_recipe(root,recipe,b,True)
   self.assertEqual(f.read_text(),'x=1\n');self.assertEqual((b/'build.prop').read_text(),'old backup')
 def test_duplicate_resolved_target_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   base=pathlib.Path(d);root=base/'tree';root.mkdir();(root/'p').write_text('x=1\n')
   recipe=self.recipe(root,base,[{'type':'set_property','path':'p','key':'x','value':'2'},{'type':'set_property','path':'p','key':'x','value':'3'}])
   with self.assertRaises(ValueError):apply_recipe(root,recipe,base/'b',False)
if __name__=='__main__':unittest.main()
