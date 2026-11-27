import pathlib,tempfile,zipfile,unittest
from tools.gsi_archive_inventory import inventory
class InventoryTests(unittest.TestCase):
 def test_zip_images_only_no_extraction(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'a.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('system.img',b'x');z.writestr('text.txt',b'y')
   r=inventory(p);self.assertEqual([x['name'] for x in r['image_candidates']],['system.img'])
