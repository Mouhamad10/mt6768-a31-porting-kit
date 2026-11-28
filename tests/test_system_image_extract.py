import pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];TOOL=ROOT/'tools/system_image_extract.py'
class ExtractGuard(unittest.TestCase):
 def test_unknown_image_refused(self):
  with tempfile.TemporaryDirectory() as td:
   img=pathlib.Path(td)/'unknown.img';img.write_bytes(b'not filesystem')
   dst=pathlib.Path(td)/'tree'
   r=subprocess.run(['python3',str(TOOL),str(img),str(dst)],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('unknown filesystem',r.stderr)
 def test_nonempty_destination_refused(self):
  with tempfile.TemporaryDirectory() as td:
   img=pathlib.Path(td)/'img';img.write_bytes(b'x'*4096)
   dst=pathlib.Path(td)/'tree';dst.mkdir();(dst/'keep').write_text('x')
   r=subprocess.run(['python3',str(TOOL),str(img),str(dst)],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('destination must be absent or empty',r.stderr)
if __name__=='__main__':unittest.main()
