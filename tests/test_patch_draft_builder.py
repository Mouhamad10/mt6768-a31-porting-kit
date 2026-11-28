import sys,pathlib,unittest,tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from patch_draft_builder import draft
class Tests(unittest.TestCase):
 def test_hash_locked_incomplete_draft(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);(root/"rc").write_text("service x\n")
   r=draft(root,["rc"]);self.assertEqual(r["status"],"draft_only");self.assertEqual(r["operations"][0]["status"],"INCOMPLETE_NOT_APPLICABLE");self.assertTrue(r["operations"][0]["expected_sha256"])
 def test_escape_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(ValueError):draft(td,["../outside"])
if __name__=="__main__":unittest.main()
