import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from vintf_compare import compare
class Tests(unittest.TestCase):
 def test_missing_interface_and_metadata(self):
  with tempfile.TemporaryDirectory() as td:
   t=pathlib.Path(td)/"t";d=pathlib.Path(td)/"d";t.mkdir();d.mkdir()
   (t/"manifest.xml").write_text('<manifest><hal name="android.hardware.foo" transport="hwbinder"><interface name="IFoo"><instance>default</instance></interface></hal></manifest>')
   (d/"manifest.xml").write_text('<manifest><hal name="android.hardware.foo" transport="hwbinder"><interface name="IFoo"><instance>default</instance></interface></hal><hal name="android.hardware.bar"><interface name="IBar"><instance>default</instance></interface></hal></manifest>')
   r=compare(t,d);self.assertEqual(len(r["donor_only_entries"]),1);self.assertEqual(r["donor_only_entries"][0]["package"],"android.hardware.bar");self.assertEqual(len(r["shared_entries"]),1)
 def test_parse_failure_skipped(self):
  with tempfile.TemporaryDirectory() as td:
   t=pathlib.Path(td)/"t";d=pathlib.Path(td)/"d";t.mkdir();d.mkdir();(t/"bad.xml").write_text("<oops");(d/"x.xml").write_text("<manifest/>")
   self.assertEqual(compare(t,d)["target_entries"],[])
if __name__=="__main__":unittest.main()
