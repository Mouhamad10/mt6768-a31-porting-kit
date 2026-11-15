# Boot-log triage (signature matcher)

A boot log on this device is thousands of lines of MediaTek/Samsung noise with a handful of lines
that actually matter. This tool pulls out the lines that matter, says what each one means, and —
for problems we have already solved — points at the exact fix. It is how you turn a raw `last_kmsg`
/ ramoops dump into "here is what is wrong and here is the patch" in seconds instead of reading the
whole thing by hand.

## What it is (and what it is not)

- **It is a deterministic signature matcher.** [`tools/boot-signatures.json`](../tools/boot-signatures.json)
  is a list of known log signatures, each with a severity, what it means, what to do, and — where
  one exists — the patch or crash-database entry that fixes it.
  [`tools/triage-bootlog.py`](../tools/triage-bootlog.py) scans a log against that list and writes a
  report.
- **It is honest about the boundary.** For a fatal fault that matches a known signature, it names
  the documented fix. For a fatal fault with **no** known signature, it says exactly that and tells
  you how to analyse it (read the `pc:`/`lr:`/`Call trace:`, match the function to the driver
  source). **It does not fabricate a patch for an unknown crash** — that step is a human, or an AI
  reading the trace, deciding the fix and then adding a new signature here. A GitHub Action cannot
  invent a correct kernel source patch from a log, and this tool does not pretend to.

Think of it as the fast, reliable half of "feed a log, get the fix": the lookup is automated; the
first-time analysis of a genuinely new crash is not, and never silently guesses.

## Run it locally

```sh
python3 -I tools/triage-bootlog.py path/to/last_kmsg.txt
# binary ramoops/pmsg works too - NUL bytes are string-decoded automatically:
python3 -I tools/triage-bootlog.py path/to/pmsg-ramoops.txt
```

## Run it in CI

Actions → **"Triage a boot log (A31 / MT6768)"** → Run workflow. Give it either:

- `log_url` — a direct URL to a log (e.g. a paste/raw link, or a file uploaded somewhere), or
- `repo_path` — the path of a log you committed into this repo.

The report is printed to the job summary and uploaded as an artifact.

## Severities

| severity | meaning |
|----------|---------|
| **fatal** | boot-blocking fault. The device will not finish booting until this is fixed. |
| **intentional** | a `BUG()`/reset that fired on purpose (e.g. the Samsung forced-reset hook when you hold Vol-Down+Power). **Not a bug.** A generic "Oops" on the same line is suppressed so it does not masquerade as a real crash. |
| **warning** | real but non-fatal. Boot continues; a feature may be degraded. |
| **info** | harmless noise worth recognising so you stop chasing it. |

## Seeded signatures

The database ships with the crashes and warnings already seen on this device:

- the three bring-up kernel crashes — gpufreq efuse, EINT node, thermal sysrst — each linked to its
  [`crash-database.md`](crash-database.md) entry and fix;
- the Samsung **forced-reset** hook (so a captured ramdump is correctly read as "you held the keys",
  not a spontaneous crash);
- the **eBPF program load failure** (`NetBpfLoad: CRITICAL FAILURE …`) — an old-kernel-vs-new-Android
  gap, non-fatal despite its alarming wording;
- the Trustonic **TEE `tee_mmu_create`** warning, **RPMB** counter mismatch, the **exFAT/sdfat**
  mount path, and the harmless **PERFMON** capability note.

## Adding a signature (this is the real workflow)

When you hit a new crash the tool does not recognise:

1. Read the fault: the `pc :` / `lr :` function and the `Call trace:`.
2. Unpack the kernel to match the address to source if needed
   ([`tools/a31_bootimg.py`](../tools/a31_bootimg.py) + `gunzip` the `Image`).
3. Work out the fix (usually: an MTK driver dereferences an `ERR_PTR`/NULL because a DT node or
   nvmem/efuse cell is named differently on the A31 — make it fall back the way the 4.14 kernel did).
4. Add an entry to `tools/boot-signatures.json` with the signature regex, the meaning, the action,
   and the `fix` pointer. Now every future log with that fault is triaged automatically.

That is the loop that got UN1CA / One UI booting: predict and fix a whole *class* of crash from the
source, add the signature, move on — not one reboot per crash.
