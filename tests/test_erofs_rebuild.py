import pathlib,tempfile,unittest
from unittest.mock import patch
from tools.erofs_rebuild import rebuild
class RebuildTests(unittest.TestCase):
 def test_missing_tool_refused(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);tree=p/'tree';tree.mkdir()
   with patch('tools.erofs_rebuild.shutil.which',return_value=None):
    with self.assertRaises(RuntimeError):rebuild(tree,p/'out','lz4')
 def test_invalid_compression_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);tree=p/'tree';tree.mkdir()
   with self.assertRaises(ValueError):rebuild(tree,p/'out','lz4hc')
 def test_output_inside_tree_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);tree=p/'tree';tree.mkdir()
   with self.assertRaises(ValueError):rebuild(tree,tree/'image.erofs','none')
 def test_staged_build_and_report(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);tree=p/'tree';tree.mkdir();out=p/'image.erofs'
   def fake_run(cmd,**kw):
    pathlib.Path(cmd[-2]).write_bytes(b'fake erofs')
    return type('R',(),{'returncode':0,'stdout':'ok','stderr':''})()
   with patch('tools.erofs_rebuild.shutil.which',side_effect=lambda x:'/fake/'+x if x in ('mkfs.erofs','fsck.erofs') else None),patch('tools.erofs_rebuild.subprocess.run',side_effect=fake_run):
    r=rebuild(tree,out,'lz4')
   self.assertTrue(out.exists());self.assertTrue(out.with_suffix('.erofs.report.json').exists());self.assertEqual(r['fsck_erofs']['returncode'],0)
 def test_fsck_failure_discards_stage(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);tree=p/'tree';tree.mkdir();out=p/'image.erofs';out.write_bytes(b'old image')
   def fake_run(cmd,**kw):
    if 'fsck.erofs' in cmd[0]:return type('R',(),{'returncode':1,'stdout':'','stderr':'bad'})()
    pathlib.Path(cmd[-2]).write_bytes(b'new image');return type('R',(),{'returncode':0,'stdout':'','stderr':''})()
   with patch('tools.erofs_rebuild.shutil.which',side_effect=lambda x:'/fake/'+x if x in ('mkfs.erofs','fsck.erofs') else None),patch('tools.erofs_rebuild.subprocess.run',side_effect=fake_run):
    with self.assertRaises(RuntimeError):rebuild(tree,out,'none')
   self.assertEqual(out.read_bytes(),b'old image')
