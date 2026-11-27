import pathlib,tempfile,unittest,zipfile
from tools.gsi_prepare import fs_type,select_zip
class T(unittest.TestCase):
 def test_single_candidate(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'a.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('folder/system.img',b'x')
   with zipfile.ZipFile(p) as z:self.assertEqual(select_zip(z),'folder/system.img')
 def test_ambiguous(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'a.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('one/system.img',b'x');z.writestr('two/system.img',b'y')
   with zipfile.ZipFile(p) as z:
    with self.assertRaises(ValueError):select_zip(z)
 def test_ext4_magic(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'x';b=bytearray(4096);b[1080:1082]=bytes.fromhex('53ef');p.write_bytes(b);self.assertEqual(fs_type(p),'ext4')
if __name__=='__main__':unittest.main()
