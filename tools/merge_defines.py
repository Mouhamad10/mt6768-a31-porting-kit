#!/usr/bin/env python3
"""merge_defines.py <target.h> <source.h>
Insert every '#define NAME ...' that exists in source.h but not in target.h,
right after the nearest preceding source define that target.h already has.
Existing target defines are never changed (values in conflict are reported)."""
import re
import sys
from pathlib import Path

tgt_p, src_p = Path(sys.argv[1]), Path(sys.argv[2])
tgt = tgt_p.read_text().splitlines()
src = src_p.read_text().splitlines()
DEF = re.compile(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\b(.*)$")


def names(lines):
    out = {}
    for i, l in enumerate(lines):
        m = DEF.match(l)
        if m and m.group(1) not in out:
            out[m.group(1)] = (i, m.group(2).split("/*")[0].strip())
    return out


tn = names(tgt)
added, conflicts, prev = 0, [], None
seen = set()
for l in src:
    m = DEF.match(l)
    if not m:
        continue
    n, val = m.group(1), m.group(2).split("/*")[0].strip()
    if n in seen:
        continue
    seen.add(n)
    if n in tn:
        if tn[n][1] != val and val and tn[n][1]:
            conflicts.append("%s: target=%s source=%s" % (n, tn[n][1], val))
        prev = n
        continue
    # insert after prev's current position in tgt
    tn_now = names(tgt)
    pos = tn_now[prev][0] + 1 if prev in tn_now else len(tgt)
    # skip past multi-line define continuation
    while pos < len(tgt) and tgt[pos - 1].rstrip().endswith("\\"):
        pos += 1
    tgt.insert(pos, l)
    added += 1
    prev = n
    tn = names(tgt)

tgt_p.write_text("\n".join(tgt) + "\n")
print("%s: +%d defines from %s" % (tgt_p.name, added, src_p.name))
for c in conflicts:
    print("  kept target value -", c)
