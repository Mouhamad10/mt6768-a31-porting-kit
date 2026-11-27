# GSI Port Engine: steps 3–7

## 3. Multi-image archive inventory
Inventory archive entries before selecting payloads. Never assume the largest image is `system`; names and partition labels are recorded, and selection is explicit. ZIP/TAR metadata listings are safe by default; extraction remains path-safe and payload-focused.

## 4. Layout and mount-reference analysis
Scan an extracted tree for fstab, first-stage mount, logical-partition, and partition-name references. Output is heuristic evidence only, not a resolved partition map.

## 5. A31 compatibility report
Reports must separate facts (filesystem, image metadata, tree references) from unknowns (vendor HAL/API compatibility, kernel ABI, SELinux, boot). No auto verdict or claim of bootability.

## 6. Reversible recipes
Recipes are declarative JSON, with preconditions, exact target paths, before/after hashes where applicable, and rollback instructions. Applying recipes is deliberately not automatic in this stage.

## 7. Rebuild and validation
EROFS rebuild compression is restricted to **standard LZ4 (`-zlz4`) only**, or uncompressed. Do not use LZ4HC, LZMA, deflate/libdeflate, fragments, ztailpacking, dedupe, or large pclusters. Rebuilds are opt-in, require an extracted filesystem tree and `mkfs.erofs`, and are followed by tool-based filesystem checks, size/hash recording, and a validation report. These checks do not constitute device boot testing.
