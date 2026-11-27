# QuantumROM method review — transferable porting primitives

**Reviewed:** 2026-11-27  
**Reference:** SN-Abdullah-Al-Noman/QuantumROM (public repository, main workflow and `scripts/QuantumRom.sh` inspected).  
**Scope:** Adapt concepts, not copy its One UI firmware build pipeline wholesale. QuantumROM is primarily a Samsung firmware-to-custom-ROM builder, not a universal GSI compatibility patcher.

## Verified workflow structure in QuantumROM

The workflow exposes explicit source/target inputs: source-stock device configuration, target Samsung device and CSC/download source, firmware version, output filesystem (EROFS/ext4/F2FS), and feature switches. Its pipeline then:

1. validates and downloads a source-device configuration directory;
2. downloads/extracts target Samsung firmware;
3. extracts super and partition images;
4. extracts partition filesystems;
5. applies source-device configuration;
6. runs selected ROM modifications and patches;
7. builds output filesystem images and packages/releases them.

Its helper script includes filesystem detection (sparse/ext2/3/4/F2FS/EROFS), sparse conversion, super-image unpacking, extraction paths for ext4/EROFS/F2FS, and image build helpers. These are transferable engineering ideas.

## What is and is not transferable to a GSI port

- **Transferable:** staged pipeline; explicit device/source/target profiles; filesystem-aware extraction; sparse-image conversion; repeatable transformations; configurable output FS; logs/artifacts.
- **Not directly transferable:** Samsung stock firmware extraction and CSC-specific ROM assembly, Samsung framework/SSRM patches, debloating, feature additions, Bluetooth patching and stock-device configuration. Those operations assume Samsung firmware internals and may be inappropriate or harmful on a generic GSI.
- **No verified evidence found in the inspected workflow that QuantumROM performs universal GSI-to-device porting or tests arbitrary GSI boots.** This kit will not represent those features as proven.

## Proposed port-engine architecture

### Stage A — intake and immutable source
Preserve the downloaded payload, record URL/filename/size/SHA256, identify archive members, and avoid modifying the source file.

### Stage B — image identification and extraction
Identify sparse/raw images and supported FS types; extract into a work tree using a dedicated backend per filesystem. Unknown formats remain preserved and clearly labeled.

### Stage C — profile-driven analysis
Load an A31 profile containing verified partition sizes/layout, mount expectations, vendor compatibility facts, architecture, API level and known boot-log signatures. Missing facts remain unknown rather than guessed.

### Stage D — diagnostic-first compatibility
Inspect build properties, mount/fstab references, SELinux policy/version mapping, overlays, required partition references, and image size constraints. Produce an evidence report before applying changes.

### Stage E — opt-in patch recipe
Apply only patch operations with explicit preconditions, backup/diff, testable postconditions and reversible output. Recipe failures must not be swallowed or mislabeled as successful ports.

### Stage F — image rebuild and artifact
Rebuild only supported FS targets, preserve ownership/modes/contexts where tooling permits, report limitations, checksum output and provide a patch manifest. A successful CI run is not a boot test.

## Reference
- QuantumROM: https://github.com/SN-Abdullah-Al-Noman/QuantumROM
- Reviewed `.github/workflows/QuantumROM.yml` and `scripts/QuantumRom.sh` (repository main).