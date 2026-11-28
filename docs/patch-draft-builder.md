# Review-only patch draft
python3 tools/patch_draft_builder.py extracted-system-tree init.rc system.prop --output patch-draft.json

The builder creates hash-locked incomplete templates. The output deliberately uses a separate schema that cannot be fed directly into the patch applier. Fill the exact replacement strings, convert to the guarded patch schema only after review, and validate the target subsystem. It never modifies the tree.
