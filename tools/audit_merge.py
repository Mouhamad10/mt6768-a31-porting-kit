#!/usr/bin/env python3
"""audit_merge.py <repo> <base_rev> <file>...
For files that existed in <base_rev> (the original 4.19 tree), list every line the
port ADDED that is not inside a preprocessor block guarded by a Samsung symbol.
Those are the lines a 3-way merge may have pulled in by accident."""
import difflib
import re
import subprocess
import sys

repo, base = sys.argv[1], sys.argv[2]
GUARD = re.compile(r"CONFIG_(FSCRYPT_SDP|SDP|DDAR|KNOX|FIVE|PROCA|SECURITY_DEFEX|SEC_|SAMSUNG|BATTERY_SAMSUNG|"
                   r"USB_ANDROID_SAMSUNG|USB_CONFIGFS_F_DM|USB_CONFIGFS_F_CONN|USB_CONFIGFS_F_SS_MON|USB_F_CONN|"
                   r"USB_F_SS_MON|USB_NOTIFY|USB_HOST_NOTIFY|MUIC|PDIC|SMCDSD)")
total = 0
for f in sys.argv[3:]:
    try:
        old = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (base, f)], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, check=True).stdout.decode(errors="replace").splitlines()
    except subprocess.CalledProcessError:
        continue
    new = open("%s/%s" % (repo, f), errors="replace").read().splitlines()
    # guarded line map for new file
    guarded, stack = [False] * len(new), []
    for i, l in enumerate(new):
        s = l.strip()
        if re.match(r"#\s*if", s):
            stack.append(bool(GUARD.search(s)))
        elif re.match(r"#\s*(else|elif)", s) and stack:
            stack[-1] = stack[-1] or bool(GUARD.search(s))
        guarded[i] = any(stack) or (re.match(r"#\s*(if|endif|else|elif)", s) is not None and bool(stack and stack[-1]))
        if re.match(r"#\s*endif", s) and stack:
            guarded[i] = guarded[i] or stack[-1]
            stack.pop()
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    bad = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("insert", "replace"):
            for j in range(j1, j2):
                if new[j].strip() and not guarded[j] and not re.match(r"#\s*(include|endif)", new[j].strip()):
                    bad.append((j + 1, new[j]))
    if bad:
        total += len(bad)
        print("== %s: %d unguarded added line(s)" % (f, len(bad)))
        for ln, l in bad[:25]:
            print("   %5d: %s" % (ln, l.rstrip()[:110]))
print("total unguarded added lines:", total)
