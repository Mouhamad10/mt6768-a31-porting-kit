# Magisk modules (no kernel change, no vendor flash)

Two modules that fix device behaviour entirely from userspace — they overlay/observe, never touch
the kernel or the vendor partition, and are reversible by disabling the module.

## `a31_touchfix` — touch watchdog (IST4050)

One UI disables the touch input on screen-off and leaves the Imagis IST4050 in a low-power
(singletap/AOD) mode it never leaves, so touch is dead when you wake the phone (fingerprint and
keys still work). The watchdog detects a lit screen with a disabled touch input (or a chip that
stops answering `get_chip_id`) and re-enables it (clears the LP features, power-cycles the chip).

- v3 fix: "screen is lit" is judged by `mWakefulness=Awake`, not only the backlight node (which can
  read 0 while the screen is on in doze), so the repair actually runs.
- Install: copy the folder into `/data/adb/modules/`, reboot. Log: `/data/local/tmp/a31_touchfix.log`.

## `a31_lte_guard` — keep the network up despite the modem LTE hang

Workaround for the MD-WDT modem hang on LTE (see
[`../bring-up/modem-4g-findings.md`](../bring-up/modem-4g-findings.md)). On a modem reset it switches
the SIM to 3G/2G so the connection stays up instead of hanging again on LTE. It **verifies** the
switch actually took effect (the radio silently refuses the change while it restarts, so the module
re-applies until `get-allowed-network-types` confirms it), and re-applies 3G after a reboot (the
system puts LTE back on boot).

Controls (create the file to use):

| File | Effect |
|---|---|
| `/data/local/tmp/lte_guard.stay3g` | **permanent 3G+** — never retry LTE |
| `/data/local/tmp/lte_guard.off` | pause the module, restore LTE |
| `/data/local/tmp/lte_guard.lte_now` | try LTE right now |

Without `stay3g`, it retries LTE on a back-off (30 min → 1 h → 2 h → 4 h) **only while the screen is
off**, so a retry never interrupts you; if LTE then stays up 30 min the back-off resets. Log:
`/data/local/tmp/a31_lte_guard.log`.

> These are workarounds for a stock-firmware modem bug, not a fix. The root cause is inside the
> modem firmware and is still open.

## Packaging

Each folder is a standard Magisk module (`module.prop` + `service.sh`). Zip the folder contents and
flash in the Magisk app, or copy the folder into `/data/adb/modules/` as root and reboot.
