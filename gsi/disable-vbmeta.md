# Disabling vbmeta verification (A31)

A GSI replaces `system`, which breaks AVB (Android Verified Boot) chain verification, so vbmeta
must be flashed with verification disabled or the device won't boot.

## Easiest (fastboot)

```sh
fastboot --disable-verity --disable-verification flash vbmeta vbmeta.img
```

Use the **stock A31 `vbmeta.img`** (from the `A315FXXS5DXB1` firmware, AP tar) - the flags above
disable its enforcement; you do not need a modified image.

## Samsung note

On Samsung you often flash vbmeta via **Odin** (AP slot, in a `.tar`) rather than fastboot, because
the bootloader is locked to Odin for some partitions. If `fastboot flash vbmeta` is rejected:

1. Put the stock `vbmeta.img` (verification already patched, or empty vbmeta) into a `.tar`.
2. Flash it in Odin's **AP** slot together with the normal unlock flow.

Keep a copy of the **stock vbmeta** so you can restore AVB if you go back to the stock ROM.
