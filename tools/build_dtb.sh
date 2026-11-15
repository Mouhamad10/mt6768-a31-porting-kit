#!/bin/bash
# build_dtb.sh <kernel_tree> <out_dir_with_generated_autoconf> <dest>
# Builds the A31 SoC base dtb (with __symbols__) and the board overlay dtbo.
set -e
K="$1"; O="$2"; D="$3"; mkdir -p "$D"
DTS="$K/arch/arm64/boot/dts"
pp() {
  cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp \
      -I "$O/include" -I "$DTS" -I "$DTS/mediatek" -I "$DTS/mediatek/a31" \
      -I "$K/include" -I "$K/scripts/dtc/include-prefixes" \
      -include "$O/include/generated/autoconf.h" "$1" -o "$2"
}
DTC="${DTC:-dtc}"
pp "$DTS/mediatek/mt6768.dts" "$D/mt6768.pp.dts"
$DTC -@ -q -I dts -O dtb -o "$D/mt6768.dtb" "$D/mt6768.pp.dts"
echo "base dtb: $(stat -c %s "$D/mt6768.dtb") bytes"
for b in a31_cis_ser_w00_r03 a31_cis_ser_w00_r00; do
  [ -e "$DTS/mediatek/a31/$b.dts" ] || continue
  pp "$DTS/mediatek/a31/$b.dts" "$D/$b.pp.dts"
  $DTC -@ -q -I dts -O dtb -o "$D/$b.dtbo" "$D/$b.pp.dts"
  echo "overlay $b.dtbo: $(stat -c %s "$D/$b.dtbo") bytes"
done
