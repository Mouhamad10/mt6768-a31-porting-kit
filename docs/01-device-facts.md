# Device facts — Samsung Galaxy A31 (SM-A315F)

## SoC and hardware

| | |
|---|---|
| SoC | **MediaTek MT6768** (Helio P65), `MT6768V/CA` |
| RAM / storage | 4 GB, eMMC |
| PMIC | MT6358 (main) + Samsung **S2MU106** (charger / fuel-gauge / MUIC / PDIC) |
| Touch | Imagis **IST4050** (`sec_touchscreen`, chip id `0x4050`), I2C bus 6 @ 0x50 |
| Panel | Samsung `smcdsd` (A31), EA8076-class AMOLED, **command mode** |
| GPU | Mali-G52 MC2 (vendor userspace = mali bifrost **r25p0**) |
| TEE | Trustonic **TEE 410** (t-base) |
| Amp | SMA1303 |
| Cameras | s5kgm2 / hi2021q / s5k4hayx / gc5035 |
| EINT node | `apirq@1000b000` (label `eint`) — see crash #2 |
| CPU thermal | 8x, AP NTC via auxadc `thermistor-ch3` — see crash #3 |

## Bootloader / boot image

- Bootloader: `A315FXXS5DXB1`. Android boot header **v2**, page size 2048.
- Load addresses: kernel `0x40080000`, ramdisk `0x47c80000`, tags/dtb `0x4bc80000`.
- The dtb inside the boot image is an **Android DT table** (magic `0xd7b7ab1e`) with one entry;
  the board overlay lives in the `dtbo` partition.
- The A31 `mt6768.dts` rebuilt in a newer tree can be made **byte-identical** to the stock boot
  dtb (229 `__symbols__`, so the stock dtbo applies). Keep it identical — do not add nodes.

## Encryption / fstab (why `/data` is delicate)

- `/data` is **f2fs** with `inlinecrypt` and `fileencryption=aes-256-xts:aes-256-cts:v1`.
- Samsung SDP partitions `/keydata` and `/keyrefuge`.
- A kernel that lacks inline-crypt / fscrypt / SDP support can fail to mount `/data`, which may
  **format** it. Kernel must carry: `FS_ENCRYPTION_INLINE_CRYPT`, `MMC_CRYPTO_LEGACY`, SDP +
  `FSCRYPT_SDP`. This is the single most important compatibility item when moving to `boot`.

## Vendor (keep it, don't patch it)

- Stock vendor: `A315FXXS5DXB1` (Android 12, ext4). The custom ROM (UN1CA / One UI 8) runs on it.
- Vendor ships **10 kernel modules built for 4.14** that will not load on a newer kernel:
  `bt_drv_connac1x, connfem, fmradio_drv_mt6631, fpsgo, gps_drv, met, udc_lib, wlan_drv_gen4m,
  wmt_chrdev_wifi, wmt_drv`. On a new kernel, **build these drivers in** and remove the vendor
  `insmod` lines via a **Magisk overlay** on `/vendor/etc/init/*.rc` — never by flashing vendor.

## Partition map (names under `/dev/block/by-name/`)

`boot`, `recovery`, `dtbo`, `vbmeta`, `vbmeta_samsung`, `lk`, `md1img` (modem), `md_udc` (=/metadata),
`super` (system/vendor/product/odm), `userdata`, `nvdata`, `nvcfg`, `efs`, `protect1/2`,
`metadata`, `misc`, `param`, `up_param`, `tee1`, `gz1/2`, `spmfw`, `scp1`, `sspm_1`, `persist`,
`keydata`, `keyrefuge`, `proinfo`, `prism`, `optics`, `omr`, `carrier`, `efuse`, `uh`.

Modem NV lives in `nvdata/md/NVRAM`, `protect_f/md`, `protect_s/md`, `efs`. IMEI in
`nvdata/md/NVRAM/NVD_IMEI`. These are **never** touched by kernel/recovery flashing.

## RAM log regions (from the LK log)

`ram_console 0x4d000000` (64K), `pstore 0x4d010000` (0xe0000), `sec-log 0x46C00000` (2M),
`sec-lastklog 0x46E00000` (2M), `sec-logger 0x47000000` (4M). The kernel mirrors its console into
`sec-log`; the bootloader surfaces the previous boot at `/proc/last_kmsg`.
