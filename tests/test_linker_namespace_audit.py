import tempfile,unittest,pathlib
from linker_namespace_audit import scan
class Tests(unittest.TestCase):
 def test_sections_directives_and_comments(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/"etc"/"ld.config.txt";p.parent.mkdir()
   p.write_text("# ignored\n[global]\nnamespace.default.isolated = true\n[namespace.default]\nnamespace.default.search.paths = /system/lib64\nnamespace.default.links = vendor\n")
   r=scan(d)
   self.assertEqual(len(r["config_files"]),1)
   self.assertEqual([x["section"] for x in r["namespaces"]],["namespace.default"])
   self.assertEqual(r["namespaces"][0]["directives"][0]["key"],"namespace.default.search.paths")
 def test_empty(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(scan(d)["sections"],[])
if __name__=="__main__":unittest.main()
