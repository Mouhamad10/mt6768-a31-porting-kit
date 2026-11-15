#!/usr/bin/env python3
"""port_pmqos.py <kernel_tree> <dir>...
4.14 MTK drivers used pm_qos_* with MTK classes (PM_QOS_DDR_OPP, ...) that lived in
linux/pm_qos.h. On the 4.19 MTK tree those classes belong to the separate mtk_pm_qos
framework that dvfsrc listens to. Converts every file that uses an MTK class:
  struct pm_qos_request -> struct mtk_pm_qos_request, pm_qos_*() -> mtk_pm_qos_*(),
  MTK class/default names -> MTK_PM_QOS_* ; adds <linux/soc/mediatek/mtk-pm-qos.h>.
Files that also use generic classes (CPU_DMA_LATENCY, NETWORK_*) are only reported."""
import re
import sys
from pathlib import Path

K = Path(sys.argv[1])
hdr = (K / "include/linux/soc/mediatek/mtk-pm-qos.h").read_text()
have_timeout = "mtk_pm_qos_update_request_timeout" in hdr

CLASS_MAP = {
    "PM_QOS_DDR_OPP": "MTK_PM_QOS_DDR_OPP",
    "PM_QOS_VCORE_OPP": "MTK_PM_QOS_VCORE_OPP",
    "PM_QOS_SCP_VCORE_REQUEST": "MTK_PM_QOS_SCP_VCORE_REQUEST",
    "PM_QOS_EMI_OPP": "MTK_PM_QOS_DDR_OPP",          # EMI clock == DDR on mt6768
    "PM_QOS_MEMORY_BANDWIDTH": "MTK_PM_QOS_MEMORY_BANDWIDTH",
    "PM_QOS_HRT_BANDWIDTH": "MTK_PM_QOS_HRT_BANDWIDTH",
    "PM_QOS_VVPU_OPP": "MTK_PM_QOS_VVPU_OPP",
    "PM_QOS_VMDLA_OPP": "MTK_PM_QOS_VMDLA_OPP",
    "PM_QOS_CPU_MEMORY_BANDWIDTH": "MTK_PM_QOS_CPU_MEMORY_BANDWIDTH",
    "PM_QOS_GPU_MEMORY_BANDWIDTH": "MTK_PM_QOS_GPU_MEMORY_BANDWIDTH",
    "PM_QOS_OTHER_MEMORY_BANDWIDTH": "MTK_PM_QOS_OTHER_MEMORY_BANDWIDTH",
    "PM_QOS_VCORE_DVFS_FORCE_OPP": "MTK_PM_QOS_VCORE_DVFS_FORCE_OPP",
}
# names already valid as-is in mtk-pm-qos.h
KEEP = ["PM_QOS_DISP_FREQ", "PM_QOS_MDP_FREQ", "PM_QOS_VDEC_FREQ", "PM_QOS_VENC_FREQ", "PM_QOS_IMG_FREQ",
        "PM_QOS_CAM_FREQ", "PM_QOS_DPE_FREQ", "PM_QOS_MM0_BANDWIDTH_LIMITER", "PM_QOS_MM1_BANDWIDTH_LIMITER",
        "PM_QOS_MM_MEMORY_BANDWIDTH", "PM_QOS_ISP_HRT_BANDWIDTH", "PM_QOS_APU_MEMORY_BANDWIDTH"]
MTK_NAMES = list(CLASS_MAP) + KEEP
mtk_rx = re.compile(r"\b(%s)(_DEFAULT_VALUE)?\b" % "|".join(sorted(MTK_NAMES, key=len, reverse=True)))
generic_rx = re.compile(r"\bPM_QOS_(CPU_DMA_LATENCY|NETWORK_LATENCY|NETWORK_THROUGHPUT|CLUSTER\d|C\d_|DEVFREQ)")

changed, skipped = 0, []
for d in sys.argv[2:]:
    for p in sorted(Path(d).rglob("*.[ch]")):
        s = p.read_text(errors="surrogateescape")
        if "mtk_pm_qos" in s and not mtk_rx.search(re.sub(r"MTK_PM_QOS_\w+", "", s)):
            continue
        if not mtk_rx.search(s):
            continue
        if generic_rx.search(s):
            skipped.append(str(p))
            continue
        o = s
        s = re.sub(r"\bstruct\s+pm_qos_request\b", "struct mtk_pm_qos_request", s)
        s = re.sub(r"(?<!mtk_)\bpm_qos_(add_request|update_request|remove_request|request_active|"
                   r"update_request_timeout|add_notifier|remove_notifier)\s*\(", r"mtk_pm_qos_\1(", s)
        s = re.sub(r"(?<!mtk_)\bpm_qos_request\s*\(", "mtk_pm_qos_request(", s)

        def cls(m):
            name, dflt = m.group(1), m.group(2) or ""
            if name in CLASS_MAP:
                tgt = CLASS_MAP[name]
                return tgt + dflt if not (name == "PM_QOS_EMI_OPP" and dflt) else "MTK_PM_QOS_DDR_OPP_DEFAULT_VALUE"
            return name + dflt
        s = re.sub(r"(?<![A-Z_])" + mtk_rx.pattern, cls, s)
        if "linux/soc/mediatek/mtk-pm-qos.h" not in s:
            s = re.sub(r"^(#include\s+[<\"][^>\"]+[>\"].*)$", r"\1\n#include <linux/soc/mediatek/mtk-pm-qos.h>", s, count=1, flags=re.M)
        if s != o:
            p.write_text(s, errors="surrogateescape")
            changed += 1
            print("converted", p)
print("files converted:", changed, "| mtk_pm_qos_update_request_timeout available:", have_timeout)
for f in skipped:
    print("SKIPPED (also uses generic pm_qos classes):", f)
