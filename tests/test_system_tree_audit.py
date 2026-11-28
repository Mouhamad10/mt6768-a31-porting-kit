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
 def test_elf_abi_metadata_when_compiler_available(self):
  import shutil
  compiler=shutil.which('cc') or shutil.which('gcc')
  if not compiler: self.skipTest('C compiler unavailable')
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td)/'tree'; (root/'system/lib64').mkdir(parents=True)
   src=pathlib.Path(td)/'fixture.c'; src.write_text('int fixture(void){return 42;}\\n')
   so=root/'system/lib64/libfixture.so'
   subprocess.run([compiler,'-shared','-fPIC',str(src),'-Wl,-soname,libfixture.so','-o',str(so)],check=True)
   report=pathlib.Path(td)/'report.json'; txt=pathlib.Path(td)/'report.txt'
   subprocess.run(['python3',str(TOOL),str(root),'--report',str(report),'--props-report',str(txt)],check=True)
   data=json.loads(report.read_text()); item=next(x for x in data['elf'] if x['path'].endswith('libfixture.so'))
   self.assertTrue(item['elf_class']); self.assertTrue(item['machine']); self.assertTrue(item['endianness'])
   self.assertEqual(item['soname'],'libfixture.so'); self.assertIsInstance(item['runpath_rpath'],list)
 def test_init_import_trigger_and_service_inventory(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td)/'tree'; (root/'system').mkdir(parents=True)
   rc=root/'system/init.rc'; rc.write_text('import /vendor/etc/init/foo.rc\non property:sys.boot_completed=1\nservice testd /system/bin/testd\n')
   report=pathlib.Path(td)/'report.json'; txt=pathlib.Path(td)/'report.txt'
   subprocess.run(['python3',str(TOOL),str(root),'--report',str(report),'--props-report',str(txt)],check=True)
   data=json.loads(report.read_text())
   self.assertEqual(data['init_imports'][0]['target'],'/vendor/etc/init/foo.rc')
   self.assertIn('sys.boot_completed=1',data['init_actions'][0]['trigger'])
   self.assertEqual(data['init_services'][0]['name'],'testd')
 def test_invalid_elf_is_recorded_without_crashing(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td)/'tree'; (root/'system/lib64').mkdir(parents=True)
   bad=root/'system/lib64/broken.so'; bad.write_bytes(b'\\x7fELFbroken')
   report=pathlib.Path(td)/'report.json'; txt=pathlib.Path(td)/'report.txt'
   subprocess.run(['python3',str(TOOL),str(root),'--report',str(report),'--props-report',str(txt)],check=True)
   data=json.loads(report.read_text())
   self.assertTrue(any(x['path'].endswith('broken.so') for x in data['errors']))
if __name__=='__main__':unittest.main()
