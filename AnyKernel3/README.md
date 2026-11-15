# AnyKernel3 config (A31)

`anykernel.sh` is the A31 config that [`build-kernel.yml`](../.github/workflows/build-kernel.yml)
uses to package the built `Image.gz` into a TWRP-flashable ZIP. The CI clones the upstream
[AnyKernel3](https://github.com/osm0sis/AnyKernel3) at run time, drops this `anykernel.sh` and the
built `Image.gz` in, and zips it — so only this small config lives in the repo.

- Default: flashes the kernel into **`boot`** (keeps your existing ramdisk/Magisk).
- For **data-safe testing**, change `block=` to the `recovery` partition (see the comment in the
  file) and flash that zip, then boot recovery with the keys.
- `do.devicecheck=0` so it won't refuse to flash on a ROM that spoofs `ro.product.device`
  (this One UI port reports `r0s`). Flash only on an actual A31.
