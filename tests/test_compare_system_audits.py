import importlib.util,pathlib,unittest
P=pathlib.Path(__file__).resolve().parents[1]/'tools/compare_system_audits.py'
spec=importlib.util.spec_from_file_location('compare',P);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Compare(unittest.TestCase):
 def test_missing_names_and_abi(self):
  target={'root':'T','elf':[{'path':'lib/a.so','soname':'a.so','needed':['b.so','missing.so'],'machine':'AArch64','elf_class':'ELF64'},{'path':'lib/b.so','soname':'b.so','needed':[],'machine':'AArch64','elf_class':'ELF64'}]}
  donor={'root':'D','elf':[{'path':'donor/a.so','soname':'a.so','needed':[],'machine':'ARM','elf_class':'ELF32'}]}
  r=mod.compare(target,donor)
  self.assertEqual(r['missing_soname_names_in_donor'],['b.so'])
  self.assertEqual(r['target_needed_names_missing_from_target_inventory'],['missing.so'])
  self.assertEqual(r['target_needed_names_missing_from_donor_inventory'],['b.so','missing.so'])
  self.assertTrue(r['shared_soname_abi_evidence'][0]['abi_differences'])
  self.assertEqual(r['runtime_compatibility'],'NOT ASSESSED')
if __name__=='__main__':unittest.main()
