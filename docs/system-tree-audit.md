# System compatibility audit (experimental)

Run on an **extracted system-side directory** (including files physically under the system root that represent system_ext; no standalone system_ext partition is assumed):

`python3 tools/system_tree_audit.py TREE --report audit.json --props-report audit.txt`

The read-only analyzer inventories ELF SONAME/DT_NEEDED/hash plus ELF class, machine, endianness, interpreter and RPATH/RUNPATH metadata, duplicate SONAME candidates, property conflicts with file and line, init RC files and service declarations, linker-config files, fstab candidates, filename-based HAL/service hints, APK/APEX and overlay paths.

**Interpretation limits:** duplicate SONAME is not proof of a linker collision; property collisions depend on partition and load precedence; filename hints do not establish HAL availability or registration; init inventory is not runtime service state. Correlate findings with target vendor manifests, VINTF, linker namespace definitions, SELinux, logs and actual boot.

The Flyme OS Android 16 image test is **not completed**: the previously supplied Pixeldrain payload could not be fetched in the environment. The analyzer has not been run against that real image. It does not mount or extract images and does not modify files.

Related reversible helper: [docs/reversible-system-patches.md](reversible-system-patches.md). That helper is limited to hash-guarded property updates on an extracted tree with a rollback manifest; it is not a compatibility verdict.


## ELF ABI triage

Each ELF inventory record includes ABI metadata collected from `readelf`: class (32/64-bit), machine architecture, byte order, program interpreter (when present), and RPATH/RUNPATH. These fields help flag architecture and linker-search-path mismatches when comparing donor and target trees. The analyzer does not resolve Android linker namespaces or prove that any dependency can be loaded at runtime; comparison and namespace-aware validation remain separate steps.


## Compare donor and target reports

Run the analyzer separately against each extracted tree, then compare the JSON inventories:

```sh
python3 tools/system_tree_audit.py TARGET_TREE --report target.json --props-report target.txt
python3 tools/system_tree_audit.py DONOR_TREE --report donor.json --props-report donor.txt
python3 tools/compare_system_audits.py target.json donor.json --output elf-compare.json
```

The comparison reports target SONAME names absent from the donor inventory, aggregate DT_NEEDED names missing from either inventory, and ABI metadata differences for shared SONAME names. It is a triage report, not an instruction to copy files: namespace visibility, symbol compatibility and HAL/runtime requirements must be assessed before changes.
