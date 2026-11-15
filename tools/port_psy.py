#!/usr/bin/env python3
"""power_supply for A31 on 4.19: Samsung A31 header + sysfs (battery stack / healthd ABI),
plus the mainline-4.19 USB_TYPE property the 4.19 power_supply core relies on."""
import re
import sys
from pathlib import Path

A, F = Path(sys.argv[1]), Path(sys.argv[2])
hdr_a = (A / "include/linux/power_supply.h").read_text()
hdr_f = (F / "include/linux/power_supply.h").read_text()

h = hdr_a
# 1) USB_TYPE property right after PROP_TYPE (same slot as mainline 4.19)
anchor = "\tPOWER_SUPPLY_PROP_TYPE, /* use power_supply.type instead */\n"
assert anchor in h
if "POWER_SUPPLY_PROP_USB_TYPE," not in h:
    h = h.replace(anchor, anchor + "\tPOWER_SUPPLY_PROP_USB_TYPE,\n", 1)

# 2) enum power_supply_usb_type from the 4.19 header
m = re.search(r"enum power_supply_usb_type \{.*?\};\n", hdr_f, re.S)
assert m
if "enum power_supply_usb_type {" not in h:
    h = h.replace("enum power_supply_type {", m.group(0) + "\nenum power_supply_type {", 1)

# 3) usb_types in power_supply_desc
desc = re.search(r"struct power_supply_desc \{.*?\n\};", h, re.S)
assert desc
if "usb_types" not in desc.group(0):
    d = desc.group(0).replace("\tenum power_supply_type type;\n",
                              "\tenum power_supply_type type;\n"
                              "\tconst enum power_supply_usb_type *usb_types;\n"
                              "\tsize_t num_usb_types;\n", 1)
    assert d != desc.group(0), "type field not found in power_supply_desc"
    h = h.replace(desc.group(0), d, 1)
(F / "include/linux/power_supply.h").write_text(h)
print("power_supply.h: A31 header + USB_TYPE")

# sysfs: A31 attribute table + usb_type at the matching position
s = (A / "drivers/power/supply/power_supply_sysfs.c").read_text()
if "POWER_SUPPLY_ATTR(usb_type)" not in s:
    s2 = re.sub(r"(\n(\s*)POWER_SUPPLY_ATTR\(type\),\n)", r"\1\2POWER_SUPPLY_ATTR(usb_type),\n", s, count=1)
    assert s2 != s, "POWER_SUPPLY_ATTR(type) not found"
    s = s2
(F / "drivers/power/supply/power_supply_sysfs.c").write_text(s)
print("power_supply_sysfs.c: A31 + usb_type attr")
