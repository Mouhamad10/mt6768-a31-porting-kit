import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from port_log_analyzer import analyze
class Tests(unittest.TestCase):
 def test_mixed_log_formats_and_categories(self):
  t="console-ramoops\n pmsg-ramoops\navc: denied { read }\nCANNOT LINK EXECUTABLE: libmissing.so\nService foo pid 42 crashed SIGSEGV\napexd failed activation\nVINTF mismatch\n"
  r=analyze(t);self.assertTrue(any("ramoops" in x for x in r["sources_detected"]));self.assertEqual({e["type"] for e in r["events"]},{"selinux_denial","linker_missing","service_crash","apex","vintf"})
 def test_repetition_grouping(self):
  r=analyze("Service foo pid 1 crashed SIGSEGV\nService foo pid 2 crashed SIGSEGV\n")
  c=[x for x in r["clusters"] if x["type"]=="service_crash"];self.assertEqual(len(c),1);self.assertEqual(c[0]["count"],2)
 def test_safe_plan_no_direct_changes(self):
  r=analyze("avc: denied { write }\n");self.assertEqual(r["patch_plan"]["status"],"review_only");self.assertEqual(r["patch_plan"]["proposals"],[])
if __name__=="__main__":unittest.main()
