import gzip, pathlib, tempfile, zipfile, unittest, lzma, io
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
   r=normalize(z,out);self.assertEqual(r['selected_member'],'nested/system.img');self.assertEqual(r['filesystem_hint'],'ext4')
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
 def test_configurable_limit(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);s=root/'input';s.write_bytes(b'a'*32);r=normalize(s,root/'out',64)
   self.assertEqual(r['size_limit_bytes'],64)
   with self.assertRaises(ValueError):normalize(s,root/'second',16)
 def test_input_inside_output_tree_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);out=root/'out';out.mkdir();s=out/'source';s.write_bytes(b'abc')
   with self.assertRaises(ValueError):normalize(s,out)
 def test_sparse_declared_size_limit(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'sparse';h=bytearray(28);h[:4]=bytes.fromhex('3aff26ed');h[12:16]=(4096).to_bytes(4,'little');h[16:20]=(10).to_bytes(4,'little');p.write_bytes(h)
   with self.assertRaises(ValueError):sparse_size(p,100)
 
 def test_7z_stream_selection_mocked(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);src=root/'archive.7z';src.write_bytes(b'fake')
   listing='\nType = 7z\n\nPath = archive.7z\n\nPath = system.img\nSize = 3\nFolder = -\n\n'
   proc=type('Proc',(),{'stdout':io.BytesIO(b'abc'),'wait':lambda self:0,'kill':lambda self:None})()
   with patch('tools.gsi_extract.zipfile.is_zipfile',return_value=False),patch('tools.gsi_extract.tarfile.is_tarfile',return_value=False),patch('tools.gsi_extract.shutil.which',return_value='/fake/7z'),patch('tools.gsi_extract.subprocess.run',return_value=type('R',(),{'returncode':0,'stdout':listing})()),patch('tools.gsi_extract.subprocess.Popen',return_value=proc):
    r=normalize(src,root/'out',100)
   self.assertEqual(r['selected_member'],'system.img')
   self.assertEqual((root/'out/system.img').read_bytes(),b'abc')

 def test_duplicate_zip_member_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);s=root/'dup.zip'
   with zipfile.ZipFile(s,'w') as z:z.writestr('system.img',b'a');z.writestr('system.img',b'b')
   with self.assertRaises(ValueError):normalize(s,root/'out')
