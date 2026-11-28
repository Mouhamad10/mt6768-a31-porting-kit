# Reversible extracted-system property patch helper

The helper supports only hash-guarded `set_property` operations on extracted system trees.
It requires the expected source SHA-256 for each operation, creates a rollback manifest,
and refuses rollback if the file has changed since patching. It does not mount images,
modify partitions, disable services or delete libraries.

Example patch:
```json
{"schema":"a31-system-patch-v1","operations":[
 {"op":"set_property","path":"system/build.prop","key":"ro.sf.lcd_density","value":"420","expected_sha256":"SOURCE_FILE_SHA256"}
]}
```

Apply: `python3 tools/system_patch.py apply TREE patch.json --rollback-manifest rollback.json`
Rollback: `python3 tools/system_patch.py rollback TREE rollback.json`

Paths must remain inside TREE. Review patches and backups before use. This is a file-tree
operation, not evidence that the property is compatible with a particular device.
