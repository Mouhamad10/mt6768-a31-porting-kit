# Automation (GitHub Actions) — what's real vs. what isn't

This answers a natural wish: *"upload a kernel/log and have CI hand me back a correct patch and a
flashable ZIP."* Part of that is solid and worth building; part of it is not reliable today. Here is
the honest split, and what this repo actually ships.

## Layer 1 — deterministic CI (real, reliable, shipped here)

A computer can do these exactly and repeatably, no AI involved:

- **Build a kernel → flashable ZIP.** Clone a MT6768 kernel, apply a patch stack, build `Image.gz`,
  package it with **AnyKernel3** into a ZIP you flash in TWRP. AnyKernel3 swaps only the kernel into
  the existing boot image **on the device**, so no stock `boot.img` needs to be uploaded.
  → [`.github/workflows/build-kernel.yml`](../.github/workflows/build-kernel.yml).
- **Generate a patch (diff).** "Make a patch from a kernel" only means *diff against a base*. Given a
  base tree+commit and a modified tree, `git format-patch` produces a clean, correct patch series.
  This is deterministic. (Vendor/system work the same way: diff the modified files against the stock
  extraction.) → planned `make-patch.yml`.
- **Repack / package.** boot/recovery/vendor repack, AnyKernel3 zips, OTA-style zips — all exact.

This layer is genuinely useful and is the backbone. It does **not** invent fixes; it builds and
packages what you give it.

## Layer 2 — AI triage (useful as an assistant, NOT an autopilot)

The wish *"upload a non-working system's log, AI emits a guaranteed-correct patch + flashable ZIP"*
is **not reliable** today, for concrete reasons:

- A patch that **compiles is not a patch that boots.** This whole project needed the physical device
  in the loop and multiple reboots to confirm each fix; some crashes are still open. CI has no A31 to
  boot on, so it cannot verify a fix.
- **System/vendor** failures (props, overlays, HAL/SELinux, missing libs) are even more device- and
  ROM-specific than kernel crashes; a log rarely contains enough to synthesize a *correct* change.
- An LLM will happily produce a **plausible-but-wrong** patch. Flashing unverified patches risks
  bootloops, bricks, or data loss.

What **is** realistic and worth building: an **AI-assisted triage** that, when you open an issue with
a `last_kmsg` / logcat attached:

1. Greps the log against the known-signature table in
   [`../bring-up/crash-database.md`](../bring-up/crash-database.md) — if it matches a known crash,
   it posts the exact cause + fix. This part is deterministic and already backed by this repo.
2. If an API key secret is configured and the signature is unknown, it asks a model to **draft a
   candidate analysis and patch**, posted as a comment clearly labelled
   **"CANDIDATE — review and test on the device, do NOT flash blindly."**

So the honest product is: **deterministic build/package + a knowledge-base triage that drafts
candidates for a human to review and test.** Not an auto-fixer that flashes guaranteed patches.

## How the pieces fit your workflow

1. You push a kernel change (or point the build workflow at any MT6768 kernel + ref).
2. CI builds it and hands you a **TWRP-flashable AnyKernel3 ZIP** as an artifact.
3. You flash it (recovery first, per [`../bring-up/recovery-test-method.md`](../bring-up/recovery-test-method.md)),
   and if it crashes you upload `last_kmsg` to an issue.
4. Triage matches it against the crash database (instant known-cause answer) or drafts a candidate.
5. You, or an AI session with the device attached, apply + test the candidate — then it becomes a new
   entry in the crash database, and the next person gets it for free.

That loop is real and compounding. The "no human, guaranteed correct, auto-flashed" version is the
part to treat as aspiration, not a feature.
