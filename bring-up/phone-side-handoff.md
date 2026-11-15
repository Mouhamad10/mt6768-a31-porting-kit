# A31 (SM-A315F) kernel 4.19 test

You run on the laptop that has the phone on USB (adb + Odin available). A cloud session builds the
kernel; your job is to flash test images **only to the recovery partition**, reproduce the crash, and
collect logs. Be careful and quick. Report results back to the user in one short message.

## Hard safety rules
- NEVER write to `boot`, `dtbo`, `vbmeta`, `super`, `userdata`, `misc` or any partition other than `recovery`.
- NEVER wipe/format anything. Do not run TWRP wipe/format/repair.
- Before every flash, keep `recovery_backup.img` (current working TWRP) on the laptop.
- Do not use `adb reboot recovery` with a test image (it sets the boot-recovery command and the phone
  then loops into the crashing recovery). Enter recovery with keys: power off, then Vol Up + Power
  with USB connected.
- If the phone loops: Download mode (Vol Down + Power ~7 s, then immediately Vol Up + Vol Down and
  plug USB), Odin AP = `recovery.tar` containing the backup renamed `recovery.img` (7-Zip, tar format).

## State
- `boot` = Atrocious V6 public0 + Magisk 30 (working). Leave it.
- `recovery` = old working TWRP. Test image: `recovery_twrp_a31_4.19_test2.img`
  (md5 6dc322f8cf67f60b2113f9405be30fdc): same TWRP ramdisk/dtb/dtbo, new 4.19 kernel.
- Symptom: Samsung logo ~3 s, a green line flashes for a fraction of a second, reboot. LK's RAM_CONSOLE
  then reports `wdt_status 0x0, exp_type 0x0` (no WDT/KE recorded) — the kernel dies very early.
- Do NOT use any ramoops `ramoops.*` kernel cmdline: it makes even the old kernel crash.

## Goal: get the 4.19 kernel's own log
The new kernel mirrors its console into Samsung's sec_log buffer (0x46C00000). Samsung shows it as
`/proc/last_kmsg` only when the debug level is MID (cmdline currently has `sec_debug=0`).

1. In Android, ask the user to dial `*#9900#` → Debug level → MID (phone reboots). Verify with
   `adb shell cat /proc/cmdline` that `sec_debug=0` is gone/changed. If *#9900# is unavailable, stop and tell the user.
2. Backup and flash the test image to recovery (from Android with Magisk root, or from TWRP):
   ```
   adb shell su -c "dd if=/dev/block/by-name/recovery of=/sdcard/recovery_backup.img"
   adb pull /sdcard/recovery_backup.img
   adb push recovery_twrp_a31_4.19_test2.img /sdcard/
   adb shell su -c "dd if=/sdcard/recovery_twrp_a31_4.19_test2.img of=/dev/block/by-name/recovery"
   ```
   (In TWRP, drop `su -c`. If `su -c` fails in Android, run `adb shell`, then `su`, then the command.)
3. Power off, enter recovery with keys. If an "Upload mode" screen appears, ask the user for a photo,
   then Vol Down + Power ~7 s.
4. As soon as Android is up (no full power-off in between):
   ```
   adb shell su -c "cat /proc/last_kmsg" > last_kmsg_419.txt
   adb shell su -c "cat /proc/cmdline" > cmdline.txt
   ```
   Check that `last_kmsg_419.txt` contains `4.19.325`. If it only contains LK lines (`[LK]`, `LK_LOG_STORE`),
   say so.
5. Restore the old TWRP: `dd` of `recovery_backup.img` to recovery.
6. Give the user `last_kmsg_419.txt` (the last ~200 lines matter most) to send to the cloud session.
