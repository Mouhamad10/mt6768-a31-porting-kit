# Mainline / GKI status and the 5.10 GKI plan

## Where GKI stands for MT6768

- **4.14 / 4.19** — pre-GKI. Device drivers are built into a monolithic Image; the stock A31 is 4.14.
- **5.4** — GKI 1.0, weak split, still largely vendor-coupled.
- **5.10** — GKI 2.0, mature. Generic `Image` (boot) + device-specific **vendor modules**
  (vendor_boot). This is the realistic modern target that can still run on the **stock A12 vendor**
  with a shim.
- **6.6** — effectively mainline. A MT6768 6.6 exists (`mt6768-mainline/android_kernel_samsung_mt6768`,
  Galaxy A05, TEEGRIS, mali r49p1) but it is a **from-scratch mainline bring-up**, not a port that
  keeps Samsung's A12 vendor stack. A31 on 6.6 means abandoning One UI + the stock vendor and
  bringing up A31's specific hardware (IST4050 touch, smcdsd panel, S2MU106, its cameras) on
  mainline drivers — a months-long research effort. Not a fix for any current device problem.

## Why 5.10 GKI (and not 6.6) for a daily driver

The A31 runs the **stock Android 12 vendor** (RIL/display/camera/sensor HALs + 10 `.ko` all built
for the 4.14 ABI). A 6.6 kernel orphans all of it. A 5.10 GKI kernel can keep that vendor if the
kernel **speaks the vendor's ABI** for the device drivers and the few vendor-side init tweaks are
done with a **Magisk overlay** (never a vendor flash, never a `/data` format).

## The 5.10 GKI port plan (Stage 2)

Base: Samsung **A17 4G (SM-A175F)** kernel **5.10.233** GKI
([`physwizz/A175f-V-u1`](https://github.com/physwizz/A175f-V-u1), `kernel-5.10`) — a Samsung MT6768
5.10 GKI tree, closest starting point.

MT6768 5.10 platform bits that already exist in
[`OnePlusOSS/android_kernel_5.10_oneplus_mt6983`](https://github.com/OnePlusOSS/android_kernel_5.10_oneplus_mt6983):
clk, pinctrl, spm, mcdi, cpufreq_v2, dcm, sound, gpufreq. **Not** present there and to be
forward-ported from the 4.19 `fire` tree: display, ccci (modem), m4u, emi.

Rule (same as the 4.19 work): **drivers that talk to the A31 vendor/firmware keep the A31 (4.14)
version and are fixed for the newer core; the platform core comes from the newer tree.**

### Keeping the stock vendor with a Magisk overlay

1. Build the 10 vendor-module drivers **into** the 5.10 kernel (built-in, not `.ko`).
2. A Magisk module overlays `/vendor/etc/init/*.rc` to delete the `insmod` lines for those modules
   (the real vendor partition stays byte-identical).
3. Verify crypto: `FS_ENCRYPTION_INLINE_CRYPT`, `MMC_CRYPTO_LEGACY`, SDP/FSCRYPT must match before
   any `boot` flash, or `/data` won't mount. Until then, test only on `recovery`.

### Carry-over fixes already solved (apply equivalently on 5.10)

- gpufreq efuse → `get_devinfo_with_index` fallback (crash #1).
- EINT base via `reg_base_eint` phandle (crash #2).
- thermal sysrst / AP NTC auxadc mapping (crash #3, still open on 4.19).
- Note: 5.10's `sdfat`/exfat is newer and does **not** have the 4.14 `time_offset` mount bug
  (see [`../bring-up/sdfat-exfat-fix.md`](../bring-up/sdfat-exfat-fix.md)).
