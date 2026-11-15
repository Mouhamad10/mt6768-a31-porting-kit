#!/usr/bin/env python3
# Boot-log triage for the MT6768 / A31 porting kit.
#
# Reads a kernel log (plain text, or a binary ramoops/pmsg dump - NUL bytes are
# handled by extracting printable strings), scans it against tools/boot-signatures.json,
# and prints a Markdown report: which known signatures fired, what each means, and
# where the fix is documented. Deterministic matcher - it names *known* problems and the
# existing fix. For a fatal fault with no known signature it says exactly that and never
# fabricates a patch.
#
# It also does two things a flat grep cannot:
#   * correlation - when a known COMBINATION fires in one boot (e.g. netbpfload failure +
#     bpfloader reboot), it raises a single root-cause callout instead of N loose warnings;
#   * collateral suppression - generic/teardown signatures are demoted once a specific cause
#     is identified, so the vold/mobicore/apexd shutdown noise does not masquerade as a cause.
#
# Usage:
#   python3 -I tools/triage-bootlog.py <logfile> [--sigs tools/boot-signatures.json] [--md report.md]
#
# Exit code: 0 always (advisory tool; the report carries the verdict).

import argparse
import json
import os
import re
import sys

SEV_ORDER = {"fatal": 0, "intentional": 1, "warning": 2, "info": 3}
SEV_EMOJI = {"fatal": "[FATAL]", "intentional": "[INTENTIONAL]", "warning": "[WARNING]", "info": "[INFO]"}
SUPPRESS_LINES = 25


def read_log(path):
    """Return (text, was_binary). If it looks binary (NUL in first 8 KB), extract
    printable strings (runs of >= 4 printable chars), like `strings`."""
    with open(path, "rb") as fh:
        raw = fh.read()
    if b"\x00" in raw[:8192]:
        runs = re.findall(rb"[\x20-\x7e\t]{4,}", raw)
        return "\n".join(r.decode("ascii", "replace") for r in runs), True
    return raw.decode("utf-8", "replace"), False


def line_offsets(text):
    offsets = [0]
    for m in re.finditer("\n", text):
        offsets.append(m.end())
    return offsets


