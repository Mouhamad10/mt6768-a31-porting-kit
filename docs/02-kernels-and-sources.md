# Kernels and sources

## Stock kernel

- Samsung ships **4.14.186** for the A31 (`A315FXXS5DXB1`, Android 12 base). Built with the
  stock GKI-less Samsung/MTK tree. Open-source drop is the basis of the community trees below.
- The stock kernel expects the Samsung DT (EINT as `apirq`, no gpufreq nvmem cells, AP NTC thermal,
  SDP crypto). Any newer kernel must reproduce these behaviours or crash (see the crash database).

## Atrocious V6 (daily driver, 4.14.186)

- The working daily kernel. Source: [`Mouhamad10/SM-A315F`](https://github.com/Mouhamad10/SM-A315F)
  (branch `A315FXXS5DXB1`); upstream `github.com/SN-Abdullah-Al-Noman/SM-A315F` @ `66a5095b6` (+1
  config commit). Toolchain: clang `r383902` + GCC 4.9.
- Boots, decrypts `/data`, everything works. This is the reference ABI every port must match.
- **How it is built:** `make O=out <defconfig> && make O=out -j$(nproc) Image.gz`, then the Image
  is packed into a Samsung boot image (header v2). Magisk is patched in afterward (the running
  daily `boot` is Atrocious + Magisk).

## Lucreticus (4.14.357 + eBPF ~5.15 backports)

- Source: [`Mouhamad10/kernel_samsung_mt6768-lucreticus`](https://github.com/Mouhamad10/kernel_samsung_mt6768-lucreticus)
  (branch `r1-Armaros`); upstream `github.com/stardustps/kernel_samsung_mt6768-lucreticus`
  @ `54c11cfc0` + A31 commits.
- Boots and decrypts `/data`, but **USB/ADB was broken** in the tested build. Notes gathered during
  bring-up: UH/RKP must be **OFF** (otherwise it hangs after "jump to linux kernel"),
  `INPUT_SEC_INPUT` off, and it needs `SDP + FSCRYPT_SDP + MMC_CRYPTO_LEGACY`.

## A31 4.19 port (this kit's patch stack)

- Base: Xiaomi Redmi 12 **`fire`** tree, `4.19.325-cip124`, LineageOS 23.2 branch, commit
  `9937de9f6` — upstream [`mt6768-dev/android_kernel_xiaomi_fire`](https://github.com/mt6768-dev/android_kernel_xiaomi_fire).
  Chosen because it is a complete MT6768 platform (legacy display, mali bifrost r25p0) that already
  runs Android 16.
- Apply the **29 patches** in [`../patches/`](../patches/): they import the Samsung A31 drivers from
  Atrocious, keep every vendor/firmware-ABI driver at its A31 (4.14) version, add compat shims
  (legacy timer API, pm_qos→mtk_pm_qos, wakeup_source, Samsung power_supply/input headers, SDP into
  fs/crypto), rebuild the A31 dts byte-identical, and wire `a31_defconfig`.
- Then apply the three bring-up fixes documented in the [crash database](../bring-up/crash-database.md):
  gpufreq efuse fallback, EINT phandle lookup, (pending) thermal sysrst. The exFAT/sdfat fix for
  4.14 is separate — see [`../bring-up/sdfat-exfat-fix.md`](../bring-up/sdfat-exfat-fix.md).
- Result so far: builds clean (clang 18), boots, runs ~1 s, crashes in the thermal sysrst cooler.
  Image placement/size are not the problem (uncompressed image ends at the same address as Atrocious).

### Applying the patch stack

```sh
git clone https://github.com/mt6768-dev/android_kernel_xiaomi_fire fire
cd fire && git checkout 9937de9f6e23641ffaae60b57fcaf7f5b610b202
git config core.autocrlf false           # the patches contain CRLF in some files; keep them
git am --keep-cr --whitespace=nowarn /path/to/kit/patches/*.patch
cp /path/to/kit/configs/a31_defconfig arch/arm64/configs/
```

## ROM

- [`Mouhamad10/UN1CA`](https://github.com/Mouhamad10/UN1CA) (branch `sixteen`) — the One UI 8
  (Android 16) port that runs on the stock A12 vendor. This is the userspace the kernel must serve.
