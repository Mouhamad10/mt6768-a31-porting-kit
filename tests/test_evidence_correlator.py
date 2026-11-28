import sys,pathlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from evidence_correlator import correlate
class Tests(unittest.TestCase):
 def test_library_inventory_and_absence(self):
  log={"events":[{"line":3,"type":"linker_missing","text":"dlopen failed libmissing.so and libfound.so"}]}
  audit={"elf":[{"path":"lib/libfound.so","soname":"libfound.so","needed":[]}],"init_services":[],"properties":[],"apex":[]}
  m=correlate(log,audit)["findings"][0]["matches"]
  self.assertTrue(any(x["kind"]=="library_inventory" for x in m));self.assertTrue(any(x["kind"]=="missing_library_inventory_candidate" for x in m))
 def test_service_match_and_status(self):
  log={"events":[{"line":1,"type":"service_crash","text":"Service foo crashed"}]}
  audit={"elf":[],"init_services":[{"name":"foo","file":"init.rc","line":2,"command":"/system/bin/foo"}],"properties":[],"apex":[]}
  r=correlate(log,audit);self.assertEqual(r["correlated_event_count"],1);self.assertEqual(r["compatibility_status"],"NOT ASSESSED")
 def test_empty(self):
  self.assertEqual(correlate({"events":[]},{"elf":[],"init_services":[],"properties":[],"apex":[]})["findings"],[])
if __name__=="__main__":unittest.main()
