import pathlib,tempfile,unittest
from tools.a31_compat_report import report
class ReportTests(unittest.TestCase):
 def test_unknowns_explicit(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'img';p.write_bytes(bytes(2048))
   r=report(p);self.assertEqual(r['status'],'not_assessed');self.assertEqual(r['boot_test'],'not_performed')
