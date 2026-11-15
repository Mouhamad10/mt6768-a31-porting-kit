#!/usr/bin/env python3
"""merge3.py <ours(fire)> <theirs(a31)> [base]
3-way merge of Samsung additions onto the 4.19 file, written in place over <ours>.
If base is not given it is derived from <theirs> with unifdef (Samsung SDP/DDAR/KNOX
symbols undefined). Conflicts are auto-resolved when one side equals base, or when
ours is fully contained in theirs (pure addition). Remaining ones are left marked."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ours, theirs = Path(sys.argv[1]), Path(sys.argv[2])
SYMS = ["CONFIG_FSCRYPT_SDP", "CONFIG_DDAR", "CONFIG_SDP", "CONFIG_SDP_KEY_DUMP",
        "CONFIG_FSCRYPT_SDP_KEY_DUMP", "CONFIG_KNOX_NCM", "CONFIG_FIVE", "CONFIG_PROCA",
        "CONFIG_SECURITY_DEFEX", "CONFIG_SEC_EXT", "CONFIG_BATTERY_SAMSUNG",
        "CONFIG_SMCDSD_PANEL", "CONFIG_USB_NOTIFY_LAYER", "CONFIG_MUIC_NOTIFIER",
        "CONFIG_PDIC_NOTIFIER", "CONFIG_SEC_DEBUG", "CONFIG_SAMSUNG_PRODUCT_SHIP"]
import os
SYMS += [s for s in os.environ.get("MERGE3_SYMS", "").split() if s]
with tempfile.TemporaryDirectory() as td:
    if len(sys.argv) > 3:
        base = Path(sys.argv[3])
    else:
        base = Path(td) / "base"
        r = subprocess.run(["unifdef"] + ["-U" + s for s in SYMS] + [str(theirs)],
                           stdout=subprocess.PIPE)
        base.write_bytes(r.stdout)
    subprocess.run(["git", "merge-file", "--diff3", "-L", "ours", "-L", "base", "-L", "theirs",
                    str(ours), str(base), str(theirs)])

s = ours.read_text(errors="surrogateescape")
pat = re.compile(r"^<<<<<<< ours\n(.*?)^\|\|\|\|\|\|\| base\n(.*?)^=======\n(.*?)^>>>>>>> theirs\n", re.S | re.M)


def n(t):
    return [re.sub(r"\s+", " ", l).strip() for l in t.splitlines() if l.strip()]


left = 0


def res(m):
    global left
    o, b, t = m.group(1), m.group(2), m.group(3)
    if n(o) == n(b):
        return t
    if n(t) == n(b):
        return o
    no, nt = n(o), n(t)
    if not no:
        return t
    for k in range(len(nt) - len(no) + 1):
        if nt[k:k + len(no)] == no:
            return t
    left += 1
    return m.group(0)


s = pat.sub(res, s)
ours.write_text(s, errors="surrogateescape")
print("%s: %d unresolved conflict(s)" % (ours.name, left))
sys.exit(1 if left else 0)
