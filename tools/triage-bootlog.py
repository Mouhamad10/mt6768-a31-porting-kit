#!/usr/bin/env python3
# Boot-log triage for the MT6768 / A31 porting kit.
#
# Reads a kernel log (plain text, or a binary ramoops/pmsg dump - NUL bytes are
# handled by extracting printable strings), scans it against tools/boot-signatures.json,
# and prints a Markdown report: which known signatures fired, what each means, and
# where the fix is documented. It is a DETERMINISTIC matcher - it tells you which
# *known* problems are present and names the existing fix. For a fatal fault with no
# known signature it says exactly that and points you at how to analyse it; it never
# fabricates a patch.
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


def read_log(path):
    """Return the log as text. If it looks binary (NUL in first 8 KB), extract
    printable strings (runs of >= 4 printable chars), like `strings`."""
    with open(path, "rb") as fh:
        raw = fh.read()
    head = raw[:8192]
    if b"\x00" in head:
        # binary ramoops/pmsg: pull printable runs out
        runs = re.findall(rb"[\x20-\x7e\t]{4,}", raw)
        text = "\n".join(r.decode("ascii", "replace") for r in runs)
        return text, True
    return raw.decode("utf-8", "replace"), False


def line_index(text):
    """Map character offset -> 1-based line number (cheap, for small logs)."""
    offsets = [0]
    for m in re.finditer("\n", text):
        offsets.append(m.end())
    return offsets


def lineno_for(offsets, pos):
    # binary search
    lo, hi = 0, len(offsets) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if offsets[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def boot_progress(text):
    """Cheap heuristic: how far did boot get?"""
    markers = [
        ("Freeing unused kernel memory", "kernel handed off to userspace (init started)"),
        ("init: init first stage started", "init first stage"),
        ("init: Service 'apexd'", "apexd / second stage"),
        ("apexd: Marking APEXd as activated", "APEX activated - well into userspace boot"),
        ("Starting Android", "Android runtime starting"),
        ("Boot completed", "boot completed"),
    ]
    reached = [desc for probe, desc in markers if probe in text]
    return reached[-1] if reached else "no userspace marker seen (may have died in the kernel)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile")
    ap.add_argument("--sigs", default=os.path.join(os.path.dirname(__file__), "boot-signatures.json"))
    ap.add_argument("--md", help="also write the Markdown report to this file")
    args = ap.parse_args()

    with open(args.sigs, "r", encoding="utf-8") as fh:
        db = json.load(fh)
    sigs = db["signatures"]

    text, was_binary = read_log(args.logfile)
    offsets = line_index(text)

    # First pass: record every occurrence (as line numbers) of each signature.
    occ = {}  # id -> list of (line, matchobj)
    for sig in sigs:
        rx = re.compile(sig["regex"], re.IGNORECASE | re.MULTILINE)
        occ[sig["id"]] = [(lineno_for(offsets, m.start()), m) for m in rx.finditer(text)]

    # "Explainer" lines: every occurrence of a specific signature (intentional, or a
    # fatal that is NOT the generic fallback). A generic fallback fatal that lands within
    # SUPPRESS_LINES of an explainer is the SAME crash block already named by that
    # explainer (e.g. the Oops line of a deliberate forced reset), so it must not be
    # counted as an independent fatal.
    SUPPRESS_LINES = 25
    explainer_lines = []
    for sig in sigs:
        if sig.get("fallback"):
            continue
        if sig["severity"] in ("intentional", "fatal"):
            explainer_lines += [ln for ln, _ in occ[sig["id"]]]

    hits = []
    for sig in sigs:
        found = occ[sig["id"]]
        if sig.get("fallback"):
            found = [(ln, m) for (ln, m) in found
                     if not any(abs(ln - e) <= SUPPRESS_LINES for e in explainer_lines)]
        if not found:
            continue
        first_line, first = found[0]
        sample = text[first.start():first.end() + 120].splitlines()[0].strip()
        hits.append({
            "sig": sig,
            "count": len(found),
            "line": first_line,
            "sample": sample[:200],
        })

    hits.sort(key=lambda h: (SEV_ORDER.get(h["sig"]["severity"], 9), h["line"]))

    fatals = [h for h in hits if h["sig"]["severity"] == "fatal"]
    intentional = [h for h in hits if h["sig"]["severity"] == "intentional"]

    # Verdict
    if fatals:
        verdict = "FATAL kernel fault(s) present - boot is blocked. See the fatal rows below."
    elif intentional and not fatals:
        verdict = ("No self-inflicted kernel crash. The only BUG() is a DELIBERATE forced reset "
                   "(keys held). If you were chasing a boot crash, re-capture without holding the keys.")
    elif any(h["sig"]["severity"] == "warning" for h in hits):
        verdict = "No fatal fault matched. Warnings present (non-fatal) - boot most likely continued."
    else:
        verdict = "No known fatal or warning signature matched."

    out = []
    out.append("# A31 boot-log triage")
    out.append("")
    out.append(f"- **Log:** `{os.path.basename(args.logfile)}`"
               + ("  _(binary ramoops/pmsg - decoded via string extraction)_" if was_binary else ""))
    out.append(f"- **Boot reached:** {boot_progress(text)}")
    out.append(f"- **Signatures matched:** {len(hits)}  "
               f"(fatal: {len(fatals)}, intentional: {len(intentional)})")
    out.append("")
    out.append(f"> **Verdict:** {verdict}")
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
            s = h["sig"]
            fix = ""
            if s.get("fix"):
                fix = f"<br>**Fix:** `{s['fix']}`"
            cell = f"{s['meaning']}<br>**Action:** {s['action']}{fix}"
            cell = cell.replace("|", "\\|")
            out.append(f"| {SEV_EMOJI.get(s['severity'],'')} | **{s['name']}** | {h['line']} "
                       f"| {h['count']} | {cell} |")
        out.append("")
        out.append("### Matched sample lines")
        out.append("```")
        for h in hits:
            out.append(f"L{h['line']}  [{h['sig']['severity']}] {h['sample']}")
        out.append("```")

    out.append("")
    out.append("---")
    out.append("_Deterministic signature match against `tools/boot-signatures.json`. "
               "It names known faults and their documented fixes; it does not invent patches "
               "for unknown faults._")

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


if __name__ == "__main__":
    sys.exit(main())
