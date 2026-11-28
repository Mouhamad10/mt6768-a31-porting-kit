import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from boot_evidence import extract
class EvidenceTests(unittest.TestCase):
 def test_extract_order_and_types(self):
  log="boot ok\navc: denied { read }\nFatal signal 11 (SIGSEGV)\nKernel panic - not syncing: test\n"
  r=extract(log);self.assertEqual(r["event_count"],3);self.assertEqual([x["type"] for x in r["events"]],["selinux_denial","tombstone","kernel_fault"]);self.assertEqual([x["line"] for x in r["events"]],[2,3,4])
 def test_pid_clustering(self):
  r=extract("Service foo pid 123 exited with status 1\nService foo pid 999 exited with status 1\n")
  self.assertEqual(len(r["clusters"]),1);self.assertEqual(r["clusters"][0]["count"],2)
 def test_limits_excerpt(self):
  r=extract("CANNOT LINK EXECUTABLE: library missing\n");self.assertEqual(r["events"][0]["type"],"linker_missing");self.assertTrue(r["limitations"])
if __name__=="__main__":unittest.main()
