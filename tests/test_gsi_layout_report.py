import pathlib,tempfile,unittest
from tools.gsi_layout_report import scan
class ScanTests(unittest.TestCase):
 def test_fstab_reference_detected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'etc';p.mkdir();(p/'fstab').write_text('/system logical first_stage_mount\n')
   r=scan(d);self.assertTrue(any('first_stage_mount' in x['text'] for x in r['matches']))
