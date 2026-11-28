import pathlib,tempfile,unittest
from tools.hal_vendor_analyzer import scan
from tools.port_validator import validate
class Stage11Tests(unittest.TestCase):
 def test_vintf_rc_evidence_and_read_only(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'manifest.xml').write_text('<manifest><hal><name>android.hardware.foo</name></hal></manifest>')
   (p/'foo-hal.rc').write_text('service foo /vendor/bin/foo\n');(p/'ld.config.txt').write_text('x')
   (p/'policy.te').write_text('allow x y z')
   (p/'libx.so').write_bytes(b'\x7fELFdata')
   before={f.name:f.read_bytes() for f in p.iterdir()};r=scan(p)
   self.assertTrue(r['no_changes_made']);self.assertIn('manifest.xml',r['evidence']['vintf'])
   self.assertTrue(r['xml_rc_policy_snippets']);self.assertIn('foo-hal.rc',r['evidence']['hal_service_rc'])
   self.assertIn('ld.config.txt',r['evidence']['linker_config']);self.assertIn('policy.te',r['evidence']['sepolicy'])
   self.assertEqual(before,{f.name:f.read_bytes() for f in p.iterdir()})
class Stage12Tests(unittest.TestCase):
 def test_duplicate_property_hash_manifest(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'build.prop').write_text('a=1\na=2\n')
   r=validate(p);self.assertEqual(r['result'],'PASS_WITH_WARNINGS');self.assertTrue(r['file_hash_manifest']);self.assertTrue(any(f['kind']=='duplicate_property' for f in r['findings']))
 def test_symlink_escape_error(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);root=p/'tree';root.mkdir();outside=p/'out';outside.write_text('x')
   (root/'link').symlink_to(outside);r=validate(root)
   self.assertEqual(r['result'],'FAIL');self.assertTrue(any(f['kind']=='symlink_escape' for f in r['findings']))
 def test_dangling_symlink_warning(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);(root/'broken').symlink_to(root/'missing')
   r=validate(root);self.assertEqual(r['result'],'PASS_WITH_WARNINGS');self.assertTrue(any(f['kind']=='dangling_symlink' for f in r['findings']))
 def test_rc_nul_detection(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);(root/'bad.rc').write_bytes(b'service foo /bin/foo\x00bad\n')
   r=validate(root);self.assertEqual(r['result'],'FAIL');self.assertTrue(any(f['kind']=='invalid_init_line' for f in r['findings']))
