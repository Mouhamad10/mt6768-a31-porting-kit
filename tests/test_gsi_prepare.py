import pathlib,tempfile,unittest,zipfile
from tools.gsi_prepare import normalize,fs_type,select_image
class PrepareTests(unittest.TestCase):
 def test_archive_requires_system_img(self):
  with self.assertRaises(ValueError):select_image(['boot.img','vendor.img'])
 def test_select_image(self):
  self.assertEqual(select_image(['vendor.img','nested/system.img']), 'nested/system.img')
 def test_detect_ext4(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'img';b=bytearray(1200);b[1080:1082]=bytes.fromhex('53ef');p.write_bytes(b)
   self.assertEqual(fs_type(p),'ext4')
 def test_zip_extract_candidate_and_detect(self):
  with tempfile.TemporaryDirectory() as d:
   src=pathlib.Path(d)/'a.zip';dst=pathlib.Path(d)/'out.img';b=bytearray(1200);b[1080:1082]=bytes.fromhex('53ef')
   with zipfile.ZipFile(src,'w') as z:z.writestr('system.img',b);z.writestr('notes.txt','x')
   self.assertEqual(normalize(src,dst),'ext4');self.assertEqual(fs_type(dst),'ext4')
 def test_fail_unknown_no_fallback(self):
  with tempfile.TemporaryDirectory() as d:
   src=pathlib.Path(d)/'unknown';dst=pathlib.Path(d)/'out';src.write_bytes(b'junk')
   with self.assertRaises(ValueError):normalize(src,dst)
if __name__=='__main__':unittest.main()
