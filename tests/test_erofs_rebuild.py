import pathlib,tempfile,unittest
from unittest.mock import patch
from tools.erofs_rebuild import rebuild
class RebuildTests(unittest.TestCase):
 def test_missing_tool_refused(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);tree=p/'tree';tree.mkdir()
   with patch('tools.erofs_rebuild.shutil.which',return_value=None):
    with self.assertRaises(RuntimeError):rebuild(tree,p/'out.img','lz4')
