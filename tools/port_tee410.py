#!/usr/bin/env python3
"""Trustonic TEE 410 for A31 on the 4.19 tree.
Keeps the fire 4.19 MobiCoreDriver (already adapted to 4.19 mm APIs) and adds the
A31 gfp_allowed_mask serialisation (no CMA pages pinned for the TEE), the A31 TUI
HAL for mt6768 and the Kconfig dependency fix. Wires gud/ into misc/mediatek."""
import shutil
import sys
from pathlib import Path

A, F = Path(sys.argv[1]), Path(sys.argv[2])
g_a = A / "drivers/misc/mediatek/gud"
g_f = F / "drivers/misc/mediatek/gud"

# 1) mmu.c gfp mask serialisation
mmu = g_f / "410/MobiCoreDriver/mmu.c"
s = mmu.read_text()
GFP_BLOCK = '''
static gfp_t tee_cma_saved_gfp_mask;
static DEFINE_MUTEX(gfp_mutex);     /* Lock for gfp_allowed_mask */

void tee_cma_restore_gfp_mask(void)
{
#ifdef CONFIG_PM_SLEEP
	WARN_ON(!mutex_is_locked(&pm_mutex));
#endif
	if (tee_cma_saved_gfp_mask)  {
		gfp_allowed_mask = tee_cma_saved_gfp_mask;
		tee_cma_saved_gfp_mask = 0;
	}
	mutex_unlock(&gfp_mutex);
}

void tee_cma_restrict_gfp_mask(void)
{
#ifdef CONFIG_PM_SLEEP
	WARN_ON(!mutex_is_locked(&pm_mutex));
#endif
	WARN_ON(tee_cma_saved_gfp_mask);
	mutex_lock(&gfp_mutex);
	tee_cma_saved_gfp_mask = gfp_allowed_mask;
	gfp_allowed_mask &= ~__GFP_CMA;
}
'''
if "tee_cma_restrict_gfp_mask" not in s:
    anchor = "#define MMU_ION_BUF\t\tBIT(24)\n"
    assert anchor in s, "anchor MMU_ION_BUF missing"
    s = s.replace(anchor, anchor + GFP_BLOCK, 1)
    old = "\t\tret = gup_local(mm, start, nr_pages, write, pages);\n"
    assert s.count(old) == 1, "gup_local call site not unique"
    s = s.replace(old, "\t\ttee_cma_restrict_gfp_mask();\n" + old + "\n\t\ttee_cma_restore_gfp_mask();\n", 1)
    mmu.write_text(s)
    print("mmu.c: gfp mask serialisation added")

# 2) A31-only TUI HAL files + Kconfig fix
for rel in ["410/TlcTui/tui-hal_mt.h", "410/TlcTui/tui-hal_mt6768.c", "500/TlcTui/tui-hal_mt6768.c"]:
    if not (g_f / rel).exists():
        shutil.copy2(g_a / rel, g_f / rel)
        print("copied", rel)
k = g_f / "410/Kconfig"
ks = k.read_text()
if "depends on TRUSTONIC_TEE\n" in ks:
    k.write_text(ks.replace("depends on TRUSTONIC_TEE\n", "depends on TRUSTONIC_TEE_SUPPORT\n"))
    print("410/Kconfig: TUI dependency fixed")

# 3) wire gud/ into drivers/misc/mediatek
mk = F / "drivers/misc/mediatek/Kconfig"
s = mk.read_text()
line = 'source "drivers/misc/mediatek/gud/Kconfig"'
if line not in s:
    idx = s.rfind("endmenu")
    s = s[:idx] + "# --- A31 port: Trustonic TEE 410 ---\n" + line + "\n\n" + s[idx:] if idx >= 0 else s + "\n" + line + "\n"
    mk.write_text(s)
    print("misc/mediatek/Kconfig: gud sourced")
mm = F / "drivers/misc/mediatek/Makefile"
s = mm.read_text()
line = "obj-$(CONFIG_TRUSTONIC_TEE_SUPPORT) += gud/"
if line not in s:
    mm.write_text(s.rstrip("\n") + "\n\n# --- A31 port: Trustonic TEE 410 ---\n" + line + "\n")
    print("misc/mediatek/Makefile: gud added")