def lineno_for(offsets, pos):
    lo, hi = 0, len(offsets) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if offsets[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def boot_progress(text):
    markers = [
        ("Freeing unused kernel memory", "kernel handed off to userspace (init started)"),
        ("init: init first stage started", "init first stage"),
        ("apexd: Marking APEXd as activated", "APEX activated - well into userspace boot"),
        ("Entered the Android system server", "system_server started"),
        ("Boot completed", "boot completed"),
    ]
    reached = [desc for probe, desc in markers if probe in text]
    rebooted = ("reboot: Restarting system" in text) or ("####Reboot start" in text)
    tail = reached[-1] if reached else "no userspace marker seen (may have died in the kernel)"
    if rebooted:
        tail += "  -> then the device REBOOTED (bootloop)"
    return tail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile")
    ap.add_argument("--sigs", default=os.path.join(os.path.dirname(__file__), "boot-signatures.json"))
    ap.add_argument("--md")
    args = ap.parse_args()

    with open(args.sigs, "r", encoding="utf-8") as fh:
        db = json.load(fh)
    sigs = db["signatures"]
    correlations = db.get("correlations", [])

    text, was_binary = read_log(args.logfile)
    offsets = line_offsets(text)

    # Pass 1: every occurrence (line, match) per signature.
    occ = {}
    for sig in sigs:
        rx = re.compile(sig["regex"], re.IGNORECASE | re.MULTILINE)
        occ[sig["id"]] = [(lineno_for(offsets, m.start()), m) for m in rx.finditer(text)]

    matched_ids = {sid for sid, lst in occ.items() if lst}

    # A non-fallback FATAL anywhere means the root cause is already named: demote every
    # fallback (generic catcher / teardown collateral) so it cannot pose as a rival cause.
    non_fallback_fatal = any(
        occ[s["id"]] and s["severity"] == "fatal" and not s.get("fallback") for s in sigs
    )
    # Lines of specific (non-fallback) intentional/fatal signatures, for proximity suppression
    # of a generic Oops that is really part of a named crash block (e.g. the forced reset).
    explainer_lines = [
        ln for s in sigs if not s.get("fallback") and s["severity"] in ("intentional", "fatal")
        for ln, _ in occ[s["id"]]
    ]

    hits, suppressed = [], []
    for sig in sigs:
        found = occ[sig["id"]]
        if not found:
            continue
        if sig.get("fallback"):
            if non_fallback_fatal:
                suppressed.append(_mk(sig, found, text, "a specific cause is already identified"))
                continue
            visible = [(ln, m) for (ln, m) in found
                       if not any(abs(ln - e) <= SUPPRESS_LINES for e in explainer_lines)]
            if not visible:
                suppressed.append(_mk(sig, found, text, "explained by a nearby specific signature"))
                continue
            hits.append(_mk(sig, visible, text, None))
        else:
            hits.append(_mk(sig, found, text, None))

    hits.sort(key=lambda h: (SEV_ORDER.get(h["sig"]["severity"], 9), h["line"]))
    fatals = [h for h in hits if h["sig"]["severity"] == "fatal"]
    intentional = [h for h in hits if h["sig"]["severity"] == "intentional"]

    fired_correlations = [c for c in correlations if all(i in matched_ids for i in c["all"])]

    if fatals:
        verdict = "FATAL fault(s) present - boot is blocked. See the fatal rows (and the root-cause callout, if any)."
    elif intentional:
        verdict = ("No self-inflicted kernel crash. The only BUG() is a DELIBERATE forced reset "
                   "(keys held). Re-capture without holding the keys to catch a real crash.")
    elif any(h["sig"]["severity"] == "warning" for h in hits):
        verdict = "No fatal fault matched. Warnings present (non-fatal) - boot most likely continued."
    else:
        verdict = "No known fatal or warning signature matched."

    out = ["# A31 boot-log triage", ""]
    out.append(f"- **Log:** `{os.path.basename(args.logfile)}`"
               + ("  _(binary ramoops/pmsg - decoded via string extraction)_" if was_binary else ""))
    out.append(f"- **Boot reached:** {boot_progress(text)}")
    out.append(f"- **Signatures matched:** {len(hits)} shown"
               + (f", {len(suppressed)} suppressed as collateral/explained" if suppressed else "")
               + f"  (fatal: {len(fatals)}, intentional: {len(intentional)})")
    out.append("")
    out.append(f"> **Verdict:** {verdict}")
    out.append("")

    if fired_correlations:
        out.append("### Correlated root cause")
        for c in fired_correlations:
            out.append(f"- **{' + '.join(c['all'])}** -> {c['note']}")
        out.append("")

    if not hits:
        out.append("No signature from the database matched this log. If the device still fails to "
                   "boot, the fault is not yet in the database: read the `pc :` / `lr :` and "
                   "`Call trace:` lines, identify the faulting driver, and add a signature to "
                   "`tools/boot-signatures.json` with the fix. This tool will not guess a patch.")
    else:
        out.append("| sev | signature | line | count | what it means / what to do |")
        out.append("|-----|-----------|------|-------|-----------------------------|")
        for h in hits:
            out.append(_row(h))
        out.append("")
        out.append("### Matched sample lines")
        out.append("```")
        for h in hits:
            out.append(f"L{h['line']}  [{h['sig']['severity']}] {h['sample']}")
        out.append("```")

    if suppressed:
        out.append("")
        out.append("### Suppressed as collateral / already-explained")
        out.append("_These matched but are consequences of a cause named above, or generic catchers "
                   "a specific signature overrides - listed so nothing is hidden, not counted as causes._")
        out.append("")
        for h in suppressed:
            out.append(f"- `{h['sig']['id']}` (x{h['count']}, first L{h['line']}) - {h['reason']}")

    out.append("")
    out.append("---")
    out.append("_Deterministic signature match against `tools/boot-signatures.json` (with same-boot "
               "correlation and collateral suppression). It names known faults and their documented "
               "fixes; it does not invent patches for unknown faults._")

    report = "\n".join(out)
    print(report)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(report + "\n")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n")
    return 0


def _mk(sig, found, text, reason):
    first_line, first = found[0]
    sample = text[first.start():first.end() + 120].splitlines()[0].strip()
    return {"sig": sig, "count": len(found), "line": first_line, "sample": sample[:200], "reason": reason}


def _row(h):
    s = h["sig"]
    fix = f"<br>**Fix:** `{s['fix']}`" if s.get("fix") else ""
    cell = f"{s['meaning']}<br>**Action:** {s['action']}{fix}".replace("|", "\\|")
    return (f"| {SEV_EMOJI.get(s['severity'], '')} | **{s['name']}** | {h['line']} "
            f"| {h['count']} | {cell} |")


if __name__ == "__main__":
    sys.exit(main())
