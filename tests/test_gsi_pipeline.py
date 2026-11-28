import json,pathlib,tempfile,unittest
from tools.gsi_pipeline import run_pipeline
class PipelineTests(unittest.TestCase):
 def test_pipeline_report_unknown_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);src=root/'input.bin';src.write_bytes(b'unknown payload')
   out=root/'report'
   r=run_pipeline(src,out,1024)
   self.assertEqual(r['schema'],'a31-gsi-pipeline-report-v1')
   self.assertEqual(r['normalization']['filesystem_hint'],'unknown')
   self.assertEqual(r['readiness']['compatibility_assessment'],'insufficient_evidence')
   self.assertEqual(r['readiness']['boot_test'],'not_performed')
   self.assertTrue((out/'pipeline-report.json').is_file())
   self.assertEqual((out/'normalized/system.img').read_bytes(),src.read_bytes())
 def test_overlap_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);src=root/'source';src.write_bytes(b'x')
   with self.assertRaises(ValueError):run_pipeline(src,root,100)
