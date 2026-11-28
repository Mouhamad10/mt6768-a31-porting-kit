import pathlib,tempfile,unittest
from tools.hal_vendor_analyzer import scan
from tools.port_validator import validate
class Stage11Tests(unittest.TestCase):
 def test_vintf_rc_evidence_and_no_changes(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'manifest.xml').write_text('<manifest><hal><name>android.hardware.foo</name></hal></manifest>')
   (p/'foo-hal.rc').write_text('service foo /vendor/bin/foo\n')
   before=(p/'manifest.xml').read_bytes();r=scan(p)
   self.assertTrue(r['no_changes_made']);self.assertIn('manifest.xml',r['evidence']['vintf']);self.assertTrue(r['xml_rc_policy_snippets']);self.assertEqual(before,(p/'manifest.xml').read_bytes())
class Stage12Tests(unittest.TestCase):
 def test_detect_duplicate_property_and_hashes(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'build.prop').write_text('a=1\na=2\n')
   r=validate(p);self.assertEqual(r['result'],'PASS_WITH_WARNINGS');self.assertTrue(r['file_hash_manifest'])
 def test_symlink_escape_error(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);root=p/'tree';root.mkdir();outside=p/'out';outside.write_text('x')
   (root/'link').symlink_to(outside)
   r=validate(root);self.assertEqual(r['result'],'FAIL');self.assertTrue(any(f['kind']=='symlink_escape' for f in r['findings']))
