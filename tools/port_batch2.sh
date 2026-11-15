#!/bin/bash
# Batch 2: API fixes + A31 versions of vendor-ABI drivers on the 4.19 tree.
set -e
T=$(cd "$(dirname "$0")" && pwd)
A="$1"; F="$2"; REF="$T/ref_fire"
mkdir -p "$REF"
py() { python3 -I "$@"; }

replace_with_a31() {   # keep fire copy as reference, put A31 version in place
  d="$1"
  [ -d "$A/$d" ] || { echo "no A31 $d"; return; }
  if [ -d "$F/$d" ] && [ ! -d "$REF/$d" ]; then mkdir -p "$(dirname "$REF/$d")"; cp -a "$F/$d" "$REF/$d"; fi
  rm -rf "$F/$d"; mkdir -p "$(dirname "$F/$d")"; cp -a "$A/$d" "$F/$d"
  echo "A31 version: $d"
}

# 1) power_supply (Samsung battery stack ABI) + SMA1303 component API
py "$T/port_psy.py" "$A" "$F"
py "$T/port_sma1303.py" "$F/sound/soc/codecs/sma1303.c"

# 2) Samsung input codes / sec log, printk auto-comment levels
py "$T/merge_defines.py" "$F/include/uapi/linux/input-event-codes.h" "$A/include/uapi/linux/input-event-codes.h"
grep -q 'define SECLOG' "$F/include/uapi/linux/input.h" || \
  sed -i '0,/#include <linux\/types.h>/s//#include <linux\/types.h>\n\n#define SECLOG\t\t\t"[sec_input]"/' "$F/include/uapi/linux/input.h"
for h in include/linux/kern_levels.h include/linux/printk.h; do
  py "$T/merge3.py" "$F/$h" "$A/$h" || true
done

# 3) Samsung SDP on fscrypt + VFS hooks (3-way merge onto the 4.19 code)
cp -a "$A/fs/crypto/sdp" "$F/fs/crypto/" 2>/dev/null || true
cp -n "$A/fs/crypto/fscrypt_knox_private.h" "$F/fs/crypto/" || true
for f in Kconfig Makefile crypto.c fname.c fscrypt_private.h keysetup.c keysetup_v1.c policy.c; do
  py "$T/merge3.py" "$F/fs/crypto/$f" "$A/fs/crypto/$f" || true
done
for f in include/linux/fscrypt.h fs/ext4/ioctl.c fs/ext4/super.c fs/libfs.c fs/f2fs/file.c fs/f2fs/super.c \
         fs/namei.c fs/read_write.c include/linux/sched.h include/linux/pagemap.h; do
  py "$T/transplant_ifdefs.py" "$F/$f" "$A/$f" 'FSCRYPT_SDP|CONFIG_SDP|CONFIG_DDAR' || true
done

# 4) Trustonic 410 on 4.19 APIs
m="$F/drivers/misc/mediatek/gud/410/MobiCoreDriver/mmu.c"
sed -i 's/&pm_mutex/\&system_transition_mutex/g; s/release_pages(pages, gup_ret, 0)/release_pages(pages, gup_ret)/g' "$m"
grep -q '<linux/suspend.h>' "$m" || sed -i '0,/#include <linux\/mm.h>/s//#include <linux\/mm.h>\n#include <linux\/suspend.h>/' "$m"

# 5) sec_debug: seq_file no longer pulled in implicitly
for f in drivers/samsung/debug/sec_debug.c; do
  grep -q '<linux/seq_file.h>' "$F/$f" || sed -i '0,/#include/s//#include <linux\/seq_file.h>\n#include/' "$F/$f"
done

# 6) vendor-ABI drivers: A31 versions
replace_with_a31 drivers/misc/mediatek/accdet
replace_with_a31 drivers/misc/mediatek/usb20
replace_with_a31 drivers/misc/mediatek/imgsensor
replace_with_a31 drivers/misc/mediatek/cam_cal
replace_with_a31 drivers/misc/mediatek/flashlight
replace_with_a31 drivers/misc/mediatek/video
replace_with_a31 drivers/misc/mediatek/lcm
replace_with_a31 drivers/misc/mediatek/ext_disp
f=drivers/misc/mediatek/pmic/mt6358/v1/pmic_throttling_dlpt.c
py "$T/merge3.py" "$F/$f" "$A/$f" || true
echo "batch2 done"
