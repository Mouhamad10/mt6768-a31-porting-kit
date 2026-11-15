# AnyKernel3 config for Samsung Galaxy A31 (SM-A315F) / MT6768
# Flashes the built Image.gz into the existing boot image, keeping the current ramdisk.
# Used by .github/workflows/build-kernel.yml (the CI drops Image.gz next to this file).

### AnyKernel properties
properties() { '
kernel.string=MT6768 A31 kernel (built in CI) - Mouhamad10/mt6768-a31-porting-kit
do.devicecheck=0
do.modules=0
do.systemless=1
do.cleanup=1
do.cleanuponabort=1
device.name1=a31
device.name2=a31x
device.name3=SM-A315F
device.name4=r0s
supported.versions=
supported.patchlevels=
'; }

### boot/recovery slot (no A/B on A31)
block=/dev/block/bootdevice/by-name/boot;
is_slot_device=0;
ramdisk_compression=auto;
patch_vbmeta_flag=auto;

# ------------------------------------------------------------------------------
# DATA-SAFE TESTING: to test a kernel without risking /data, flash it to the
# RECOVERY partition instead of boot. Change the line above to:
#   block=/dev/block/bootdevice/by-name/recovery;
# build a second zip, flash it, and boot recovery with the hardware keys.
# See bring-up/recovery-test-method.md.
# ------------------------------------------------------------------------------

## AnyKernel methods (don't edit below unless you know AnyKernel3)
. tools/ak3-core.sh;

## boot install
dump_boot;
write_boot;
## end boot install
