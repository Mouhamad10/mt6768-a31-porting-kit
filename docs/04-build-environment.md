# Build environment

Builds were done on **WSL Ubuntu 24.04** with **clang 18 / ld.lld**. A GitHub Codespace works the
same way (the kit is designed so anyone can build from the account).

## Toolchain

```sh
sudo apt install -y clang-18 lld-18 llvm-18 make bc flex bison libssl-dev libelf-dev \
                    cpio lz4 xz-utils gcc device-tree-compiler python3
# a cross binutils is optional; LLVM=1 LLVM_IAS=1 does assembly/link itself
```

For 4.14/Atrocious the original toolchain is clang `r383902` + GCC 4.9 (in Samsung's prebuilts).
For the 4.19 port, clang 18 builds it cleanly.

## Building the 4.19 A31 kernel

See [`tools/kflags.env`](../tools/kflags.env) for the exact flags. Summary:

```sh
export ARCH=arm64 LLVM=1 LLVM_IAS=1 CROSS_COMPILE=aarch64-linux-gnu-
export KCFLAGS="-Werror=implicit-function-declaration -Werror=int-conversion \
                -Werror=incompatible-pointer-types -Werror=return-type ..."   # see kflags.env
make O=out a31_defconfig
make O=out -j$(nproc) Image.gz
```

**Never use `-w`** to silence warnings — it hid real bugs during this port. Keep the
`-Werror=implicit-function-declaration,int-conversion,incompatible-pointer-types` set on; they catch
exactly the merge mistakes that otherwise crash at boot.

Output: `out/arch/arm64/boot/Image.gz` (~18 MB). Pack it into a boot/recovery image with
[`tools/a31_bootimg.py`](../tools/a31_bootimg.py).

## Config

- [`configs/a31_defconfig`](../configs/a31_defconfig) — full defconfig.
- [`configs/a31_4.19.fragment`](../configs/a31_4.19.fragment) — the A31 delta over the fire base.
- Key options on: `EROFS_FS` + `EROFS_FS_ZIP`, `F2FS`, `FS_ENCRYPTION_INLINE_CRYPT`,
  `MMC_CRYPTO_LEGACY`, `IKCONFIG_PROC`.
- Deliberately **off**: UH/RKP (hangs after "jump to linux kernel"), KPERFMON,
  `MTK_EMMC_HW_CQ`/`MMC_CQHCI` (need 4.14 mmc core), `SEC_DEBUG_AUTO_COMMENT`, `MTK_AEE_HANGDET`,
  `MTK_CM_MGR` (use cm_mgr_v1), `MEDIATEK_WATCHDOG`, `EXTCON_MTK_USB`.

## Tools

| Tool | Purpose |
|---|---|
| `a31_bootimg.py` | info / unpack / repack Android boot image header v0–v2 (byte-identical repack verified) |
| `dttable.py` | wrap/unwrap the Android DT table (`0xd7b7ab1e`) |
| `build_dtb.sh` | build the A31 SoC base dtb (with `__symbols__`) + board dtbo |
| `merge3.py`, `transplant_ifdefs.py`, `port_pmqos.py`, `audit_merge.py` | driver-merge helpers used to port A31 drivers onto the newer core |
| `kflags.env` | the exact build flags |

## Boot-image sanity check (before flashing)

After repacking, confirm only the kernel changed:

```sh
python3 a31_bootimg.py info new.img         # compare kernel_size, cmdline, dtb_size vs the original
# the ramdisk, dtb and cmdline md5 should be identical to the source image
```

For a **minimal in-place kernel tweak** you can even binary-patch the gzipped Image and repack,
changing only the bytes you intend — see the sdfat fix, which changed a single byte in the
decompressed Image and left ramdisk/dtb/cmdline/Magisk untouched.
