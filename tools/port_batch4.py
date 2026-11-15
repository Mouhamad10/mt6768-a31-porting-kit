#!/usr/bin/env python3
"""Batch 4: targeted 4.14 -> 4.19 API fixes in A31 drivers. Each fix asserts its anchor."""
import re
import sys
from pathlib import Path

F = Path(sys.argv[1])
FIRE_PSY = Path(sys.argv[2]).read_text()  # original 4.19 power_supply.h


def edit(rel, fn):
    p = F / rel
    s = p.read_text(errors="surrogateescape")
    n = fn(s)
    if n != s:
        p.write_text(n, errors="surrogateescape")
        print("fixed", rel)


def add_include(rel, inc, after=None):
    def f(s):
        if inc in s:
            return s
        m = re.search(r"^#include\s+[<\"][^>\"]+[>\"].*$", s, re.M)
        assert m, rel
        return s[:m.end()] + "\n#include " + inc + s[m.end():]
    edit(rel, f)


# power_supply: what the 4.19 core needs on top of the Samsung header
def psy(s):
    if "struct fwnode_handle *fwnode;" not in s:
        s = re.sub(r"(struct power_supply_config \{\n\tstruct device_node \*of_node;\n)",
                   r"\1\tstruct fwnode_handle *fwnode;\n", s, count=1)
        assert "struct fwnode_handle *fwnode;" in s, "power_supply_config anchor"
    if "#define to_power_supply(" not in s:
        m = re.search(r"#define to_power_supply\(.*\n", FIRE_PSY)
        s = s.replace("extern struct class *power_supply_class;", m.group(0) + "\nextern struct class *power_supply_class;", 1)
        assert "#define to_power_supply(" in s
    for en in ["power_supply_typec_mode", "power_supply_typec_src_rp", "power_supply_typec_power_role"]:
        if "enum %s {" % en not in s:
            m = re.search(r"enum %s \{.*?\n\};\n" % en, FIRE_PSY, re.S)
            if m:
                s = s.replace("enum power_supply_type {", m.group(0) + "\nenum power_supply_type {", 1)
    if "power_supply_get_property_from_supplier" not in s:
        m = re.search(r"extern int power_supply_get_property_from_supplier\(.*?\);\n", FIRE_PSY, re.S)
        if m:
            s = s.replace("extern int power_supply_get_property(", m.group(0) + "extern int power_supply_get_property(", 1)
    return s
edit("include/linux/power_supply.h", psy)

# musb: ida_pre_get/ida_get_new/ida_remove are gone
def musb(s):
    s = re.sub(r"\tret = ida_pre_get\(&musb_ida, gfp_mask\);\n\tif \(!ret\) \{\n.*?\n\t\}\n\n\tret = ida_get_new\(&musb_ida, &id\);",
               "\tid = ida_simple_get(&musb_ida, 0, 0, gfp_mask);\n\tret = id;", s, count=1, flags=re.S)
    return s.replace("ida_remove(&musb_ida, id);", "ida_simple_remove(&musb_ida, id);")
edit("drivers/misc/mediatek/usb20/musb_core.c", musb)

# ccci skb timestamps: struct input_event has no .time in the kernel since 4.16
edit("drivers/misc/mediatek/eccci/mixdev/mix_event.c", lambda s: s.replace(
    "\tdo_gettimeofday(&(skb_times_ring.times[index].time));",
    "\t{\n\t\tstruct timeval __tv;\n\n\t\tdo_gettimeofday(&__tv);\n"
    "\t\tskb_times_ring.times[index].input_event_sec = __tv.tv_sec;\n"
    "\t\tskb_times_ring.times[index].input_event_usec = __tv.tv_usec;\n\t}"))

# ccci: mtk_secure_api.h (via modem_secure_base.h) already defines the same SMC IDs
edit("drivers/misc/mediatek/eccci/mt6768/ccci_platform.c",
     lambda s: s.replace("#include <linux/soc/mediatek/mtk_sip_svc.h>\n", "", 1))

# imgsensor sysfs: direct sys_* calls are not callable on arm64 4.19 (syscall wrappers)
def imgs(s):
    s = re.sub(r"\bsys_open\(", "ksys_open(", s)
    s = re.sub(r"\bsys_read\(", "ksys_read(", s)
    s = re.sub(r"\bsys_close\(", "ksys_close(", s)
    s = re.sub(r"\bsys_rmdir\(", "ksys_rmdir(", s)
    s = re.sub(r"\bsys_umask\(([^)]*)\)", r"xchg(&current->fs->umask, (\1) & S_IRWXUGO)", s)
    for inc in ["<linux/syscalls.h>", "<linux/fs_struct.h>", "<linux/sched.h>"]:
        if inc not in s:
            m = re.search(r"^#include\s+[<\"][^>\"]+[>\"].*$", s, re.M)
            s = s[:m.end()] + "\n#include " + inc + s[m.end():]
    return s
edit("drivers/misc/mediatek/imgsensor/src/common/sysfs/imgsensor_sysfs.c", imgs)

add_include("drivers/misc/mediatek/gud/410/MobiCoreDriver/mmu.c", "<linux/suspend.h>")
add_include("fs/crypto/keysetup_v1.c", "<crypto/sha.h>")
for f in ["drivers/misc/mediatek/imgsensor/src/common/v1/imgsensor_hw.c",
          "drivers/misc/mediatek/imgsensor/src/common/v1/imgsensor_i2c.c"]:
    add_include(f, "<linux/pinctrl/consumer.h>")
for f in ["drivers/misc/mediatek/connectivity/common/connectivity_build_in_adapter.c",
          "drivers/misc/mediatek/eccci/mt6768/md_sys1_platform.c"]:
    add_include(f, "<mt-plat/mtk-clkbuf-bridge.h>")
print("batch4 done")
