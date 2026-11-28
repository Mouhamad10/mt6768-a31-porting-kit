import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from elf_symbol_compare import compare
class TestCompare(unittest.TestCase):
 def test_non_elf_inputs(self):
  with tempfile.TemporaryDirectory() as td:
   t=pathlib.Path(td)/"t";d=pathlib.Path(td)/"d";t.mkdir();d.mkdir()
   (t/"x").write_text("no elf");(d/"x").write_text("no elf")
   r=compare(t,d);self.assertEqual(r["matched_paths"],1);self.assertEqual(r["symbol_gaps"],[])
if __name__=="__main__":unittest.main()
