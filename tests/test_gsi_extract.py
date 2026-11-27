import pathlib,tempfile,zipfile,unittest
from tools.gsi_extract import normalize

class ExtractTests(unittest.TestCase):
 def test_zip_extracts_system_payload_without_path_expansion(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d); z=root/'gsi.zip'; out=root/'out'
   payload=bytearray(4096); payload[1080:1082]=bytes.fromhex('53ef')
   with zipfile.ZipFile(z,'w') as a:
    a.writestr('../../escape.txt','unsafe path is not extracted')
    a.writestr('nested/system.img',payload)
    a.writestr('boot.img',b'boot')
   report=normalize(z,out)
   self.assertEqual(report['selected_member'],'nested/system.img')
   self.assertEqual(report['filesystem_hint'],'ext4')
   self.assertFalse((root/'escape.txt').exists())
   self.assertEqual((out/'system.img').read_bytes(),bytes(payload))
   self.assertFalse(report['filesystem_contents_extracted'])
 def test_raw_unknown_is_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d); src=root/'input';src.write_bytes(b'opaque payload')
   report=normalize(src,root/'out')
   self.assertEqual(report['filesystem_hint'],'unknown')
   self.assertEqual((root/'out/system.img').read_bytes(),src.read_bytes())
