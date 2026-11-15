# Modem / 4G investigation (MD WDT on LTE)

A separate problem from the kernel port, documented here because the diagnostic method is reusable
for any MT6768 modem issue, and because it ends in a Magisk workaround (see
[`../magisk/`](../magisk/)). **This is on the stock 4.14 kernel**, not a port artifact.

## Symptom

Mobile data drops and returns every ~2–3 minutes on LTE. Kernel log at each drop:

```
[ccci1/mcd] MD WDT IRQ
[ccci1/fsm] reset MD after WDT
... modem power off/on ...
```
Userspace: `ccci_mdinit: (1):md status event 12`, `RILD: DoHandleModemReset()`. It is a
**modem-side firmware watchdog** (the modem firmware hangs), not an AP/userspace crash.

## What it is NOT (ruled out with evidence)

| Hypothesis | Test | Result |
|---|---|---|
| LTE-only mode (set via Phone-info) | restore auto GSM/WCDMA/LTE | resets continued |
| Data load (gaming, downloads) | correlate `ccmni` throughput vs resets | reset fired at <1 KB/s |
| Weak signal | log RSRP/RSRQ at reset | RSRP ~−100 steady, unchanged at reset |
| IMS / VoLTE | disable at RIL **and** stop vendor `imsd` + Samsung IMS apps | resets continued |
| Fast dormancy | zero `persist.vendor.radio.fd.*`, reboot | resets continued |
| Modem firmware / NV corruption | md5 `md1img` vs stock CP; diff `nvdata` vs a July backup | all match / no corruption |
| boot / recovery / vendor partitions | md5 vs stock firmware | match (only `boot`/`recovery`/`vbmeta` differ, as expected for a custom ROM) |
| Location | test in a different area | resets continued |
| SIM / network | SIM works fine on other phones | hardware-/firmware-side, device-specific |

**Key observation:** the modem is fine on **3G** (hours stable) and hangs only once an **LTE data
session (PDN)** is up — independent of how much traffic flows. Firmware is byte-identical to stock.

## Diagnostic method (reusable)

- `grep` kernel log for `MD WDT IRQ`; `logcat` for `md status event 12` / `DoHandleModemReset`.
- Per-second `/proc/net/dev` on `ccmni*`/`rmnet*` to correlate throughput with reset time.
- `dumpsys telephony.registry` for serving cell (PCI/EARFCN/band) + RSRP/RSRQ at each reset.
- Compare NV against a backup: tar `/mnt/vendor/{nvdata,nvcfg,efs,protect_f,protect_s}`, decode
  `nvdata/AllMap` (140-byte records: path at +64, offset/size at +52) against `AllFile`.
- Compare every firmware partition to the stock Odin package (`BL_/AP_/CP_` tars, lz4-decompress,
  md5 vs `dd` of each `by-name` partition).

## Workaround (Magisk, no kernel change)

Since the hang is inside stock modem firmware and no setting prevents it, the practical fix is to
**keep the SIM on 3G/2G** so LTE's hanging path is never entered. The `a31_lte_guard` module watches
for the modem reset and switches the allowed network types to 3G/2G (verifying the switch actually
applied — the radio silently refuses the change while it restarts). It can retry LTE later only
while the screen is off, or stay on 3G+ permanently. See [`../magisk/`](../magisk/).

The real fix would require modem firmware debugging (the MD exception/EE dump), which the stock ROM
does not expose. Left open.
