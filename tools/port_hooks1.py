#!/usr/bin/env python3
"""Batch 1 hooks: wire Samsung A31 drivers into the fire 4.19 tree's Kconfig/Makefiles.
Idempotent: every line/block is added only if not already present."""
import re
import sys
from pathlib import Path

A = Path(sys.argv[1])  # A31 source
F = Path(sys.argv[2])  # fire tree


def read(p):
    return p.read_text(encoding="utf-8", errors="surrogateescape")


def write(p, s):
    p.write_text(s, encoding="utf-8", errors="surrogateescape")


def add_before_last_endmenu(path, lines, tag):
    s = read(path)
    new = [l for l in lines if l not in s]
    if not new:
        return
    block = "\n# --- A31 port: %s ---\n" % tag + "\n".join(new) + "\n"
    idx = s.rfind("endmenu")
    s = s[:idx] + block + "\n" + s[idx:] if idx >= 0 else s + block
    write(path, s)
    print("kconfig  %-40s +%d" % (path.relative_to(F), len(new)))


def append_lines(path, lines, tag):
    s = read(path)
    new = [l for l in lines if l not in s]
    if not new:
        return
    if not s.endswith("\n"):
        s += "\n"
    s += "\n# --- A31 port: %s ---\n" % tag + "\n".join(new) + "\n"
    write(path, s)
    print("makefile %-40s +%d" % (path.relative_to(F), len(new)))


BLOCK_END = re.compile(r"^(config|menuconfig|menu|endmenu|choice|endchoice|if|endif|source|comment)\b")


def extract_block(kconfig, sym):
    lines = read(kconfig).splitlines()
    out, grab = [], False
    for l in lines:
        if re.match(r"^\s*(menu)?config\s+%s\s*$" % re.escape(sym), l):
            grab = True
            out = [l.strip() and l.lstrip() if not l.startswith("\t") else l]
            out = ["config %s" % sym]
            continue
        if grab:
            if BLOCK_END.match(l.strip()) and not l.startswith(("\t", " ")):
                break
            if re.match(r"^\s*(config|menuconfig)\s+\w+", l):
                break
            out.append(l)
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out) if out else None


def add_kconfig_symbols(target_rel, src_rel, syms, tag):
    tgt = F / target_rel
    s = read(tgt)
    blocks = []
    for sym in syms:
        if re.search(r"^\s*(menu)?config\s+%s\s*$" % sym, s, re.M):
            continue
        b = extract_block(A / src_rel, sym)
        if b:
            blocks.append(b)
        else:
            print("WARN: block %s not found in %s" % (sym, src_rel))
    if not blocks:
        return
    block = "\n# --- A31 port: %s ---\n" % tag + "\n\n".join(blocks) + "\n"
    idx = s.rfind("endmenu")
    s = s[:idx] + block + "\n" + s[idx:] if idx >= 0 else s + block
    write(tgt, s)
    print("symbols  %-40s +%d" % (target_rel, len(blocks)))


# ---- drivers/Kconfig ----
drv_k = [
    'source "drivers/switch/Kconfig"',
    'source "drivers/samsung/Kconfig"',
    'source "drivers/sensors/Kconfig"',
    'source "drivers/spu_verify/Kconfig"',
    'source "drivers/regulator/pmic_class/Kconfig"',
    'source "drivers/security/samsung/icdrv/Kconfig"',
    'source "drivers/usb/typec/slsi/common/Kconfig"',
    'source "drivers/vibrator/common/Kconfig"',
    'source "drivers/security/samsung/five_tee_driver/Kconfig"',
    'source "drivers/sti/abc/Kconfig"',
    'source "drivers/sti/common/Kconfig"',
    'source "drivers/security/samsung/tzic/Kconfig"',
    'source "drivers/muic/common/Kconfig"',
    'source "drivers/fingerprint/Kconfig"',
    'source "drivers/usb/typec/slsi/s2mu106/Kconfig"',
    'source "drivers/usb/typec/manager/Kconfig"',
    'source "drivers/usb/typec/common/Kconfig"',
    'source "drivers/mfd/slsi/s2mu106/Kconfig"',
    'source "drivers/hwmon/sec_thermistor/Kconfig"',
    'source "drivers/vibrator/slsi/s2mu106/Kconfig"',
    'source "drivers/regulator/s2mpb03/Kconfig"',
    'source "drivers/muic/slsi/s2mu106/Kconfig"',
    'source "drivers/battery/fuelgauge/s2mu106_fuelgauge/Kconfig"',
    'source "drivers/battery/charger/s2mu106_charger/Kconfig"',
    'source "drivers/battery/common/Kconfig"',
]
drv_k = [l for l in drv_k if (F / l.split('"')[1]).exists()]
add_before_last_endmenu(F / "drivers/Kconfig", drv_k, "Samsung drivers")

