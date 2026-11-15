#!/bin/bash
# Batch 6: A31 platform drivers the A31 dtb/LK expect (watchdog toprgu, ram_console,
# boot mode, boot reason, chip, ccmni), and link-level cleanups.
set -e
T=$(cd "$(dirname "$0")" && pwd); A="$1"; F="$2"; REF="$T/ref_fire"
rep() {
  d="$1"
  if [ -d "$F/$d" ] && [ ! -d "$REF/$d" ]; then mkdir -p "$(dirname "$REF/$d")"; cp -a "$F/$d" "$REF/$d"; fi
  rm -rf "$F/$d"; mkdir -p "$(dirname "$F/$d")"; cp -a "$A/$d" "$F/$d"; echo "A31: $d"
}
for d in drivers/watchdog/mediatek drivers/misc/mediatek/ram_console drivers/misc/mediatek/boot \
         drivers/misc/mediatek/boot_reason drivers/misc/mediatek/chip drivers/misc/mediatek/ccmni; do rep $d; done
cp "$A/drivers/usb/gadget/function/f_accessory.c" "$F/drivers/usb/gadget/function/f_accessory.c"
cd "$F"
add() { grep -qF "$2" "$1" || { printf '\n# --- A31 port ---\n%s\n' "$2" >> "$1"; echo "hook $1"; }; }
add drivers/watchdog/Makefile 'obj-$(CONFIG_MEDIATEK_SOLUTION) += mediatek/'
grep -q 'drivers/watchdog/mediatek/Kconfig' drivers/watchdog/Kconfig || \
  sed -i '0,/^endif # WATCHDOG/s||source "drivers/watchdog/mediatek/Kconfig"\n\nendif # WATCHDOG|' drivers/watchdog/Kconfig
add drivers/misc/mediatek/Makefile 'obj-$(CONFIG_MTK_BOOT) += boot/'
add drivers/misc/mediatek/Makefile 'obj-$(CONFIG_MTK_BOOT_REASON) += boot_reason/'
add drivers/misc/mediatek/Makefile 'obj-$(CONFIG_MTK_RAM_CONSOLE) += ram_console/'
for k in boot boot_reason ram_console; do
  grep -q "drivers/misc/mediatek/$k/Kconfig" drivers/misc/mediatek/Kconfig || \
    sed -i "0,/^endmenu # Misc/s||source \"drivers/misc/mediatek/$k/Kconfig\"\nendmenu # Misc|" drivers/misc/mediatek/Kconfig
done
# Samsung log hooks need Samsung printk changes: not built
sed -i 's|^obj-$(CONFIG_SEC_EXT)\t\t\t+= sec_log.o|#obj-$(CONFIG_SEC_EXT)\t\t\t+= sec_log.o|' drivers/samsung/misc/Makefile
# Xiaomi-only hacks in the 4.19 tree
python3 -I - <<'EOF'
import re
p="drivers/mmc/core/mmc.c"; s=open(p).read()
s=s.replace("extern struct mmc_card *mv_card;", "/* A31: Xiaomi mv_card export removed */", 1)
s=re.sub(r"\n\s*if\s*\(!mv_card\)\s*\{\n\s*mv_card = card;\n[^\n]*\}\n", "\n", s, count=1)
open(p,"w").write(s); print("mmc.c mv_card:", "mv_card" in s)
p="drivers/video/fbdev/core/fbsysfs.c"; s=open(p).read()
s=s.replace("\t\tti_hbm_set((enum backlight_hbm_mode)hbm_mode);", "\t\t/* A31: Xiaomi ti_hbm_set */")
s=s.replace("\t\tktd_hbm_set((enum backlight_hbm_mode)hbm_mode);", "\t\t/* A31: Xiaomi ktd_hbm_set */")
open(p,"w").write(s); print("fbsysfs hbm:", "hbm_set((" in s)
EOF
for f in arch/arm64/configs/a31_4.19.fragment arch/arm64/configs/a31_defconfig; do
  sed -i -E '/^CONFIG_(MEDIATEK_WATCHDOG|EXTCON_MTK_USB|MMC_CQHCI)=y$/d' $f
  printf '# CONFIG_MEDIATEK_WATCHDOG is not set\n# CONFIG_EXTCON_MTK_USB is not set\n# CONFIG_MMC_CQHCI is not set\n# CONFIG_SEC_DEBUG_INIT_LOG is not set\nCONFIG_MEDIATEK_SOLUTION=y\nCONFIG_MTK_WATCHDOG=y\nCONFIG_MTK_WATCHDOG_COMMON=y\nCONFIG_MTK_WATCHDOG_COMMON_V2=y\nCONFIG_MTK_WD_KICKER=y\nCONFIG_MTK_RAM_CONSOLE=y\nCONFIG_MTK_BOOT=y\nCONFIG_MTK_BOOT_REASON=y\nCONFIG_MTK_CHIP=y\n' >> $f
done
echo batch6 done
