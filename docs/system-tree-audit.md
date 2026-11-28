# A31 System Compatibility Engine (experimental)

This revision adds an evidence-first **system-tree audit** stage to the GSI porting toolkit.

## Scans
- ELF files using `readelf`: path, SONAME, DT_NEEDED and SHA-256.
- Duplicate SONAME candidates, reported but not automatically removed.
- Conflicting property values across files, including file path and line.
- Init rc, APK, APEX and overlay inventory.

## Why duplicate libraries are not automatically deleted
Duplicate names alone do not establish a harmful conflict. Android linker namespaces, partition precedence, ABI and service-specific loading determine which library is used. Removing a library based only on name can make the image unbootable. Findings must be correlated with logs and target environment.

## Flyme OS Android 16 test status
The Pixeldrain download supplied in chat could not be fetched in this environment because DNS/network access was unavailable. **This code has not been tested on the actual Flyme image.** The audit operates on an extracted system directory. Automated image extraction/mounting and reversible patch application are not yet implemented in this stage.

## Run
```bash
python3 tools/system_tree_audit.py /path/to/extracted/system --report audit.json --props-report audit.txt
```

Read-only inventory only. No automatic library deletion, property rewriting, HAL disabling or boot success claim.