drv_m = [
    "obj-$(CONFIG_SEC_EXT)\t+= samsung/",
    "obj-$(CONFIG_SWITCH)\t\t+= switch/",
    "obj-$(CONFIG_SENSORS)\t\t+= sensors/",
    "obj-$(CONFIG_SPU_VERIFY)\t+= spu_verify/",
    "obj-y += regulator/pmic_class/",
    "obj-y += security/samsung/icdrv/",
    "obj-y += usb/typec/slsi/common/",
    "obj-y += vibrator/common/",
    "obj-y += security/samsung/five_tee_driver/",
    "obj-y += sti/abc/",
    "obj-y += sti/common/",
    "obj-y += security/samsung/tzic/",
    "obj-y += muic/common/",
    "obj-y += fingerprint/",
    "obj-y += usb/typec/slsi/s2mu106/",
    "obj-y += usb/typec/manager/",
    "obj-y += usb/typec/common/",
    "obj-y += mfd/slsi/s2mu106/",
    "obj-y += hwmon/sec_thermistor/",
    "obj-y += vibrator/slsi/s2mu106/",
    "obj-y += regulator/s2mpb03/",
    "obj-y += muic/slsi/s2mu106/",
    "obj-y += battery/fuelgauge/s2mu106_fuelgauge/",
    "obj-y += battery/charger/s2mu106_charger/",
    "obj-y += battery/common/",
]
drv_m = [l for l in drv_m if (F / "drivers" / l.split("+=")[1].strip()).exists()]
append_lines(F / "drivers/Makefile", drv_m, "Samsung drivers")

# ---- usb notify ----
add_before_last_endmenu(F / "drivers/usb/Kconfig", ['source "drivers/usb/notify/Kconfig"'], "usb_notify") \
    if "endmenu" in read(F / "drivers/usb/Kconfig") else append_lines(F / "drivers/usb/Kconfig", ['source "drivers/usb/notify/Kconfig"'], "usb_notify")
append_lines(F / "drivers/usb/Makefile", ["obj-$(CONFIG_USB_NOTIFY_LAYER)\t+= notify/"], "usb_notify")

# ---- touchscreen ----
add_before_last_endmenu(F / "drivers/input/touchscreen/Kconfig", ['source "drivers/input/touchscreen/imagis/ist4050/Kconfig"'], "IST4050")
append_lines(F / "drivers/input/touchscreen/Makefile", ["obj-$(CONFIG_TOUCHSCREEN_IST4050)\t+= imagis/ist4050/"], "IST4050")
add_kconfig_symbols("drivers/input/Kconfig", "drivers/input/Kconfig",
                    ["INPUT_TOUCHSCREEN_TCLMV2", "SEC_DEBUG_TSP_LOG"], "sec_cmd/tclm")
append_lines(F / "drivers/input/Makefile", [
    "obj-$(CONFIG_INPUT_TOUCHSCREEN)\t+= sec_cmd.o",
    "obj-$(CONFIG_SEC_DEBUG_TSP_LOG) += sec_tsp_log.o",
    "obj-$(CONFIG_INPUT_TOUCHSCREEN_TCLMV2)\t+= sec_tclm_v2.o",
], "sec_cmd/tclm")

# ---- MFD S2MU106 symbol (defined in drivers/mfd/Kconfig on A31) ----
add_kconfig_symbols("drivers/mfd/Kconfig", "drivers/mfd/Kconfig", ["MFD_S2MU106"], "S2MU106 MFD")

# ---- NFC ----
add_kconfig_symbols("drivers/nfc/Kconfig", "drivers/nfc/Kconfig", ["SEC_NFC"], "sec_nfc")
append_lines(F / "drivers/nfc/Makefile", ["obj-$(CONFIG_SEC_NFC)\t\t\t+= sec_nfc.o"], "sec_nfc")

# ---- SMA1303 amp ----
add_kconfig_symbols("sound/soc/codecs/Kconfig", "sound/soc/codecs/Kconfig", ["SND_SOC_SMA1303"], "sma1303")
append_lines(F / "sound/soc/codecs/Makefile", [
    "snd-soc-sma1303-objs := sma1303.o",
    "obj-$(CONFIG_SND_SOC_SMA1303)\t+= snd-soc-sma1303.o",
], "sma1303")

# ---- security ----
add_kconfig_symbols("security/Kconfig", "security/Kconfig", ["SDP", "SDP_KEY_DUMP"], "SDP")
sec_k = [
    'source "security/samsung/defex_lsm/Kconfig"',
    'source "security/samsung/proca/Kconfig"',
    'source "security/samsung/proca/gaf/Kconfig"',
    'source "security/samsung/dsms/Kconfig"',
    'source "security/samsung/five/Kconfig"',
]
sec_k = [l for l in sec_k if (F / l.split('"')[1]).exists()]
add_before_last_endmenu(F / "security/Kconfig", sec_k, "Samsung security")
append_lines(F / "security/Makefile", [
    "obj-$(CONFIG_SDP) += sdp/",
    "obj-y += samsung/defex_lsm/",
    "obj-y += samsung/proca/",
    "obj-y += samsung/proca/gaf/",
    "obj-y += samsung/dsms/",
    "obj-y += samsung/five/",
], "Samsung security")

# ---- sdfat ----
fk = F / "fs/Kconfig"
s = read(fk)
if 'source "fs/sdfat/Kconfig"' not in s:
    s = s.replace('source "fs/fat/Kconfig"', 'source "fs/fat/Kconfig"\nsource "fs/sdfat/Kconfig"', 1)
    write(fk, s)
    print("kconfig  fs/Kconfig +1")
append_lines(F / "fs/Makefile", ["obj-$(CONFIG_SDFAT_FS)\t\t+= sdfat/"], "sdfat")
print("done")
