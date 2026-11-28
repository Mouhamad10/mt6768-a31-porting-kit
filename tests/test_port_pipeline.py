import sys,pathlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from port_pipeline import run,markdown
class PipelineTests(unittest.TestCase):
 def test_pipeline_without_donor(self):
  audit={"elf":[],"init_services":[],"properties":[],"apex":[],"duplicate_sonames":{}}
  r=run("CANNOT LINK EXECUTABLE: library libmissing.so not found",audit)
  self.assertEqual(r["schema"],"a31-port-evidence-pipeline-v3")
  self.assertEqual(len(r["ranked_events"]),1)
  self.assertIsNone(r["compatibility"])
  self.assertFalse(r["patch_policy"]["automatic_changes"])
  self.assertIn("Ranked events",markdown(r))
 def test_with_donor(self):
  audit={"elf":[],"init_services":[],"properties":[],"apex":[],"duplicate_sonames":{}}
  r=run("init: service foo failed",audit,audit)
  self.assertIsNotNone(r["compatibility"])
  self.assertIn("NOT ASSESSED",r["compatibility"]["assessment"])
if __name__=="__main__":unittest.main()
