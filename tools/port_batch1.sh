#!/bin/bash
# Batch 1: bring Samsung A31 self-contained drivers (4.14 Atrocious) into fire 4.19.325 tree.
# Only ADDS files that do not exist in the target; never overwrites fire files.
set -e
A="$1"   # A31 source (atr)
F="$2"   # target (fire)
[ -d "$A" ] && [ -d "$F" ] || { echo "usage: $0 <a31_src> <fire_tree>"; exit 1; }

DIRS="
drivers/samsung
drivers/battery
drivers/muic
drivers/vibrator
drivers/sti
drivers/switch
drivers/sensors
drivers/fingerprint
drivers/usb/notify
drivers/usb/typec/slsi
drivers/usb/typec/common
drivers/usb/typec/manager
drivers/mfd/slsi
drivers/regulator/s2mpb03
drivers/regulator/pmic_class
drivers/hwmon/sec_thermistor
drivers/input/touchscreen/imagis
drivers/security/samsung
drivers/spu_verify
security/samsung
security/sdp
fs/sdfat
"
copied=0
for d in $DIRS; do
  if [ ! -d "$A/$d" ]; then echo "skip (not in A31): $d"; continue; fi
  if [ -d "$F/$d" ]; then
    # merge: add only missing files
    (cd "$A/$d" && find . -type f) | while read -r f; do
      [ -e "$F/$d/$f" ] || { mkdir -p "$(dirname "$F/$d/$f")"; cp -p "$A/$d/$f" "$F/$d/$f"; }
    done
    echo "merged: $d"
  else
    mkdir -p "$(dirname "$F/$d")"; cp -a "$A/$d" "$F/$d"; echo "copied: $d"
  fi
done

# single files
for f in drivers/input/sec_cmd.c drivers/input/sec_tclm_v2.c drivers/input/sec_tsp_log.c \
         sound/soc/codecs/sma1303.c sound/soc/codecs/sma1303.h \
         drivers/nfc/sec_nfc.c drivers/nfc/sec_nfc.h; do
  [ -e "$A/$f" ] || { echo "skip file: $f"; continue; }
  [ -e "$F/$f" ] || { cp -p "$A/$f" "$F/$f"; echo "file: $f"; }
done

# headers that only exist in A31
(cd "$A" && find include -type f) | while read -r f; do
  [ -e "$F/$f" ] || { mkdir -p "$(dirname "$F/$f")"; cp -p "$A/$f" "$F/$f"; }
done
echo "headers done"
