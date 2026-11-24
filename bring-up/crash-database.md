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

## 5. init::SetupSelinux() abort — policy LOAD failure, not an enforcement denial

**Confirmed on:** [`Mouhamad10/oneos-a31` release `vendor-lumi-ext4-v1`](https://github.com/Mouhamad10/oneos-a31/releases/tag/vendor-lumi-ext4-v1)
(`vendor_a31_lumi.img`, ext4) — a **stock Samsung Android 12** vendor
(`ro.vendor.build.fingerprint=samsung/a31nsxx/a31:12/SP1A.210812.016/A315GXXU5DXJ1:user/release-keys`,
`ro.vndk.version=31`, security patch 2022-03) — paired with an Android 15 GSI.

**Signature** (`~2.4-2.6 s`, MT6768/A31, this vendor + Android 15 GSI, `product` removed from the layout):
```
init: Could not update logical partition
init: DM_DEV_STATUS failed for product: No such device or address
init: Could not update logical partition
init: Missing /vendor/etc/selinux/vendor_sepolicy_debug.cil
init:   #01 pc ... /system/bin/init (android::init::InitAborter(char const*)+48)
init:   #04 pc ... /system/bin/init (android::init::SetupSelinux(char**)+4960)
... ~1.8 s later ...
init: sec_reboot (0, bootloader)
<WDT register dump, hardware reset>
```

**Cause:** this is a **policy load/merge failure**, which happens before enforcement is even
consulted — an `androidboot.selinux=permissive` kernel does **not** protect against it. Permissive
mode only skips *enforcing* denials from a policy that already loaded successfully; `SetupSelinux()`
calls `InitAborter()` when it cannot construct a valid merged policy at all, regardless of
enforcing/permissive. Two contributing factors, usually seen together on a GSI-on-older-vendor port:

1. **`plat_sepolicy_vers.txt` / sepolicy mapping mismatch** — the vendor (here, a One UI 6.1 /
   Android 14 vendor) declares a platform sepolicy API level in
   `/vendor/etc/selinux/plat_sepolicy_vers.txt`. The system side must ship a matching
   `/system/etc/selinux/mapping/<that version>.cil` to translate old vendor policy into the newer
   platform policy. Pairing an old vendor with a newer (Android 15) GSI is exactly the situation
   where that mapping file can be missing — the same class of bug as the A31 `31` vs `30`
   `plat_sepolicy_vers.txt` fix, just a different pair of versions.
2. **Stale, non-`nofail` reference to a removed partition — CONFIRMED on this vendor.** `product`
   was deliberately removed (this GSI does not need it), but the vendor's own
   `/vendor/etc/fstab.mt6768` (inside `vendor_a31_lumi.img`) still ships:
   ```
   product /product ext4 ro wait,,avb,logical,first_stage_mount
   ```
   — `wait` with **no `nofail`**, meaning fs_mgr treats `/product` as a **mandatory** partition.
   Deleting the partition image is not the same as telling fstab it is optional: init still calls
   `DM_DEV_STATUS` for it at boot (→ `No such device or address`, directly in this log), and with no
   `nofail` the split-sepolicy loader that follows still expects `product_sepolicy.cil` /
   `product_file_contexts` / `product_property_contexts` to exist. **This is the confirmed,
   reproducible cause on this specific vendor release.**

**Why it ends in `fastbootd` instead of a normal retry:** once `InitAborter()` kills PID1, the kernel
cannot continue (PID1 dying is always fatal to Linux). On this platform that kernel panic is caught by
Samsung's `sec_debug`/watchdog path, which forces `sec_reboot(0, "bootloader")` and performs the reset
via the MTK watchdog (`toprgu`) — visible as the WDT register dump right after. If this device/build
only exposes `fastbootd` (no interactive preloader/bootloader menu) for that reboot target, the device
has no soft way out of the loop. **This is a symptom of the crash, not a separate bug to patch around**
— fixing the two causes above so `SetupSelinux()` never aborts is what stops the reboot from
happening in the first place, which is the only reliable way to stay out of `fastbootd` here.

**Fix:**
1. **Do this first (confirmed cause) — now automated:** run
   [`tools/patch_vendor_fstab.sh`](../tools/patch_vendor_fstab.sh) on the vendor image, or use the
   **"Patch vendor fstab + check sepolicy mapping"** GitHub Action
   ([`patch-vendor.yml`](../.github/workflows/patch-vendor.yml)). It adds `nofail` to the matching
   fstab line(s) without touching anything else (AVB flags, fs type, every other partition):
   ```
   product /product ext4 ro wait,nofail,,avb,logical,first_stage_mount
   ```
   This alone stops the `DM_DEV_STATUS failed for product` fatal path, since fs_mgr will then treat a
   missing `/product` as optional instead of a boot-blocking requirement. It also writes a
   `vendor-sepolicy-report.txt` with the vendor's `plat_sepolicy_vers.txt` / `vendor_sepolicy_version`
   / `ro.vndk.version` for step 2.
   > This is the one place in this kit that patches the vendor image at all (see the note in the
   > [README](../README.md)) - everywhere else the rule is "adapt the kernel, never the vendor". It's
   > justified here because the mismatch is self-inflicted by the GSI pairing (you removed `product`
   > from the layout), not a stock-vendor behavior being changed.
2. **Still verify (unconfirmed, may compound) — also automated:** this vendor declares
   `plat_sepolicy_vers.txt = 31.0` / `ro.vndk.version=31` — a **stock Android 12** vendor (security
   patch 2022-03) being paired with an Android 15 GSI, a 3-major-version vendor freeze gap. Run
   [`tools/check_sepolicy_mapping.py`](../tools/check_sepolicy_mapping.py) `31.0 <gsi-or-system.img>`
   (or fill `gsi_url` in the same Action) to confirm the GSI's `/system/etc/selinux/mapping/` still
   ships a `31.0.cil` — if the GSI build dropped mapping support below a higher floor (e.g. only ships
   `33.0.cil` and up), `SetupSelinux()` can still abort even after fix #1, independent of the
   `product` issue. This check is informational only — there is no safe automatic fix for a missing
   mapping file (pulling one forward from another system image is a manual, per-build decision).
3. Recompile/repackage the merged policy (`precompiled_sepolicy`) after any vendor-side change, so it
   matches the updated `fstab`/sepolicy manifest.
4. Re-run [`tools/triage-bootlog.py`](../tools/triage-bootlog.py) on the next capture — the
   `selinux-setup-abort` / `stale-partition-dm-status` correlation (in
   [`boot-signatures.json`](../tools/boot-signatures.json)) will confirm whether the same fault
   still fires, and whether a *different* fatal signature appears instead (pointing at cause #1).

**Status:** cause #2 (`product` fstab entry missing `nofail`) is **confirmed** by direct inspection of
`vendor_a31_lumi.img` from
[`oneos-a31` release `vendor-lumi-ext4-v1`](https://github.com/Mouhamad10/oneos-a31/releases/tag/vendor-lumi-ext4-v1).
Cause #1 (sepolicy mapping-version gap) is a plausible compounding factor given the Android-12-vendor
+ Android-15-GSI pairing, but needs the GSI's `/system/etc/selinux/mapping/` contents to confirm.

### ⚠️ `nofail` regression — observed, not fully explained

On this same vendor/GSI pairing, flashing a vendor patched with `nofail` (keeping the `product`
fstab line, just making it non-fatal) regressed boot: instead of reaching second-stage init and
aborting at `SetupSelinux()` (the original signature above), the device now fast-reboots at the
boot logo — i.e. it fails in **first-stage** init, *earlier* than the unpatched baseline. The
reboot is fast enough that no new console-ramoops capture survives it, so this has not been
confirmed with a log — logged here as an observed correlation, not a proven mechanism.

**Working theory:** some GSI builds embed their own compatibility stub for a merged/absent
`product` (e.g. a symlink or stub directory shipped inside `system.img` itself, so the GSI is
self-contained without a separate `product` partition at all). A fstab line for the same mount
point that is merely marked optional (`nofail`) — as opposed to fully absent — may still cause
first-stage init to attempt to reconcile two different ideas of what `/product` is, in a way a
vendor with *no* `product` fstab entry at all does not. Unconfirmed.

**Current default: delete the line entirely, not `nofail`.**
[`tools/patch_vendor_fstab.sh`](../tools/patch_vendor_fstab.sh) now defaults to `--mode delete`
(removes the matching fstab line(s) outright); `--mode nofail` still exists for comparison
testing but should not be assumed safe given the above. Re-tested against
`vendor_a31_lumi.img` after this change: `fstab.mt6768` goes from 113 to 112 lines, no `product`
reference remains anywhere in the file, `tune2fs -l` still reports `Filesystem state: clean` with
identical feature flags. **Not yet flight-tested on-device** (reported by the repo owner as the
next thing to try) — if this still fails, the next log capture is what this kit actually needs to
move past "observed regression" into a confirmed mechanism.

---

## Reading a crash yourself

The Image is gzip inside the Android boot image. To static-analyze a `pc :`/`lr :` without the
phone: unpack the boot image ([`tools/a31_bootimg.py`](../tools/a31_bootimg.py)), `gunzip` the
kernel, and match the faulting function against the source. Most of these were found by reading the
driver source **before** the next boot, predicting the next crash, and fixing a whole class at once
(all `nvmem`/efuse probes, all missing-DT-node lookups) rather than one crash per reboot — which is
the only way to make progress when every test needs a physical reboot.

---

## Appendix: signatures seen on the already-booting kernel

These are not 4.19 bring-up crashes — they are things seen in a `ramoops`/`last_kmsg` dump from the
**current, booting** kernel. They are recorded here (and in
[`tools/boot-signatures.json`](../tools/boot-signatures.json)) so the triage tool reads them
correctly instead of raising a false alarm. See [`boot-log-signatures.md`](boot-log-signatures.md).

### A. Deliberate forced reset — **not a crash**

**Signature:**
```
Hard Reset
kernel BUG at drivers/samsung/sec_hard_reset_hook.c:131!
pc : hard_reset_hook_callback+0x88/0x90
 ... __hrtimer_run_queues ...
```

**Cause:** this is Samsung's forced-upload/ramdump hook. Holding **Volume-Down + Power** long enough
makes a timer fire a deliberate `BUG()` so the RAM log can be captured. It is **user-triggered**, not
a spontaneous fault. A ramdump whose only `BUG()` is this one means the kernel booted fine and you
forced the reset — the surrounding log (here: APEX activated, services up at ~8 s) confirms a healthy
boot. The triage tool suppresses the generic "Oops" on the same line so it does not look like a real
crash. To capture a *spontaneous* crash, do not hold the keys.

### B. eBPF program load failure — old kernel vs new Android

**Signature:**
```
NetBpfLoad: libbpf: prog '...': failed to load: -13
NetBpfLoad: === CRITICAL FAILURE LOADING BPF PROGRAMS ===
NetBpfLoad: --- DO NOT EXPECT SYSTEM TO BOOT SUCCESSFULLY ---
```

**Cause:** Android's `netbpfload` tries to load mainline `netd` eBPF programs that the older kernel's
BPF verifier / BTF support rejects (`-13` = EPERM / verifier reject). Despite the wording, boot
**does** continue — but per-UID network stats, tethering and some firewall paths are degraded.

**What to check:** `CONFIG_BPF`, `CONFIG_BPF_SYSCALL`, `CONFIG_DEBUG_INFO_BTF`, `CONFIG_CGROUP_BPF`
and the net BPF hooks. On a 4.x kernel some newer programs simply cannot load — that is a
kernel-version gap, not a patchable driver bug. It is the clearest reason to move to a newer kernel
base (5.10 GKI) for a modern Android userspace, rather than something to patch on 4.x.

### C. The definitive bootloop — `reboot,bpfloader-failed` (eBPF gap)

A later capture (an A34 system/vendor on the A31) pinned down exactly how a modern Android dies on
the 4.14 kernel. This supersedes the vaguer note in B.

**Signature (console ring):**
```
netbpfload: non-optional program schedcls_tether_downstream6_ether failed to load
NetBpfLoad: === CRITICAL FAILURE LOADING BPF PROGRAMS ===
init: Service bpfloader (pid 998) exited with status 38 waiting took 20.035 seconds
init: Service bpfloader has 'reboot_on_failure' option and failed, shutting down system.
init: ####Reboot start, reason: reboot,bpfloader-failed
reboot: Restarting system with command 'bpfloader-failed'  ->  sec_reboot (0, bpfloader-failed)
```

**Signature (pmsg/tombstone ring, same boot):**
```
*** system_server native crash occurred ***
#01 register_com_android_server_connectivity_ClatCoordinator(...)   (libservice-connectivity.so)
    -> NetworkStatsServiceInitializer.<init> -> abort (SIGABRT), repeating across zygote re-forks
```

**Cause:** the 4.14 kernel's eBPF verifier/feature set cannot load the newer Android tethering APEX's
BPF programs. `bpfloader` is declared `reboot_on_failure`, so when it exits non-zero init force-reboots
with reason `bpfloader-failed` — a guaranteed bootloop. The `system_server` ClatCoordinator `SIGABRT`
is the **same** missing clat (464XLAT) BPF maps seen from user space. The vendor audio-HAL `SIGSEGV`
in the same log is an unrelated A34/A32-vendor-on-A31 mismatch, not boot-fatal.

**Decisive proof it is the `reboot_on_failure` flag, not the BPF warning:** the working 4.14 ROM
prints the identical `CRITICAL FAILURE LOADING BPF PROGRAMS` line and still boots, because its
`bpfloader` is not `reboot_on_failure`.

**Status / fix:** no source patch — an old-kernel-vs-new-Android capability gap. The real fix is a
**newer kernel base (5.10+ GKI)** with the BPF features the tethering APEX needs; this is the single
strongest argument for the 5.10 move. The only 4.14 stopgap is to remove `reboot_on_failure` from the
`bpfloader` `.rc`, which lets the device boot with broken tethering/clat instead of bricking. The
[boot-log triage](boot-log-signatures.md) tool encodes this as the `bpfloader-reboot` /
`netbpf-load-fail` / `clat-coordinator-abort` signatures plus a same-boot correlation rule.
