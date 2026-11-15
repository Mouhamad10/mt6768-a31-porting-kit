#!/bin/bash
# Batch 3: drivers that talk to A31 firmware / vendor daemons -> A31 versions.
#   eccci/ccci_util : md1img + ccci_fsd/ccci_mdinit (SIM, network)
#   connectivity/btif: wmt_loader/wmt_launcher + WiFi/BT/GPS/FM firmware
#   sspm/scp/audio_ipi: tinysys firmware in the A31 sspm/scp partitions (sensorhub, audio DSP)
#   m4u/cmdq        : used by the A31 display driver ABI
#   sound/soc/mediatek: Samsung audio (vendor audio HAL mixer controls)
#   cameraisp/ccu/cam_cal: camera HAL ABI
set -e
T=$(cd "$(dirname "$0")" && pwd); A="$1"; F="$2"; REF="$T/ref_fire"
replace_with_a31() {
  d="$1"
  [ -d "$A/$d" ] || { echo "no A31 $d"; return; }
  if [ -d "$F/$d" ] && [ ! -d "$REF/$d" ]; then mkdir -p "$(dirname "$REF/$d")"; cp -a "$F/$d" "$REF/$d"; fi
  rm -rf "$F/$d"; mkdir -p "$(dirname "$F/$d")"; cp -a "$A/$d" "$F/$d"
  echo "A31 version: $d"
}
for d in drivers/misc/mediatek/eccci drivers/misc/mediatek/ccci_util \
         drivers/misc/mediatek/connectivity drivers/misc/mediatek/btif \
         drivers/misc/mediatek/sspm drivers/misc/mediatek/scp drivers/misc/mediatek/audio_ipi \
         drivers/misc/mediatek/m4u drivers/misc/mediatek/cmdq \
         drivers/misc/mediatek/cameraisp drivers/misc/mediatek/ccu \
         sound/soc/mediatek; do
  replace_with_a31 "$d"
done
# Samsung sensorhub (SSP over SCP) — new in this tree
if [ ! -d "$F/drivers/sensorhub" ]; then cp -a "$A/drivers/sensorhub" "$F/drivers/sensorhub"; echo "added drivers/sensorhub"; fi
python3 -I - "$F" <<'EOF'
import sys
from pathlib import Path
F = Path(sys.argv[1])
k = F / "drivers/Kconfig"; s = k.read_text()
src = ['source "drivers/sensorhub/Kconfig"', 'source "drivers/sensorhub/debug/Kconfig"',
       'source "drivers/sensorhub/sensor/Kconfig"', 'source "drivers/sensorhub/sensorhub/Kconfig"',
       'source "drivers/sensorhub/vendor/Kconfig"']
src = [l for l in src if (F / l.split('"')[1]).exists() and l not in s]
if src:
    i = s.rfind("endmenu")
    s = s[:i] + "# --- A31 port: Samsung sensorhub ---\n" + "\n".join(src) + "\n\n" + s[i:]
    k.write_text(s); print("drivers/Kconfig sensorhub +%d" % len(src))
m = F / "drivers/Makefile"; s = m.read_text()
if "sensorhub/" not in s:
    m.write_text(s.rstrip("\n") + "\n\n# --- A31 port: Samsung sensorhub ---\nobj-y += sensorhub/\n"); print("drivers/Makefile sensorhub")
EOF
echo "batch3 done"
