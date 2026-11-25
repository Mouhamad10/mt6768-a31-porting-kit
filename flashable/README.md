# TWRP-flashable vendor fstab patch

Disables the stale `product` fstab entry directly on an **already-flashed** `/vendor`,
from TWRP, without re-flashing the whole vendor image. Companion to
[`tools/patch_vendor_fstab.sh`](../tools/patch_vendor_fstab.sh) (which patches a vendor
**image file** before flashing) - use whichever fits your workflow; both produce the same
end result. See [`bring-up/crash-database.md#5`](../bring-up/crash-database.md) for the
root cause this fixes.

## Build

```
cd flashable
zip -r -X patch-vendor-fstab-twrp.zip META-INF
```

## Flash

TWRP -> Install -> pick the zip -> swipe to confirm. Read the `ui_print` output - it tells
you per-file whether it patched, found nothing to do, or failed (and does **not** claim
success on a failure, see below). Safe to flash more than once (it detects an
already-disabled line and skips it).

## Why this isn't a simple `sed -i` one-liner

Confirmed by testing against the actual vendor image this kit targets
(`vendor_a31_lumi.img`, see crash-database.md#5): the live filesystem reports **0 bytes
truly available** for new writes (`stat -f` shows `Available: 0` even though the raw
free-block count is nonzero - some ext4 images are packed this tight). That breaks every
technique that needs to allocate even one new block while editing:

- `sed -i` (temp file + rename) - fails outright.
- "filter out the line, then overwrite the original file with the shorter result" - still
  fails, because truncating then rewriting still needs a fresh block allocation for the
  write in practice on this filesystem, even though the net result is smaller.

The only thing that reliably works at 0 available space: overwrite **existing** bytes with
a **same-length** replacement and never truncate. `update-binary` finds the byte offset of
the matching fstab line and `dd`s a single `#` over its first character
(`conv=notrunc`), turning it into a comment - zero size change, so no new block is ever
needed. Android's fstab parser skips `#`-prefixed lines, so this behaves exactly like
deleting the line for boot purposes, while leaving the rest of the original text
physically on disk if you ever want to restore it by hand (look for the line starting
`#roduct` - or whatever partition name you targeted, missing its first letter).

## Why not `nofail` instead of disabling the line

See the "nofail regression" note in crash-database.md#5: on this same device/GSI pairing,
keeping the line (just marked optional) was observed to make boot fail *earlier* than the
original unpatched baseline. Not fully explained, but reproducible enough that this zip
does not offer a `nofail` mode.

## Customizing

Edit `PARTS="product"` near the top of `META-INF/com/google/android/update-binary` to a
space-separated list if you've removed other partitions too (e.g. `PARTS="product
system_ext"`), then rebuild the zip.
