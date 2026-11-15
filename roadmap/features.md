# Feature roadmap

Targets for the A31 / MT6768 kernels and ROM. Items marked **done** are in this kit; the rest are
the planned direction. Each is tagged by where the work lives: **[kernel]**, **[vendor-overlay]**
(Magisk, no vendor flash), **[ramdisk/recovery]**, or **[rom]**.

## Done / working

- **EROFS with full compression** **[kernel]** — `EROFS_FS` + `EROFS_FS_ZIP` on in `a31_defconfig`.
- **Data-safe kernel testing** **[recovery]** — flash to `recovery`, never `/data`. See bring-up docs.
- **exFAT SD support on 4.14** **[kernel]** — 1-byte sdfat `time_offset` fix.
- **Touch watchdog** **[vendor-overlay]** — re-enables the IST4050 touch that One UI disables on
  screen-off. `magisk/a31_touchfix`.
- **LTE/4G hang workaround** **[vendor-overlay]** — `magisk/a31_lte_guard`.
- **Magisk** **[ramdisk]** — stock daily boot is Atrocious + Magisk; keep the Magisk ramdisk
  byte-identical when swapping the kernel in a boot image.

## Kernel features to add

- **KernelSU** **[kernel]** — needs a 5.10+ kernel for the non-GKI-patch (manager) path, or the
  kprobe-less integrated path on 4.19/5.10. Not viable cleanly on the 4.14 Samsung tree; target it
  on the 5.10 GKI build.
- **Fast charging / charge control** **[kernel]** — the A31 charger is the Samsung **S2MU106**
  (`drivers/battery` / `leds-s2mu106`). Expose charge-current / input-current sysfs and a charge
  limit; the S2MU106 driver is already imported in the 4.19 patch stack.
- **NetHunter drivers** **[kernel]** — Kali NetHunter needs: external Wi-Fi injection chipsets
  (RTL8812AU/8188EUS/etc. as modules), `CONFIG_USB_CONFIGFS_F_HID`/HID gadget, `CONFIG_USB_ACM`,
  DriveDroid-style mass-storage gadget, CD-ROM emulation, and often `CONFIG_SYSVIPC`,
  `CONFIG_BRIDGE`, `wireless ext`. All are kernel config + driver adds; no vendor change.
- **Windows-on-ARM drivers** **[kernel/firmware]** — booting Windows (as seen on some Snapdragon
  tablets) needs a UEFI firmware port (edk2) and WoA device drivers (DSDT/ACPI, GPU, USB, storage,
  touch). On MediaTek this is a very large, separate effort (no public edk2 for MT6768); track as a
  long-term research item, not a kernel patch.
- **Thermal sysrst fix** **[kernel]** — the open crash #3; correct the AP NTC auxadc channel mapping
  so the thermal zone stops reporting a bogus temperature and `BUG()`-rebooting.

## ROM / userspace

- **One UI 8 (UN1CA)** **[rom]** — the running port; keep it on the stock A12 vendor.
- **GSI support** **[rom]** — document which GSIs boot on the A31 vendor and their quirks.

## Porting to another MT6768 device

The bring-up method and crash database transfer almost unchanged. What you swap per device:
the **touch driver**, **panel/display**, **PMIC/charger**, **cameras**, the **device tree**, and the
**EINT/thermal/efuse** node names. Keep the same rule: kernel speaks the stock vendor's ABI; vendor
tweaks via Magisk overlay; test on `recovery` first.
