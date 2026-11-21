# Galaxy A41 (SM-A415F) — SELinux ioctl-xperms bootloop

## Evidence identity

- Device: Galaxy A41, model marker `SM-A415F_EUR`.
- Firmware marker in the captured ramoops: `A415FXXU8DXJ1`.
- SoC/device tree marker: `MT6768V/CA`.
- Kernel actually booted for this capture: `4.14.186 Atrocious Kernel V:6 #1`.
- This diagnosis is specific to this A41 capture. Do not treat it as proof that A31 or a later A41 kernel build has the same failure.

## Confirmed fatal chain

The captured `console-ramoops.txt` establishes this sequence:

1. First-stage init starts (around log lines 366–368).
2. `/system` mounts successfully as EROFS; init explicitly skips `/product` (around 399–405).
3. Device-mapper status queries for `system_ext` and `product` fail (around 1979–1982). These are warnings in this capture; they are not the terminal compiler error.
4. The system and ODM precompiled-policy hashes differ, so init takes the policy compilation path (around 1983–1985).
5. Init caps policy version from 30 to 29 because the running kernel reports no xperms support (line 1986).
6. Init reports stripping 837 xperms CIL rules (around 2131–2132), but at least one ioctl extended-permission rule remains in the final CIL input.
7. `libsepol.avtab_write_item` reports: `policy version 29 does not support ioctl extendedpermissions rules and one was specified`; binary-policy serialization fails, `secilc` exits 255, and init reports `Unable to open SELinux policy` (around 2324–2329).
8. `InitFatalReboot`, `InitAborter`, and `SetupSelinux` appear in the fatal stack, followed by reboot to bootloader (around 2330 onward).

**Confirmed root cause:** secilc was asked to emit policy version 29 while the merged CIL still contained at least one ioctl-xperm rule. libsepol refused to serialize the binary policy; SetupSelinux aborted because no valid binary policy was produced.

## What this log does not prove

- It does not identify which CIL input contributed the remaining ioctl-xperm rule.
- It does not prove the missing `product` or `system_ext` device-mapper nodes caused the compiler failure.
- It does not prove a `plat_sepolicy_vers.txt` mapping-version mismatch.
- It does not establish that every xperm rule was stripped: the compiler error proves at least one incompatible ioctl-xperm rule remained.

Permissive mode is not a remedy. The policy fails during compilation, before a binary policy can be loaded and enforced.

## Kernel fix path — source audit required

Policy version 30 represents ioctl extended permissions. Upstream Linux has supported this format since Linux 4.3; therefore, Linux 4.14 is not inherently too old. The captured kernel advertises a maximum of 29, so inspect the exact A41 kernel source before changing the version cap.

Audit:

- `security/selinux/include/security.h`: `POLICYDB_VERSION_XPERMS_IOCTL` and `POLICYDB_VERSION_MAX`.
- `security/selinux/ss/policydb.[ch]`: binary policy parsing and serialization.
- `security/selinux/ss/avtab.[ch]`: `AVTAB_XPERMS` representation and handling.
- `security/selinux/ss/services.[ch]` and `security/selinux/avc.c`: runtime xperm decision evaluation.
- `security/selinux/selinuxfs.c`: policy version exported to userspace.
- The actual A41 `.config`, defconfig, and vendor Kconfig overrides.

Only expose policy version 30 if the parser, writer, AV table, and runtime evaluation are complete and coherent. Otherwise backport the complete compatible xperms implementation. Do not change only `POLICYDB_VERSION_MAX`.

## Userspace follow-up

Find the exact CIL file/rule that survives the reported 837-rule stripping pass. Inspect the generated/merged CIL for `allowxperm`, `auditallowxperm`, `dontauditxperm`, `neverallowxperm`, and generated permissionx constructs. Do not blindly delete these rules: that changes ioctl access semantics and can weaken policy.

Separately compare super metadata, dynamic partition groups, fstab, and actual logical partition names to explain the `product`/`system_ext` DM warnings. Keep that investigation independent until evidence links it to the policy compiler failure.

## Read-only source audit

Run:

```sh
tools/audit-selinux-xperms.sh /path/to/exact/a41/kernel/source
```

The script only reports implementation/version markers. It does not modify source, build, or flash a kernel.
