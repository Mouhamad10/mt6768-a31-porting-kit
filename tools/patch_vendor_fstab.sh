#!/bin/bash
# Patch a vendor.img's fstab so partitions removed from the flashed layout (e.g. "product")
# no longer block boot.
#
# Root cause this fixes (see bring-up/crash-database.md#5):
#   fstab.<chip> still lists a removed partition as mandatory -> init queries DM_DEV_STATUS
#   for it at boot, fails ("No such device or address"), the split-sepolicy load that follows
#   cannot find that partition's sepolicy/file_contexts pieces -> init::SetupSelinux() calls
#   InitAborter() -> PID1 dies -> kernel panic -> sec_reboot(bootloader) -> stuck in fastbootd.
#   This fires even with androidboot.selinux=permissive, because it is a policy LOAD failure,
#   not an enforcement denial.
#
# MODE (default: delete). See bring-up/crash-database.md#5 "nofail regression" for why delete
# is now the default: on at least one real device/GSI pairing, adding "nofail" (keeping the
# fstab line, just making it non-fatal) made boot fail EARLIER (first-stage, fast reboot to
# the logo) than the original mandatory-but-unpatched line did (which at least reached
# second-stage init before aborting). The suspected reason is that some GSI builds embed their
# own compatibility stub for a merged/absent product (e.g. a symlink or stub dir shipped
# inside system.img) and a *present-but-empty* fstab entry for the same mount point - even one
# marked optional - can conflict with that stub in first-stage init in a way a fully-absent
# entry does not. Deleting the line outright has not reintroduced that regression in testing.
#   --mode delete  (default): removes the matching line(s) entirely.
#   --mode nofail           : old behavior, adds ",nofail" to the flags instead of deleting.
#     Only use this if you have confirmed on your own device/GSI pairing that nofail does not
#     regress boot earlier than the unpatched baseline - it has NOT reliably fixed this family
#     of boot failures and should not be assumed safe.
#
# This script never touches any other line or field (so AVB/dm-verity flags, the fs type,
# every other partition's entry - all untouched).
#
# Usage:
#   sudo tools/patch_vendor_fstab.sh <vendor.img> [mount points, default: product] [--mode delete|nofail]
#
# Example:
#   sudo tools/patch_vendor_fstab.sh vendor_a31_lumi.img product
#   sudo tools/patch_vendor_fstab.sh vendor_a31_lumi.img "product system_ext" --mode nofail
#
# Also dumps the vendor's /etc/selinux/plat_sepolicy_vers.txt, vendor_sepolicy_version and
# ro.vndk.version (from build.prop) into vendor-sepolicy-report.txt next to the output image,
# since a sepolicy_version/mapping mismatch (crash-database.md#5, cause #1) can fire on its
# own even after this fstab fix - this just surfaces the numbers, it does not fix that part.

set -e
IMG="$1"
PARTS="${2:-product}"
MODE="delete"
if [ "$3" = "--mode" ] && [ -n "$4" ]; then MODE="$4"; fi
[ -n "$IMG" ] && [ -f "$IMG" ] || { echo "usage: $0 <vendor.img> [mount points, default: product] [--mode delete|nofail]"; exit 1; }
case "$MODE" in delete|nofail) ;; *) echo "invalid --mode '$MODE' (use delete or nofail)"; exit 1;; esac
if [ "$(id -u)" != "0" ]; then echo "needs root (loop mount) - run with sudo"; exit 1; fi
echo "mode: $MODE"

OUT="$(basename "$IMG" .img)-patched.img"
REPORT="$(dirname "$IMG")/vendor-sepolicy-report.txt"
WORK="$(mktemp -d)"
MNT="$WORK/mnt"
mkdir -p "$MNT"

cleanup() { umount "$MNT" 2>/dev/null || true; rmdir "$MNT" 2>/dev/null || true; rm -rf "$WORK"; }
trap cleanup EXIT

cp "$IMG" "$OUT"
# Vendor/GSI ext4 images are frequently built with shared/deduped blocks and almost no free
# space (0 free blocks is common), so even a 1-byte in-place edit needs slack first: grow the
# file, then let resize2fs fill the new space, then unshare any still-shared blocks.
truncate -s "+64M" "$OUT"
resize2fs "$OUT" || true
e2fsck -y -f -E unshare_blocks "$OUT" || e2fsck -y -f "$OUT" || true

mount -o loop,rw "$OUT" "$MNT"

CHANGED=0
for f in "$MNT"/etc/fstab.*; do
  [ -f "$f" ] || continue
  for mp in $PARTS; do
    # Match a line whose second field (mount point) is exactly /<mp>, e.g.:
    #   product /product ext4 ro wait,,avb,logical,first_stage_mount
    line="$(grep -nE "^[[:space:]]*${mp}[[:space:]]+/${mp}[[:space:]]" "$f" || true)"
    [ -z "$line" ] && continue
    lineno="${line%%:*}"
    content="${line#*:}"
    if [ "$MODE" = "delete" ]; then
      sed -i "${lineno}d" "$f"
      echo "$(basename "$f"): $mp -> line deleted"
      CHANGED=$((CHANGED + 1))
    else
      if echo "$content" | grep -q 'nofail'; then
        echo "$(basename "$f"): $mp already nofail - skipped"
        continue
      fi
      # Insert ",nofail" right after the first "wait" token in the flags field, without
      # touching anything else on the line (avb mode, logical, first_stage_mount, etc).
      newcontent="$(echo "$content" | sed -E 's/(wait)/\1,nofail/')"
      sed -i "${lineno}s#.*#${newcontent}#" "$f"
      echo "$(basename "$f"): $mp -> added nofail"
      CHANGED=$((CHANGED + 1))
    fi
  done
done

{
  echo "# sepolicy report for $(basename "$IMG")"
  echo "plat_sepolicy_vers.txt: $(cat "$MNT/etc/selinux/plat_sepolicy_vers.txt" 2>/dev/null || echo 'not found')"
  echo
  echo "vendor_sepolicy_version:"
  cat "$MNT/etc/selinux/vendor_sepolicy_version" 2>/dev/null || echo "not found"
  echo
  grep -E '^ro\.vndk\.version=|^ro\.vendor\.build\.fingerprint=|^ro\.vendor\.build\.security_patch=|^ro\.board\.(first_)?api_level=|^ro\.product\.first_api_level=' \
    "$MNT/build.prop" 2>/dev/null || echo "build.prop props not found"
  echo
  echo "mode: $MODE  (partitions: $PARTS)"
  echo "NOTE: this script only patches the fstab entry/entries above. It does NOT check this"
  echo "version against a GSI's /system/etc/selinux/mapping/*.cil - run"
  echo "tools/check_sepolicy_mapping.py against the target GSI/system image for that"
  echo "(crash-database.md#5, cause #1)."
} > "$REPORT"

umount "$MNT"
trap - EXIT
rmdir "$MNT"
rm -rf "$WORK"

# Shrink back down so the output isn't permanently 64M larger than it needs to be.
e2fsck -y -f "$OUT" || true
resize2fs -M "$OUT" || true

if [ "$CHANGED" -eq 0 ]; then
  echo "no fstab line changed (already nofail, or none of [$PARTS] found) - $OUT is identical to input"
else
  echo "patched $CHANGED fstab line(s) -> $OUT"
fi
echo "sepolicy report -> $REPORT"
