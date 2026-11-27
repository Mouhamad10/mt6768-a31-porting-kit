import pathlib,tempfile,unittest
from tools.gsi_prepare import choose,fs_type
from tools.gsi_analyze import detect
class AnalyzerTests(unittest.TestCase):
 def test_sparse_magic(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'s';p.write_bytes(bytes.fromhex('3aff26ed')+bytes(100));self.assertEqual(detect(p),'android_sparse')
 def test_erofs_magic(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'e';b=bytearray(2048);b[1024:1028]=bytes.fromhex('e2e1f5e0');p.write_bytes(b);self.assertEqual(detect(p),'erofs')
 def test_f2fs_magic(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'f';b=bytearray(2048);b[1024:1028]=bytes.fromhex('1020f5f2');p.write_bytes(b);self.assertEqual(detect(p),'f2fs')
 def test_ext4(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'x';b=bytearray(4096);b[1080:1082]=bytes.fromhex('53ef');p.write_bytes(b);self.assertEqual(detect(p),'ext4')
