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

## Getting started

New here? Read [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md) — what the repo is, every feature, and exactly how to run the three GitHub Actions.
