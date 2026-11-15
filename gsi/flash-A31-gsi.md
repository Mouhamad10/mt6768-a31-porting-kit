# Flashing a GSI on the A31 (SM-A315F)

The A31 uses **dynamic partitions** (a `super` partition that holds `system`/`vendor`/`product`/
`odm` as logical images). You flash a GSI into the logical `system` through **fastbootd**, not by
`dd`. Bootloader must be unlocked (OEM unlock on, orange verified-boot state). This device is
Project-Treble; most arm64 A/B-or-A-only GSIs (`system-arm64-ab*.img`) can be tried.

## Steps

1. **Back up** your current working setup (at least `boot` and a Nandroid in TWRP). A GSI replaces
   `system`; keep a way back.
2. Reboot to bootloader, then to **fastbootd**:
   ```sh
   adb reboot bootloader
   fastboot reboot fastboot        # enters fastbootd (dynamic-partition aware)
   fastboot getvar is-userspace    # should print: yes
   ```
3. (If the GSI refuses to boot with verification on) flash a **disabled vbmeta** - see
   [`disable-vbmeta.md`](disable-vbmeta.md).
4. Flash the GSI into `system`:
   ```sh
   fastboot flash system system.img      # the raw/sparse image this kit produced
   ```
   If it complains the logical partition is too small:
   `fastboot delete-logical-partition product` (frees space), or use a smaller GSI.
5. **Wipe data** (GSIs almost always need a clean `/data`): reboot to recovery and factory reset,
   or `fastboot -w` (this erases userdata - make sure you backed up).
6. Reboot. First boot can take several minutes.

## Keep the stock kernel/vendor

A GSI only replaces **system**. Keep the A31 `boot` (kernel) and `vendor` as they are - the GSI
talks to the stock vendor HALs. If the GSI needs a newer vendor than A12, that's a separate vendor
port (not covered by just flashing a GSI).

## What usually needs manual fixups (the "porting" half)

Flashing is deterministic; **making a specific GSI fully work is not**. Common per-GSI fixups:

- **No RIL / mobile data**: vendor/GSI mismatch; may need a `fixup` overlay or a different GSI build.
- **No sensors / fingerprint**: HAL mismatch.
- **Bootloop / no display**: wrong GSI type (try `a-only` vs `a/b`, `vndklite`, a different Android
  version) or vbmeta not disabled.
- **SELinux denials**: use a `permissive` GSI variant first to confirm the base boots.

Pick the GSI variant that matches the device: **arm64, A-only** (the A31 is A-only), and an Android
version whose vendor requirements the A12 vendor can satisfy (Android 13-16 GSIs commonly boot on
A12 vendor with vndklite). Confirm boot on a `permissive` build, then move to enforcing.
