# A41 Atrocious V6 kernel source — ioctl-xperms audit

## Source identity

Public source located for the A41 model and matching firmware branch:

- Repository: [SN-Abdullah-Al-Noman/SM-A415F](https://github.com/SN-Abdullah-Al-Noman/SM-A415F)
- Branch: `A415FXXU8DXJ1`
- Branch HEAD: [`293d64d06d77f42abaf8176e499474339910b350`](https://github.com/SN-Abdullah-Al-Noman/SM-A415F/commit/293d64d06d77f42abaf8176e499474339910b350)
- Commit message: `Update local version to 'Atrocious Kernel V:6'`
- Makefile: Linux `4.14.186` (`VERSION=4`, `PATCHLEVEL=14`, `SUBLEVEL=186`)
- A41 defconfig: `arch/arm64/configs/a41_defconfig`, with `CONFIG_LOCALVERSION=" Atrocious Kernel V:6"` and `CONFIG_SECURITY_SELINUX=y`.

This is a strong source match to the kernel banner in the supplied A41 log. It does not, by itself, prove that the exact booted Image was built from this exact commit.

## Source findings

| Area | Source evidence | Result |
|---|---|---|
| Policy version constants | `security/selinux/include/security.h:46-51` | `POLICYDB_VERSION_XPERMS_IOCTL=30`; `POLICYDB_VERSION_MAX=POLICYDB_VERSION_INFINIBAND=31` |
| Policy compatibility table | `security/selinux/ss/policydb.c:158` | Explicit compatibility entry for policy version 30 |
| AV table representation | `security/selinux/ss/avtab.h:42-76` | `AVTAB_XPERMS` and extended-permission data structures exist |
| Binary-policy parser | `security/selinux/ss/avtab.c:508-533` | Rejects xperms below version 30; parses ioctl xperm fields at supported versions |
| Binary-policy writer | `security/selinux/ss/avtab.c:603-625` | Serializes xperm specified/driver/bitmap fields |
| Runtime evaluation | `security/selinux/ss/services.c:605-694,975-1104` | Computes xperm driver and decision data at runtime |
| Kernel-reported policy version | `security/selinux/selinuxfs.c:352-363` | `/sys/fs/selinux/policyvers` returns `POLICYDB_VERSION_MAX`, i.e. 31 in this source |
| A41 config | `arch/arm64/configs/a41_defconfig:5678-5697` | SELinux enabled; no separate policy-version cap found in this defconfig |

## Interpretation against the captured boot

The ramoops says init capped policy version 30 to 29 because the *running kernel* reported no xperms support. However, this public A41 Atrocious V6 source branch contains ioctl-xperms policy version 30, parser/writer support, runtime evaluation, and exports max policy version 31 through selinuxfs.

Therefore, **do not add an xperms backport or merely raise a version constant to this source tree based on the current evidence**. The immediate discrepancy is between the captured kernel binary's reported capability (29) and the inspected A41 V6 source (31).

Most likely explanations to test, not yet proven:

1. The booted Image was not built from this exact source commit/tree, despite carrying the same local version string.
2. The source used for the binary differs from the public branch or has a local patch changing SELinux policy-version support.
3. The kernel image being booted is stale or is not the image the user expects.

The log and source audit do **not** identify which CIL file contributes the remaining ioctl-xperm rule. The compiler failure itself is still confirmed.

## Next decisive checks

1. Compare the exact build tree's `security/selinux/include/security.h`, `ss/avtab.c`, `ss/services.c`, and `selinuxfs.c` against the branch HEAD above.
2. Inspect the exact build output's `.config`, `vmlinux`, and Image provenance; confirm which image was packed/flashed.
3. If the device can boot a temporary recovery/kernel, read `/sys/fs/selinux/policyvers`. This source predicts `31`.
4. Only if the actual binary/source reports 29 should we patch that exact source; first locate the difference from this V6 source snapshot.
5. Separately find why the policy preparation step stripped 837 CIL xperm rules but left at least one ioctl-xperm rule. Do not delete policy rules blindly.
