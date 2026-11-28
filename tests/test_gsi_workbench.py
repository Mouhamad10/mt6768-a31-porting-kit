import pathlib, tempfile, unittest
from tools.gsi_workbench import analyze, detect

class WorkbenchTests(unittest.TestCase):
    def test_unknown_small_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"x.bin"; p.write_bytes(b"not an image")
            self.assertEqual(analyze(p)["type"],"unknown")
    def test_ext4_signature(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"fake.img"; b=bytearray(1200); b[1080:1082]=bytes.fromhex("53ef"); p.write_bytes(b)
            self.assertEqual(detect(p),"ext4")
    def test_empty_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"empty"; p.touch()
            with self.assertRaises(ValueError): analyze(p)
    def test_zip_inventory_and_candidate(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"gsi.zip"
            with zipfile.ZipFile(p,"w") as z: z.writestr("system.img",b"fake"); z.writestr("readme.txt",b"x")
            r=analyze(p); self.assertEqual(r["type"],"zip")
            self.assertEqual(r["system_image_candidates"][0]["name"],"system.img")

if __name__=="__main__": unittest.main()
