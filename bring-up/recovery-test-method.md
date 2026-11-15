# Data-safe kernel test method (recovery partition)

**The golden rule: never flash an unproven kernel to `boot`. Test it on `recovery`.**

A new/experimental kernel can fail to decrypt or mount `/data` (f2fs + inline crypto +
`fileencryption=aes-256-xts`). Depending on the fstab flags that can trigger a **format of
`/data`**. The `recovery` partition boots a kernel that reaches TWRP / dies long before `/data` is
ever touched, so testing there is **zero risk to user data**. The entire bring-up loop below runs on
`recovery`. Only once a kernel cleanly reaches the point of mounting `/data` do you even consider
`boot` — and then with a full backup and verified crypto config.

## Why not `adb reboot recovery`

With a crashing test kernel on `recovery`, `adb reboot recovery` sets the boot-recovery command and
the device **loops into the crashing recovery**. Enter recovery with the **hardware keys** instead:
power off, then **Vol Up + Power** with USB connected (hold Vol Up a couple of seconds past the logo).

## The loop

Needs: root (Magisk) on the running Android, and `adb`. All commands are root shell on the phone.

```sh
# 0. BACK UP the current recovery first (keep this on the PC; it is your rollback)
dd if=/dev/block/by-name/recovery of=/sdcard/recovery_backup.img
# pull it:  adb pull /sdcard/recovery_backup.img

# 1. push and verify the test image (same TWRP ramdisk/dtb, new kernel)
#    md5 must match before and after writing
dd if=/sdcard/recovery_test.img of=/dev/block/by-name/recovery
sync; echo 3 > /proc/sys/vm/drop_caches
md5sum /dev/block/by-name/recovery      # compare against the source image

# 2. power off, enter recovery with Vol Up + Power (NOT adb reboot recovery)
#    the test kernel runs, crashes within ~1 s, the device reboots

# 3. boot back to Android with the keys, then read the previous boot's kernel log
cat /proc/last_kmsg > last_kmsg.txt      # contains the crash (pc/lr/call trace)
#    also useful: /sys/fs/pstore/console-ramoops

# 4. restore the working recovery
dd if=/sdcard/recovery_backup.img of=/dev/block/by-name/recovery
```

## Capturing the log before it is overwritten

The `sec_log` / `last_kmsg` RAM ring is small and wraps. If the phone runs for a while after the
crash, the 4.19 lines get overwritten by the current Android boot. **Pull `last_kmsg` within the
first minute** after the phone comes back, or script a loop that waits for `adb` to appear and
dumps it immediately.

## Debug-level note (Samsung)

Samsung gates `/proc/last_kmsg` to kernel content only when the debug level is **MID/HIGH**. On
LOW (`sec_debug=0` in the cmdline) you get LK (bootloader) lines only. Set the debug level via
`*#*#4636#*#*`-style menus or the engineering dialer; verify with the cmdline read from TWRP
(`cat /proc/cmdline`). In practice on this device the 4.19 kernel log appeared in `/proc/last_kmsg`
even on LOW, read without root from Android — try that first.

## Repacking a test image

Use [`tools/a31_bootimg.py`](../tools/a31_bootimg.py) to swap only the kernel into an existing TWRP
image (ramdisk, dtb, dtbo, cmdline unchanged):

```sh
python3 a31_bootimg.py repack old_twrp.img out.img --kernel Image.gz
# verify only the kernel changed:
python3 a31_bootimg.py info out.img
```

## Flashing `boot` later (when the kernel is proven)

Same `dd` to `/dev/block/by-name/boot` from a rooted Android — **no reboot to a special mode, no
TWRP, and `/data` is not touched by the flash itself**. The only risk is the *new kernel* failing to
mount `/data` on the next boot, so: (1) back up `boot` first, (2) confirm the kernel's crypto config
(`FS_ENCRYPTION_INLINE_CRYPT`, `MMC_CRYPTO_LEGACY`, SDP/FSCRYPT) matches the vendor, (3) keep an Odin
`recovery.tar` / `boot.tar` rollback ready. `boot` and `recovery` are separate partitions; flashing
either one never formats `/data` by itself.
