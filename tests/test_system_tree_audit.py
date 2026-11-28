import json, pathlib, subprocess, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools/system_tree_audit.py'
class AuditSmoke(unittest.TestCase):
 def test_property_conflict_and_inventory(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td)/'tree'; (root/'system').mkdir(parents=True); (root/'product/overlay').mkdir(parents=True)
   (root/'system/build.prop').write_text('ro.test=one\\n')
   (root/'product/build.prop').write_text('ro.test=two\\n')
   (root/'system/init.rc').write_text('on boot\\n')
   (root/'product/overlay/test.apk').write_text('fixture')
   report=pathlib.Path(td)/'report.json'; txt=pathlib.Path(td)/'report.txt'
   subprocess.run(['python3',str(TOOL),str(root),'--report',str(report),'--props-report',str(txt)],check=True)
   data=json.loads(report.read_text())
   self.assertIn('ro.test',data['property_conflicts'])
   self.assertEqual(data['boot_compatibility'],'NOT ASSESSED')
   self.assertEqual(data['patches_applied'],[])
   self.assertTrue(any(x.endswith('init.rc') for x in data['init_rc']))
   self.assertEqual(data['apk_count'],1)
if __name__=='__main__':unittest.main()
