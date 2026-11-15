# Bring-up crash database (MT6768 / A31)

Every early-boot crash hit while bringing up the **4.19.325** kernel on the A31, with the exact
log signature, the root cause, and the fix. These are ordered by how early they fire. The pattern
is almost always the same: a MediaTek platform driver probes hardware whose **device-tree node or
NVRAM/efuse cell is named differently** on the Samsung A31 than on the donor tree, dereferences an
`ERR_PTR`/`NULL`, and dies. The fix is to make the driver fall back the way the 4.14 Samsung kernel
did, **not** to change the device tree (that would break the byte-identical dtb).

How these were found: the 4.19 kernel mirrors its console into Samsung's `sec_log` RAM ring, and
the stock bootloader exposes the previous boot's kernel log at `/proc/last_kmsg`. Flash the test
kernel to the **recovery** partition only, boot it with the hardware keys, let it crash, boot back
to Android, and read `/proc/last_kmsg`. See [`recovery-test-method.md`](recovery-test-method.md).

---

## 1. gpufreq — NULL deref reading the GPU efuse

**Signature** (`~1.005 s`):
```
[GPU/DVFS][ERROR]@__mt_gpufreq_init_efuse: cannot get efuse_segment_cell
Unable to handle kernel NULL pointer dereference at virtual address 000000000000001e
pc : nvmem_cell_read+0x10/0x84
lr : __mt_gpufreq_pdrv_probe+0x550/0xbf0
```

**Cause:** `__mt_gpufreq_init_efuse()` calls `nvmem_cell_get(dev, "efuse_segment_cell")`. The A31
device tree (taken from the 4.14 Samsung kernel, kept byte-identical) has **no** `nvmem-cells`
entry for gpufreq — 4.14 read the segment with `get_devinfo_with_index(30)`. On the error path the
code printed the error but still passed the `ERR_PTR` straight into `nvmem_cell_read()`.

**Fix:** if `IS_ERR(efuse_cell)`, fall back to `get_devinfo_with_index(30) & 0xFF` (exactly what
4.14 did) instead of dereferencing. See `drivers/gpu/mediatek/gpufreq/mt6768/mtk_gpufreq_core.c`.
Rule of thumb: **every MTK driver that reads an efuse via nvmem on this device needs the same
`get_devinfo_with_index` fallback**, because the Samsung DT never carries those nvmem cells.

---

## 2. pinctrl/EINT — mount/IRQ deref because the EINT node is named differently

**Signature** (`~1.028 s`, first driver that requests a GPIO interrupt, here `accdet`):
```
mt6768-pinctrl pinctrl: Failed to add EINT, but pinctrl still can work
...
Unable to handle kernel NULL pointer dereference at virtual address 0000000000000004
pc : mtk_eint_set_debounce+0x34/0x22c
 mtk_gpio_set_config ... gpiod_set_debounce ... mt_accdet_probe
```

**Cause:** `mtk_build_eint()` in `pinctrl-mtk-common-v2.c` looks up the EINT controller by node
name `eint` (`of_find_node_by_name(NULL, "eint")`). On the A31 the node is labelled `eint` but is
actually named **`apirq@1000b000`**, so the lookup fails, `hw->eint` is never set up, and the first
driver to request a GPIO IRQ dereferences the NULL eint base. Without EINT, **no GPIO interrupt
works** — touch, buttons, sensors, USB/SIM detect.

**Fix:** resolve the EINT base through the `reg_base_eint` phandle first (as 4.14 does), then fall
back to the name:
```c
node = of_parse_phandle(np, "reg_base_eint", 0);
if (!node)
    node = of_find_node_by_name(NULL, "eint");
```

---

## 3. thermal sysrst cooler — BUG() on a bogus trip because the AP NTC ADC reads garbage

**Signature** (`~1.096 s`):
```
[Thermal/TZ/CPU]sysrst_buck_set_cur_state = 1
kernel BUG at drivers/misc/mediatek/thermal/common/coolers/mtk_cooler_sysrst.c:167!
pc : sysrst_tsap_set_cur_state
 ... thermal_cdev_update ... handle_thermal_trip ... mtk_cooler_sysrst_init
```

**Cause:** the `mtktsAP-sysrst` cooler calls `BUG()` deliberately as a "thermal protection reset"
when its zone crosses a trip at init. The AP-side thermistor (BTS, `mtk_ts_bts.c`) reads its NTC
through `thermistor-ch3` on the auxadc; on this port the channel mapping / calibration is off, the
zone reports an impossible temperature, the trip fires immediately, and the cooler reboots the SoC.

**Status:** not yet fixed in-tree. Options: correct the `io-channels`/`thermistor-ch*` mapping for
the A31 auxadc, or make the sysrst cooler's `set_cur_state` log-and-return instead of `BUG()` on a
clearly bogus (init-time) trip. This is the crash to tackle next on the 4.19 branch.

---

## 4. (debug aid) power-off wipes the RAM log

**Symptom:** on some builds the kernel reached a point where **something requested a full power-off**
(not a panic), the screen showed the logo ~15 s then the device powered down, and the DRAM log
(`sec_log` / `last_kmsg`) was lost to the cold boot — so there was nothing to read.

**Debug patch:** `CONFIG_A31_DEBUG_NO_POWEROFF` (in `kernel/reboot.c` + `arch/arm64/kernel/process.c`)
logs the caller of `kernel_power_off()` / `machine_power_off()` and does a **warm `kernel_restart()`
instead**, so the RAM log survives and you can read who asked to power off. **Debug only — never ship it.**

---

## Reading a crash yourself

The Image is gzip inside the Android boot image. To static-analyze a `pc :`/`lr :` without the
phone: unpack the boot image ([`tools/a31_bootimg.py`](../tools/a31_bootimg.py)), `gunzip` the
kernel, and match the faulting function against the source. Most of these were found by reading the
driver source **before** the next boot, predicting the next crash, and fixing a whole class at once
(all `nvmem`/efuse probes, all missing-DT-node lookups) rather than one crash per reboot — which is
the only way to make progress when every test needs a physical reboot.
