#!/bin/bash
# Samsung USB gadget (android0 composite, DM, conn_gadget, ss_mon) on the 4.19 tree.
set -e
T=$(cd "$(dirname "$0")" && pwd); A="$1"; F="$2"
G=drivers/usb/gadget
export MERGE3_SYMS="CONFIG_USB_ANDROID_SAMSUNG_COMPOSITE CONFIG_USB_CONFIGFS_F_DM CONFIG_USB_CONFIGFS_F_CONN_GADGET CONFIG_USB_CONFIGFS_F_SS_MON_GADGET CONFIG_USB_F_CONN_GADGET CONFIG_USB_F_SS_MON_GADGET CONFIG_USB_NOTIFY_LAYER CONFIG_USB_HOST_NOTIFY CONFIG_USB_NOTIFY_PROC_LOG"
for f in configfs.c function/f_acm.c function/f_accessory.c; do
  python3 -I "$T/merge3.py" "$F/$G/$f" "$A/$G/$f" || true
done
for f in function/f_dm.c function/f_conn_gadget.c function/f_ss_mon_gadget.c; do
  [ -e "$F/$G/$f" ] || cp -p "$A/$G/$f" "$F/$G/$f"
done
# headers the functions use (only if missing)
for h in $(grep -hoE '#include "[^"]+"' "$A/$G/function/f_dm.c" "$A/$G/function/f_conn_gadget.c" "$A/$G/function/f_ss_mon_gadget.c" | cut -d'"' -f2 | sort -u); do
  [ -e "$A/$G/function/$h" ] && [ ! -e "$F/$G/function/$h" ] && cp -p "$A/$G/function/$h" "$F/$G/function/$h" && echo "hdr $h"
done
python3 -I - "$A" "$F" <<'EOF'
import re, sys
from pathlib import Path
A, F = Path(sys.argv[1]), Path(sys.argv[2])
G = "drivers/usb/gadget"
def block(txt, sym):
    m = re.search(r"^(menu)?config %s\n(?:(?:[ \t].*|)\n)*" % sym, txt, re.M)
    return m.group(0).rstrip() + "\n" if m else None
ka = (A / G / "Kconfig").read_text(); kp = F / G / "Kconfig"; kf = kp.read_text()
add = []
for sym in ["USB_F_CONN_GADGET", "USB_F_SS_MON_GADGET", "USB_F_DM", "USB_CONFIGFS_F_DM",
            "USB_CONFIGFS_F_CONN_GADGET", "USB_CONFIGFS_F_SS_MON_GADGET", "USB_ANDROID_SAMSUNG_COMPOSITE"]:
    if re.search(r"^(menu)?config %s$" % sym, kf, re.M):
        continue
    b = block(ka, sym)
    if b: add.append(b)
if add:
    i = kf.rfind('source "drivers/usb/gadget/legacy/Kconfig"')
    blk = "# --- A31 port: Samsung gadget functions ---\n" + "\n".join(add) + "\n"
    kf = kf[:i] + blk + kf[i:] if i >= 0 else kf + blk
    kp.write_text(kf); print("gadget Kconfig +%d" % len(add))
mp = F / G / "function/Makefile"; mf = mp.read_text()
lines = ["usb_f_dm-y\t\t\t:= f_dm.o", "obj-$(CONFIG_USB_CONFIGFS_F_DM)\t+= usb_f_dm.o",
         "usb_f_conn_gadget-y             := f_conn_gadget.o", "obj-$(CONFIG_USB_F_CONN_GADGET) += usb_f_conn_gadget.o",
         "usb_f_ss_mon_gadget-y             := f_ss_mon_gadget.o", "obj-$(CONFIG_USB_F_SS_MON_GADGET) += usb_f_ss_mon_gadget.o"]
new = [l for l in lines if l.split()[0] not in mf]
if new:
    mp.write_text(mf.rstrip("\n") + "\n\n# --- A31 port: Samsung gadget functions ---\n" + "\n".join(new) + "\n"); print("gadget Makefile +%d" % len(new))
EOF
echo "usb gadget done"
