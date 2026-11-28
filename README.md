# MT6768 / Galaxy A31 (SM-A315F) Kernel Porting Kit

A field guide and toolbox for bringing up custom kernels on the **MediaTek MT6768 (Helio P65)**,
targeting the **Samsung Galaxy A31 (SM-A315F)**. It collects the parts that are hard to find and
hard to re-derive: a **crash database** from real boots, a **data-safe test method**, the **A31
patch stack**, build configs and tools, ready-to-use **Magisk modules**, and the roadmap from the
working 4.14 kernel toward a **5.10 GKI** build.

Everything here was produced while bringing the device up on a One UI 8 (Android 16) port
(UN1CA) running on the **stock Android 12 vendor** (`A315FXXS5DXB1`). The guiding rule throughout:
**the kernel adapts to the stock vendor's 4.14 ABI — the vendor partition is never patched; vendor
tweaks are done with a Magisk overlay instead.** (One narrow exception: the
[GSI vendor fstab patcher](tools/patch_vendor_fstab.sh) flips a `nofail` flag on a partition
*you've already removed from the layout* — see [`crash-database.md#5`](bring-up/crash-database.md).
That's fixing a self-inflicted boot-blocker from the GSI pairing itself, not a stock-vendor
behavior change, so it doesn't fit the Magisk-overlay model the rest of this kit uses.)

> Maintained by [@Mouhamad10](https://github.com/Mouhamad10). If you are porting another MT6768
> device, the bring-up method and crash database transfer almost directly; the device-specific
> drivers (touch, PMIC, panel, cameras) are what you swap.

## What's in here

| Path | What it is |
|---|---|
| [`docs/`](docs/) | Device facts, the kernels and their sources, mainline/GKI status, build environment |
| [`bring-up/`](bring-up/) | **The crash database**, the recovery-safe test method, the 4G/modem investigation, the exFAT/sdfat fix |
| [`patches/`](patches/) | The A31 patch stack (29 patches) on top of the 4.19 `fire` base |
| [`configs/`](configs/) | `a31_defconfig` + the fragment |
| [`tools/`](tools/) | Boot-image (un)packer, DT-table tools, build scripts, merge helpers, [vendor fstab patcher](tools/patch_vendor_fstab.sh) + [sepolicy mapping checker](tools/check_sepolicy_mapping.py) |
| [`flashable/`](flashable/) | [TWRP-flashable zip](flashable/README.md) that disables a stale vendor fstab entry on an already-flashed `/vendor`, no re-flash needed |
| [`magisk/`](magisk/) | Touch watchdog and LTE-guard modules (no kernel change needed) |
| [`roadmap/`](roadmap/) | Feature targets: KernelSU, fast charge, NetHunter, EROFS, Windows-on-ARM drivers, 5.10 GKI |

## Source trees (full kernel sources, hosted separately)

This kit holds the **patches and documentation**, not gigabytes of upstream source. The full trees:

| Kernel | Base | Repo |
|---|---|---|
| **Atrocious V6** (daily driver, 4.14.186) | Samsung A31 4.14 | [`Mouhamad10/SM-A315F`](https://github.com/Mouhamad10/SM-A315F) (branch `A315FXXS5DXB1`) |
| **Lucreticus** (4.14.357 + eBPF backports) | stardustps mt6768 | [`Mouhamad10/kernel_samsung_mt6768-lucreticus`](https://github.com/Mouhamad10/kernel_samsung_mt6768-lucreticus) (branch `r1-Armaros`) |
| **A31 4.19 port** (this kit) | Xiaomi `fire` 4.19.325-cip @ `9937de9f6` | upstream [`mt6768-dev/android_kernel_xiaomi_fire`](https://github.com/mt6768-dev/android_kernel_xiaomi_fire) + apply [`patches/`](patches/) |
| **ROM** | One UI 8 port on stock A12 vendor | [`Mouhamad10/UN1CA`](https://github.com/Mouhamad10/UN1CA) (branch `sixteen`) |

## Start here

1. [`docs/01-device-facts.md`](docs/01-device-facts.md) — SoC, partitions, boot image layout, encryption.
2. [`bring-up/recovery-test-method.md`](bring-up/recovery-test-method.md) — **read this before flashing anything.**
   You test a new kernel by writing it to the **recovery** partition, which never touches `/data`.
3. [`bring-up/crash-database.md`](bring-up/crash-database.md) — every boot crash hit so far, its root cause, and the fix.

## License

Kernel patches are GPL-2.0 (they derive from the Linux kernel). Scripts and documentation in this
repo are provided as-is for the porting community.

## Boot-log triage

Feed a kernel log (text or a binary ramoops/pmsg dump) to
[`tools/triage-bootlog.py`](tools/triage-bootlog.py) — or the
**"Triage a boot log"** GitHub Action — and it matches the log against a database of known
signatures and tells you which fault fired and where its fix is documented. See
[`bring-up/boot-log-signatures.md`](bring-up/boot-log-signatures.md).

## Activity log

Dated entries for runs done *on the repo owner's behalf, using their vendor/GSI and their
authorization* - not every commit, just end-to-end tool runs worth a record of what was tested
and what the result actually was.

### 2026-11-25 — Android 16 GSI vs the lumi vendor: cause #1 checked, a full port run end-to-end

Two things, both against the official Google AOSP ARM64 GSI
(`aosp_arm64-exp-BP2A.250605.031.A3-13578795-82277143.zip`, Android 16 QPR1, no GMS) and the same
`vendor_a31_lumi.img` from [`oneos-a31` release `vendor-lumi-ext4-v1`](https://github.com/Mouhamad10/oneos-a31/releases/tag/vendor-lumi-ext4-v1)
used throughout [`crash-database.md#5`](bring-up/crash-database.md):

1. **Fixed `patch-vendor.yml` first** - its GSI-mapping-check step couldn't handle a `.zip` GSI
   (Google ships GSIs that way; the step only handled `.xz`/`.gz`/raw) and swallowed the mapping
   check's own exit code with `set +e`, so a missing-mapping failure would have silently shown as
   "success". Added zip extraction and `set -o pipefail`, so the step's own conclusion now *is*
   the mapping verdict.
2. **Ran `patch-vendor.yml`** with that GSI as `gsi_url`:
   [run 45768318966](https://github.com/Mouhamad10/mt6768-a31-porting-kit/actions/runs/45768318966) -
   every step succeeded, **including** "Download GSI and check sepolicy mapping", which means
   `tools/check_sepolicy_mapping.py` exited 0: **this GSI's `/etc/selinux/mapping/` still ships
   `31.0.cil`**, matching the vendor's `plat_sepolicy_vers.txt=31.0`. Cause #1 (sepolicy
   mapping-version gap) is **ruled out** for this specific vendor+GSI pairing - confirmed by the
   step's own conclusion, not by reading its log (log/artifact content isn't reachable from every
   environment that might run this check; the step conclusion is).
3. **Ran `gsi-port.yml`** on the same GSI as an actual port, not just the mapping check:
   [run 45768321305](https://github.com/Mouhamad10/mt6768-a31-porting-kit/actions/runs/45768321305) -
   every step succeeded end-to-end (download, normalize to raw ext4, apply the A31 system recipe,
   shrink/repack, assemble the flashing kit), producing the `a31-ported-gsi` artifact (~986 MB).

**What this does and does not prove:** the pipeline runs clean and cause #1 is cleared for this
GSI - that's real signal, worth having before spending a flash cycle on it. It is **not** a
confirmed boot on real hardware; nobody has flashed this exact output yet. If it still doesn't
boot, the mapping gap (cause #1) and the stale `product` fstab entry (cause #2, already fixed by
`tools/patch_vendor_fstab.sh` / the TWRP zip in [`flashable/`](flashable/)) are both now ruled
out or fixed, so the next failure would be a genuinely new fault - worth a fresh
`console-ramoops` capture and a `tools/triage-bootlog.py` run rather than re-suspecting either of
these two.

## Getting started

New here? Read [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md) — what the repo is, every feature, and exactly how to run the three GitHub Actions.


## GSI Port Engine development log

### 2026-11-27 — permissive GSI intake foundation (MT6768 / Helio P65 / Galaxy A31 SM-A315F)

- Reworked the GSI Action to accept direct image and archive URLs and preserve the payload if normalization or filesystem recognition is not possible.
- Added an intake/normalization helper for ZIP, 7z (when available), XZ, gzip, LZ4, and Android sparse images.
- ZIP/7z member selection prefers a recognizable system image name; if none is found, it falls back to a candidate instead of blocking the run.
- Outputs include source and normalized SHA256, split image chunks, and a status file.
- No porting success or boot compatibility is asserted: device-specific modifications are a work-in-progress and require verified tests.

**Next ideas:** build a filesystem-aware editing stage (ext4/EROFS), collect and index A31/A41 crash logs and console/pmsg/ramoops traces, add reproducible fixes with test cases, compare approaches from established GSI port workflows (including Cantium references once the exact source is identified), implement density/overlay/property and compatibility changes with audit logs, then run CI validation and device testing.

**Current scope:** intake and packaging foundation only. It does not yet perform a proven A31-specific ROM port or guarantee boot.


### 2026-11-27 — QuantumROM workflow study

- Reviewed the upstream QuantumROM workflow and `scripts/QuantumRom.sh`.
- Documented transferable engineering primitives (staged pipeline, profile-driven processing, filesystem detection/extraction/build, reproducible logs) and Samsung-specific steps that must not be copied blindly into a GSI workflow.
- Added [`docs/quantumrom-method-review.md`](docs/quantumrom-method-review.md) with verified findings and a proposed diagnostic-first port-engine architecture.
- QuantumROM is a Samsung firmware/custom-ROM builder; the inspected source does not establish arbitrary GSI porting or boot validation, so the kit will adapt reusable filesystem/pipeline techniques rather than claim equivalence.


### 2026-11-27 — read-only filesystem inspector

- Added `tools/gsi_fs_inspect.py`, a conservative metadata inspection stage: ext4 via `debugfs`, EROFS via `dump.erofs`, and F2FS via `dump.f2fs` when available. It does not mount images or modify them.
- Added CI dependencies for filesystem inspection tooling and tests covering unknown inputs and F2FS signature identification. Tool output is recorded as diagnostics, never treated as compatibility proof.
- Corrected `gsi_prepare.py` filesystem-signature handling after spotting a syntax defect in an intermediate F2FS change; the helper was rewritten cleanly and now identifies EXT4, EROFS and F2FS signatures.

### 2026-11-27 — payload extraction and normalization engine

- Added `tools/gsi_extract.py`: selects a single system payload from ZIP/TAR/7z archives without expanding archive paths, and normalizes XZ/gzip/LZ4 and Android sparse payloads where the required tools exist.
- Produces `system.img` plus a JSON provenance report containing source/output SHA-256, selected archive member, transformations and filesystem hint. Raw unknown inputs are preserved rather than falsely classified.
- Added synthetic tests for safe ZIP-member handling and preservation of opaque payloads. Added F2FS recognition to the intake filesystem hint.
- The engine extracts/normalizes the image payload only; it does not yet unpack filesystem contents, modify ROM files, assess compatibility, or claim boot success. Tests and CI status remain pending actual workflow execution.

### 2026-11-27 — first diagnostic analyzer stage

- Added `tools/gsi_analyze.py`: read-only signature identification for Android sparse, ext4, EROFS, F2FS, XZ, gzip, LZ4, ZIP and TAR, archive listing where supported, SHA-256, candidate system image listing, and a JSON report explicitly marking compatibility and boot validation as unassessed.
- Added signature tests and a dedicated CI workflow for tests plus CLI smoke testing.
- Smoke-checked the four filesystem/image signatures (sparse, ext4, EROFS, F2FS) against synthetic byte fixtures in this session. This does **not** yet prove the GitHub workflow executed or test real images.
- Fixed TAR signature detection to inspect the TAR magic offset rather than the initial header bytes.
- Next: implement actual extraction backends, sparse conversion and safe archive-member handling, then image-level diagnostics and an audited recipe.


### 2026-11-27 — GSI port engine steps 3–7 foundation

- Added ZIP/TAR image-member inventory (no extraction) to make multi-image archive selection explicit.
- Added a heuristic scan for fstab, mount and logical-partition references in extracted trees.
- Added an A31 compatibility evidence report template and a CLI report that deliberately lists unresolved vendor/HAL, kernel ABI and SELinux checks rather than declaring compatibility.
- Added a documented reversible-recipe format; recipes are review/dry-run-first and not automatically applied.
- Added opt-in EROFS rebuild CLI restricted to standard LZ4 compression (`-zlz4`) or uncompressed output. LZ4HC and advanced EROFS features are excluded. Output hash/size and available fsck result are recorded; no boot claim.
- **Validation caveat:** these are newly committed foundations; runtime tests and actual device boot are not yet verified.


### 2026-11-27 — focused regression coverage and safety hardening

- Added tests for archive inventory, layout-reference scanning, compatibility-report honesty, and rebuild-tool absence handling.
- Fixed module-relative import handling in the A31 compatibility report.
- EROFS rebuild now refuses an output path inside the source tree and fails if an available fsck.erofs reports validation failure. Compression choices remain strictly standard LZ4 or uncompressed.
- Test execution/CI results remain pending confirmation from Actions.


### 2026-11-27 — bounded extraction and staged EROFS rebuild hardening

- Added streaming output bounds for external LZ4 and sparse-image converters; sparse headers are checked against the declared expanded size limit before conversion.
- Normalized payloads are staged in a unique temporary workspace, and final image/report files are replaced only after image processing completes. Inputs inside the output directory are rejected.
- EROFS builds now stage the output, validate compression and tree/output paths, run `fsck.erofs` when available, and preserve an existing output if validation fails.
- Added regression coverage for path rejection, sparse-size checks, duplicate ZIP members, and staged EROFS validation. These tests are committed but have not yet been executed locally or confirmed in Actions.


### 2026-11-27 — GSI workflow now uses bounded extractor

- Routed the manual GSI port workflow through `gsi_extract.py` rather than the older permissive intake normalizer; its provenance report is included with the packaged output.
- The current bounded extractor handles raw payloads, ZIP/TAR/7z-selected payloads, gzip/XZ, LZ4 and sparse conversion when tools are present. 7z member extraction is streamed through a size bound rather than expanding archive paths into the workspace.
- GitHub Actions should execute the test suite on this push; execution results are not yet verified from this session.


### 2026-11-27 — configurable expanded-image limit

- The extraction ceiling is configurable instead of fixed: the CLI accepts `--max-bytes`; the manual GSI workflow exposes `max_bytes` with an 8 GiB default (8589934592 bytes). Users can raise it for large payloads or lower it to constrain extraction. This ceiling applies to the expanded normalized payload, not the compressed download size.
- Added regression coverage for choosing a ceiling that permits a larger payload and rejects a payload beyond the chosen ceiling. Test execution remains unverified.


## System compatibility audit (experimental)

A new read-only tree analyzer (`tools/system_tree_audit.py`) inventories ELF dependencies/SONAME duplicates, property value conflicts, init scripts, APK/APEX and overlay paths. It deliberately does not delete duplicate libraries or change properties/HAL services automatically: duplicate names are not evidence of boot-breaking conflict. See [docs/system-tree-audit.md](docs/system-tree-audit.md). **Actual Flyme OS 16 image testing is pending** because the Pixeldrain payload could not be downloaded in this session. This analyzer is not yet an automated image extractor or a verified porting patch engine.


### 2026-11-28 — expanded system-side evidence inventory and guarded reversible patches

- Expanded the read-only analyzer to capture init service declarations, linker-config files, fstab candidates and filename-based HAL/service leads alongside ELF dependency hashes, SONAME findings, property conflicts, APK/APEX and overlays.
- Added a reversible extracted-tree property patch helper with SHA-256 preconditions, rollback manifests and guarded rollback; it refuses a stale source hash or changed patched file.
- Added synthetic tests and CI for patch apply/rollback and hash rejection. Real-image testing remains pending; this is not a boot-compatibility verdict.
- Layout rule: `super` is a dynamic-partition container; logical `system`, `vendor`, `odm`, `product` are distinct, and this kit does not assume a standalone `system_ext` image. The system-side analyzer scans the supplied tree including system_ext files when merged there.


### 2026-11-28 — read-only image extraction stage

- Added `tools/system_image_extract.py` to extract supported raw ext4/EROFS system images without mounting or writing to the image; it refuses unknown formats and non-empty destinations.
- Added extraction guard tests and CI. Sparse/compressed input still requires normalization first; extraction fidelity must be verified and is not boot validation.


#### Validation snapshot (2026-11-28)

- Reversible property patch CI run `46121784821`: **success** (apply/rollback and hash-precondition tests).
- System tree audit CI run `46121827554`: **success** (synthetic property-conflict, init-service, linker-config and inventory smoke test).
- System-image extraction guard CI `46121859555`: **pending at this update**; not yet counted as passing.
- Port-engine validation `46121827560`: **success** for commit `b7f20190` (existing engine validation; does not validate real ROM compatibility or image extraction).


### 2026-11-28 — patch-engine preflight hardening

- Property patch application now validates every operation and source hash before writing any target file; duplicate target-file operations are refused.
- Writes use staged temporary files and replace, and failures during the write sequence trigger restoration of already-written targets.
- Duplicate active assignments for the same property are collapsed into a single assignment while comment lines remain untouched; added regression tests for preflight refusal and duplicate keys.
- These are extracted-tree operations only. Property semantics and device compatibility still require evidence and runtime validation.


### 2026-11-28 — init graph evidence expanded

- Analyzer now captures init `import` declarations and `on` trigger blocks in addition to service declarations. These are textual leads to dependency/activation paths, not runtime state.
- Regression fixture verifies import and trigger extraction.


### 2026-11-28 — ELF ABI/linker metadata inventory

- The system-tree audit now records ELF class, machine architecture, endianness, requested interpreter and RPATH/RUNPATH in addition to SONAME, DT_NEEDED and SHA-256.
- Added a compiler-generated shared-library regression test for those fields. CI verification is pending for this commit; this metadata is evidence for donor/target comparison, not proof of Android namespace resolution or boot compatibility.
