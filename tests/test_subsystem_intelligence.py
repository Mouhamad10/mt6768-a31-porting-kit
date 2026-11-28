import sys,pathlib,unittest,tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from subsystem_intelligence import inspect
class SubsystemTests(unittest.TestCase):
 def test_vintf_and_linker_inventory(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);(root/"manifest.xml").write_text('<manifest><hal name="android.hardware.foo"><interface name="IFoo"><instance>default</instance></interface></hal></manifest>')
   (root/"ld.config.txt").write_text('namespace.default.search.paths = /system/lib64\n')
   r=inspect({"events":[]},{"elf":[]},root)
   self.assertEqual(len(r["vintf_inventory"]),1)
   self.assertEqual(len(r["linker_config_inventory"]),1)
 def test_selinux_parse(self):
  r=inspect({"events":[{"type":"selinux_denial","line":5,"text":"avc: denied { read write } scontext=u:r:test:s0 tcontext=u:object_r:foo:s0 tclass=file"}]},{"elf":[]})
  self.assertEqual(r["selinux_denials"][0]["parsed"]["tclass"],"file")
  self.assertEqual(r["selinux_denials"][0]["parsed"]["permissions"],"read write")
if __name__=="__main__":unittest.main()
