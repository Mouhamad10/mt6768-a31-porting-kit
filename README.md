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
