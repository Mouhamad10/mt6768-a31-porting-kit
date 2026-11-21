# Boot-log triage (signature matcher)

A boot log on this device is thousands of lines of MediaTek/Samsung noise with a handful of lines
that actually matter. This tool pulls out the lines that matter, says what each one means, and —
for problems we have already solved — points at the exact fix. It turns a raw `last_kmsg` / ramoops
dump into "here is what is wrong and here is the fix" in seconds instead of reading the whole thing.

## What it is (and what it is not)

- **It is a deterministic signature matcher.** [`tools/boot-signatures.json`](../tools/boot-signatures.json)
  is a list of known log signatures, each with a severity, what it means, what to do, and — where
  one exists — the patch or crash-database entry that fixes it.
  [`tools/triage-bootlog.py`](../tools/triage-bootlog.py) scans a log against that list and writes a
  report.
- **It does two things a flat grep cannot:**
  - **Same-boot correlation.** Some faults are only fatal in combination. A `netbpfload` BPF-load
    failure is survivable alone, but together with a `reboot,bpfloader-failed` in the *same* boot it
    is the bootloop. When a known combination fires, the report raises one **root-cause callout**
    instead of a scatter of loose warnings.
  - **Collateral suppression.** Once a specific cause is named, the generic catchers and the
    service deaths from the *already-committed* reboot teardown (vold, mobicore, apexd flush_work)
    are demoted to a "suppressed" list so they cannot masquerade as rival causes.
- **It is honest about the boundary.** For a fatal fault that matches a known signature, it names the
  documented fix. For a fatal fault with **no** known signature, it says exactly that and tells you
  how to analyse it. **It does not fabricate a patch for an unknown crash** — that step is a human,
  or an AI reading the trace, deciding the fix and then adding a new signature. A GitHub Action
  cannot invent a correct kernel source patch from a log, and this tool does not pretend to.

## The headline finding: why a modern Android bootloops on the 4.14 kernel

The clearest real case the database was built from (an A34 system/vendor booted on the A31):

```
netbpfload: non-optional program schedcls_tether_downstream6_ether failed to load
NetBpfLoad: === CRITICAL FAILURE LOADING BPF PROGRAMS ===
init: Service bpfloader (pid 998) exited with status 38 waiting took 20.035 seconds
init: Service bpfloader has 'reboot_on_failure' option and failed, shutting down system.
init: ####Reboot start, reason: reboot,bpfloader-failed   ->   sec_reboot (0, bpfloader-failed)
```

The 4.14 kernel's eBPF support cannot load the newer Android tethering APEX's BPF programs. The
`bpfloader` init service is declared `reboot_on_failure`, so init **reboots the device** — a
guaranteed bootloop. The `system_server` ClatCoordinator `SIGABRT` (in the pmsg/tombstone ring) is
the user-space face of the *same* missing clat BPF maps. **Decisive proof it is the flag, not the
warning:** the working 4.14 ROM prints the identical `CRITICAL FAILURE` line and still boots, because
its `bpfloader` is not `reboot_on_failure`.

This is the strongest evidence that a **newer kernel base (5.10+ GKI)** is the real fix for a modern
Android userspace — not something patchable on 4.14. The only 4.14 stopgap is to drop
`reboot_on_failure` from the `bpfloader` `.rc`, which lets the device boot with broken tethering/clat
rather than bricking.

## Run it locally

```sh
python3 -I tools/triage-bootlog.py path/to/last_kmsg.txt
# binary ramoops/pmsg works too - NUL bytes are string-decoded automatically:
python3 -I tools/triage-bootlog.py path/to/pmsg-ramoops.txt
```

## Run it in CI

Actions → **"Triage a boot log (A31 / MT6768)"** → Run workflow. Give it either `log_url` (a direct
URL to a log) or `repo_path` (a log committed in this repo). The report is printed to the job summary
and uploaded as an artifact.

## Severities

| severity | meaning |
|----------|---------|
| **fatal** | boot-blocking. The device will not finish booting until this is fixed. |
| **intentional** | a `BUG()`/reset that fired on purpose (e.g. the Samsung forced-reset hook when you hold Vol-Down+Power). **Not a bug.** |
| **warning** | real but non-fatal. Boot continues; a feature may be degraded. |
| **info** | harmless noise / a marker worth recognising so you stop chasing it. |

A signature marked `fallback` is a generic catcher or teardown-collateral line: it is suppressed when
a specific cause is already identified, and listed under "suppressed" so nothing is hidden.

## Seeded signatures

- **The eBPF bootloop** (headline above): `bpfloader-reboot` (fatal) + `netbpf-load-fail` (warning) +
  `clat-coordinator-abort` (fatal symptom), tied together by a correlation rule.
- the three 4.19 bring-up kernel crashes — gpufreq efuse, EINT node, thermal sysrst — each linked to
  its [`crash-database.md`](crash-database.md) entry and fix;
- the Samsung **forced-reset** hook (so a captured ramdump is read as "you held the keys", not a
  spontaneous crash);
- the **vendor audio-HAL SIGSEGV** (`mtk-audio-hal-segv`) — an A34/A32-vendor-on-A31 mismatch, breaks
  audio, not boot-fatal;
- the generic **reboot-reason catcher** and **service-exit-timeout** (so any *future* reboot names its
  culprit even without a specific signature), the **teardown collateral** (vold/mobicore/apexd), and
  the TEE/RPMB/exFAT/PERFMON/unprivileged-bpf markers.

## Adding a signature (the real workflow)

When you hit a new crash the tool does not recognise:

1. Read the fault: the `pc :` / `lr :` function and the `Call trace:`, or the init reboot reason.
2. If kernel-side, unpack the kernel to match the address to source
   ([`tools/a31_bootimg.py`](../tools/a31_bootimg.py) + `gunzip` the `Image`).
3. Work out the fix (kernel crash → usually an MTK driver dereferencing an `ERR_PTR`/NULL because a
   DT node or nvmem/efuse cell is named differently on the A31; userspace → often an old-kernel vs
   new-Android capability gap with no patch, where the fix is a newer kernel).
4. Add an entry to `tools/boot-signatures.json` (and a `correlations` rule if it is only fatal in
   combination). Now every future log with that fault is triaged automatically.

- The A41-specific **ioctl-xperms policy compile failure** (`selinux-xperms-policy-compile-fail`) is fatal: secilc cannot serialize a remaining ioctl-xperm rule when init caps the target policy version to 29. The generic policy-load abort is a fallback. See [`a41-selinux-xperms.md`](a41-selinux-xperms.md).

- The A41 **missing logical-partition DM status** (`logical-partition-dm-status-missing`) is recorded as a warning only. It is deliberately not correlated with the ioctl-xperms compiler failure: the supplied A41 log does not prove a causal link between them.
