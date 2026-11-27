import pathlib,tempfile,unittest
from tools.gsi_prepare import choose,fs_type
class T(unittest.TestCase):
 def test_prefers_system(self):self.assertEqual(choose(['misc','nested/system.img','thing']), 'nested/system.img')
 def test_fallback(self):self.assertTrue(choose(['a.bin','b.bin']))
 def test_ext4(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'x';b=bytearray(4096);b[1080:1082]=bytes.fromhex('53ef');p.write_bytes(b);self.assertEqual(fs_type(p),'ext4')
