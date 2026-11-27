import gzip, pathlib, tempfile, zipfile, unittest, lzma
from unittest.mock import patch
from tools.gsi_extract import normalize, sparse_size

class ExtractTests(unittest.TestCase):
 def payload(self):
  b=bytearray(4096);b[1080:1082]=bytes.fromhex('53ef');return bytes(b)
 def test_zip_safe_member_and_report(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);z=root/'gsi.zip';out=root/'out'
   with zipfile.ZipFile(z,'w') as a:
    a.writestr('../../escape.txt','unsafe');a.writestr('nested/system.img',self.payload());a.writestr('boot.img',b'boot')
   r=normalize(z,out)
   self.assertEqual(r['selected_member'],'nested/system.img');self.assertEqual(r['filesystem_hint'],'ext4')
   self.assertFalse((root/'escape.txt').exists());self.assertEqual((out/'system.img').read_bytes(),self.payload())
   self.assertFalse(r['filesystem_contents_extracted']);self.assertTrue((out/'extract-report.json').is_file())
 def test_unknown_raw_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);s=root/'input';s.write_bytes(b'opaque');r=normalize(s,root/'out')
   self.assertEqual(r['filesystem_hint'],'unknown');self.assertEqual((root/'out/system.img').read_bytes(),s.read_bytes())
 def test_gzip_normalized(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);s=root/'payload.gz';s.write_bytes(gzip.compress(self.payload()));r=normalize(s,root/'out')
   self.assertEqual(r['transformations'],['gzip']);self.assertEqual((root/'out/system.img').read_bytes(),self.payload())
 def test_xz_normalized(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);s=root/'payload.xz';s.write_bytes(lzma.compress(self.payload()));r=normalize(s,root/'out')
   self.assertEqual(r['transformations'],['xz']);self.assertEqual((root/'out/system.img').read_bytes(),self.payload())
 def test_stream_limit_enforced(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);s=root/'input';s.write_bytes(b'a'*32)
   with patch('tools.gsi_extract.MAX_BYTES',16):
    with self.assertRaises(ValueError):normalize(s,root/'out')
   self.assertFalse(any(x.name.startswith('.gsi-extract-') for x in (root/'out').iterdir()))
 def test_input_inside_output_tree_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);out=root/'out';out.mkdir();s=out/'source';s.write_bytes(b'abc')
   with self.assertRaises(ValueError):normalize(s,out)
 def test_sparse_declared_size_limit(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'sparse';h=bytearray(28);h[:4]=bytes.fromhex('3aff26ed');h[12:16]=(4096).to_bytes(4,'little');h[16:20]=(10).to_bytes(4,'little');p.write_bytes(h)
   with patch('tools.gsi_extract.MAX_BYTES',100):
    with self.assertRaises(ValueError):sparse_size(p)
 def test_duplicate_zip_member_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);s=root/'dup.zip'
   with zipfile.ZipFile(s,'w') as z:z.writestr('system.img',b'a');z.writestr('system.img',b'b')
   with self.assertRaises(ValueError):normalize(s,root/'out')
