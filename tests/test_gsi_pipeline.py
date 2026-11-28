import json,pathlib,tempfile,unittest
from tools.gsi_pipeline import run_pipeline
class PipelineTests(unittest.TestCase):
 def test_pipeline_report_unknown_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);src=root/'input.bin';src.write_bytes(b'unknown payload')
   out=root/'report'
   r=run_pipeline(src,out,1024)
   self.assertEqual(r['schema'],'a31-gsi-pipeline-report-v2')
   self.assertEqual(r['normalization']['filesystem_hint'],'unknown')
   self.assertEqual(r['readiness']['compatibility_assessment'],'insufficient_evidence')
   self.assertEqual(r['readiness']['boot_test'],'not_performed')
   self.assertTrue((out/'pipeline-report.json').is_file())
   self.assertEqual((out/'normalized/system.img').read_bytes(),src.read_bytes())
 def test_optional_tree_audit(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);src=root/'payload';src.write_bytes(b'unknown')
   tree=root/'tree';tree.mkdir();(tree/'build.prop').write_text('ro.build.version.release=16\n')
   out=root/'out'
   r=run_pipeline(src,out,1024,tree)
   self.assertIsNotNone(r['supplied_system_tree_audit'])
   self.assertEqual(r['supplied_system_tree_audit']['file_count'],1)
   self.assertTrue((out/'system-tree-audit.json').is_file())
   self.assertFalse(r['readiness']['elf_and_vintf_comparisons'])
   self.assertEqual(r['readiness']['boot_test'],'not_performed')
 def test_overlap_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);src=root/'source';src.write_bytes(b'x')
   with self.assertRaises(ValueError):run_pipeline(src,root,100)
