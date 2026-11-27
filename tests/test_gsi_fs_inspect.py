import pathlib,tempfile,unittest
from tools.gsi_prepare import fs_type
from tools.gsi_fs_inspect import inspect
class InspectorTests(unittest.TestCase):
 def test_unknown_is_not_assessed(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'img';p.write_bytes(b'unknown bytes')
   report=inspect(p)
   self.assertEqual(report['filesystem'],'unknown')
   self.assertEqual(report['compatibility'],'not_assessed')
 def test_f2fs_signature(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'f';b=bytearray(2048);b[1024:1028]=bytes.fromhex('1020f5f2');p.write_bytes(b)
   self.assertEqual(fs_type(p),'f2fs')
