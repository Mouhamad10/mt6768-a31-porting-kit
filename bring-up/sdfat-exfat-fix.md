# exFAT SD card won't mount on 4.14 (sdfat `time_offset`) — 1-byte kernel fix

## Symptom

An exFAT microSD shows as **"unmountable"** in One UI. Kernel log:

```
[SDFAT](mmcblk1p1): set fs-type by option : exfat
[SDFAT](mmcblk1p1): unrecognized mount option "time_offset=120" or missing value
[SDFAT](mmcblk1p1): failed to parse options
[SDFAT](mmcblk1p1): failed to mount! (-22)
```

## Cause

The One UI (newer-Android) `vold` mounts exFAT with a `time_offset=<minutes>` option (the local UTC
offset). The Samsung **sdfat 2.5.2a** in the 4.14 kernel has no `time_offset` token in its option
table (`fs/sdfat/sdfat.c`, `sdfat_tokens`), so the whole mount fails with `-EINVAL`.

Internal (`vfat`) volumes are unaffected because fs/fat has its own table that already knows
`time_offset`. Only sdfat (used for the external card) chokes.

## Fix — repoint an unused token to the existing `time_offset=%d` string

The cleanest change is a **source** one: add a `time_offset=%d` token to `sdfat_tokens` whose handler
ignores the value (sdfat derives timestamps itself). But because the running daily kernel was
already built, this was done as a **1-byte binary patch of the gzipped Image** so nothing else
changed (ramdisk, dtb, cmdline and the Magisk ramdisk stayed byte-identical):

- In sdfat's option table, repoint the `const char*` of the **`Opt_defrag` entry** (`"defrag"`, a
  no-op when `CONFIG_SDFAT_DFR` is off — nobody passes it) to the existing `"time_offset=%d"`
  string already present in the Image for fs/fat.
- Net effect: sdfat now accepts `time_offset=<any int>` (routed to the no-op defrag handler) and the
  exFAT card mounts. No other filesystem is affected.

### Why not the `tz=UTC` or `allow_utime` slot

- `allow_utime=%o` uses `match_octal`, which **cannot** parse e.g. `time_offset=180` (the `8` is not
  an octal digit) — it works in winter (UTC+2 → 120) and breaks in summer (UTC+3 → 180). Rejected.
- `tz=UTC` (`Opt_tz_utc`) parses any int but sets `tz_utc=1`, which changes how exFAT timestamps
  without a stored UTC offset are read (a cosmetic metadata shift). Acceptable but has a side effect.
- `Opt_defrag` is a pure no-op when `CONFIG_SDFAT_DFR` is off → **zero side effects**. Chosen.

### Verifying the repacked boot image

Only 1 byte of the decompressed kernel differs; ramdisk/dtb/cmdline md5 identical; the Android boot
header differs only in `kernel_size` and the `id` SHA1 field. Flash to `boot` from rooted Android
(`dd`), keep the original `boot` as rollback. Result: card mounts (`SDFAT: mounted successfully!`),
`/data` and Magisk unaffected.

## On 5.10 / 6.6

Newer `sdfat`/`exfat` already supports `time_offset`; this bug does not exist there. This is a
4.14-only patch.
