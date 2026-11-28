import sys,pathlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from compatibility_evidence import report
class Tests(unittest.TestCase):
 def test_dependency_gap_and_abi_difference(self):
  t={"root":"target","elf":[{"path":"a.so","soname":"a.so","needed":["b.so"],"machine":"ARM","elf_class":"ELF64"}],"duplicate_sonames":{},"init_services":[]}
  d={"root":"donor","elf":[{"path":"b.so","soname":"b.so","needed":[],"machine":"X86","elf_class":"ELF64"}],"init_services":[]}
  r=report(t,d);self.assertTrue(any(x["category"]=="abi_metadata_difference" for x in r["gap_findings"]));self.assertIn("NOT ASSESSED",r["assessment"])
 def test_absent_needed_donor(self):
  t={"elf":[{"path":"x","soname":"x","needed":["z.so"]}],"duplicate_sonames":{},"init_services":[]};d={"elf":[],"init_services":[]}
  self.assertTrue(any(x["category"]=="donor_dependency_gap" for x in report(t,d)["gap_findings"]))
if __name__=="__main__":unittest.main()
