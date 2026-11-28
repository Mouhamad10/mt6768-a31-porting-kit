# Evidence-driven Port Engine (experimental)

The engine reads a log and the signature database, emits structured diagnoses/correlations, and can generate **guarded property-only** proposals from an explicitly authored recipe file.

```sh
python3 tools/port_engine.py boot.log --report triage.json
python3 tools/port_engine.py boot.log --tree extracted_system --recipes approved-recipes.json --report triage.json --patch proposed.json
python3 tools/port_engine.py boot.log --tree extracted_system --recipes approved-recipes.json --apply --rollback-manifest rollback.json
python3 tools/system_patch.py rollback extracted_system rollback.json
```

Recipes are user/maintainer-authored, not synthesized guesses. Each recipe must identify a signature, a relative target path, property key/value, and exact expected SHA-256 of the target file. The engine rejects path escapes, absent files, stale hashes, and unsupported operations. `--apply` delegates to the existing transactional hash-guarded patcher. Review reports and patch proposals before applying. The current engine does **not** parse kernel stack traces semantically, alter ELF/APEX/SELinux/init files, or validate boot compatibility; unmatched signatures remain diagnostic-only. Recipe applicability is evidence of matching log signature and file hash, not proof the change is correct for every ROM/device.

## Guarded exact-text edits (new experimental capability)

Recipes may also use `type: replace_exact` to replace a literal text block in one UTF-8 file. The block must be non-empty, differ from the replacement, and occur **exactly once** in the target file. A full-file SHA-256 precondition is required. The engine rejects ambiguous matches and the patch applier rechecks the hash and uniqueness before writing. Edits are staged and written atomically; rollback is hash-guarded. This is not a syntax-aware init/SELinux/linker validator, so generated proposals require human review and downstream validation. Never use this to blanket-disable services or broaden SELinux policy.
