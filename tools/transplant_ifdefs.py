#!/usr/bin/env python3
"""transplant_ifdefs.py <target.c> <source.c> <regex>
Copy every top-level '#if...' block whose condition matches <regex> from source into
target, if the target does not already contain it.
 - plain block: inserted after the closest preceding context line found exactly once
   in the target (falls back to the following context line, inserting before it).
 - block with '#else': the '#else' branch is the original code; it is located in the
   target and replaced by the whole block.
Reports every block it could not place, so it can be done by hand."""
import re
import sys
from pathlib import Path

tgt_p, src_p, rx = Path(sys.argv[1]), Path(sys.argv[2]), re.compile(sys.argv[3])
T = tgt_p.read_text(errors="surrogateescape").split("\n")
S = src_p.read_text(errors="surrogateescape").split("\n")


def blocks(lines):
    i, out = 0, []
    while i < len(lines):
        l = lines[i].strip()
        if re.match(r"#\s*if", l) and rx.search(l):
            depth, j, else_at = 0, i, None
            while j < len(lines):
                s = lines[j].strip()
                if re.match(r"#\s*if", s):
                    depth += 1
                elif re.match(r"#\s*endif", s):
                    depth -= 1
                    if depth == 0:
                        break
                elif re.match(r"#\s*(else|elif)", s) and depth == 1 and else_at is None:
                    else_at = j
                j += 1
            out.append((i, j, else_at))
            i = j + 1
        else:
            i += 1
    return out


def norm(l):
    return re.sub(r"\s+", " ", l.strip())


def find_unique(seq, needle_lines):
    n = [norm(x) for x in needle_lines]
    hits = []
    for k in range(len(seq) - len(n) + 1):
        if all(norm(seq[k + q]) == n[q] for q in range(len(n))):
            hits.append(k)
    return hits


placed, failed = 0, []
for (a, b, e) in reversed(blocks(S)):
    blk = S[a:b + 1]
    if find_unique(T, blk):
        continue  # already there
    if e is not None:
        orig = [x for x in S[e + 1:b] if x.strip()]
        if orig:
            # locate original code as a contiguous run of non-empty lines in target
            Tn = [(k, x) for k, x in enumerate(T) if x.strip()]
            seq = [x for _, x in Tn]
            hits = find_unique(seq, orig)
            if len(hits) == 1:
                k0 = Tn[hits[0]][0]
                k1 = Tn[hits[0] + len(orig) - 1][0]
                T[k0:k1 + 1] = blk
                placed += 1
                continue
        failed.append((a + 1, "else-branch not found uniquely", blk[0]))
        continue
    done = False
    for back in range(1, 8):  # preceding context
        k = a - back
        if k < 0:
            break
        if not S[k].strip():
            continue
        ctx = S[k:a]
        ctx = [x for x in ctx if x.strip()]
        hits = find_unique(T, [S[k]])
        if len(hits) == 1:
            T[hits[0] + 1:hits[0] + 1] = blk
            placed += 1
            done = True
        break
    if done:
        continue
    for fwd in range(1, 8):  # following context
        k = b + fwd
        if k >= len(S):
            break
        if not S[k].strip():
            continue
        hits = find_unique(T, [S[k]])
        if len(hits) == 1:
            T[hits[0]:hits[0]] = blk
            placed += 1
            done = True
        break
    if not done:
        failed.append((a + 1, "no unique context", blk[0]))

tgt_p.write_text("\n".join(T), errors="surrogateescape")
print("%s: placed %d block(s)" % (tgt_p, placed))
for ln, why, first in failed:
    print("  FAILED src line %d (%s): %s" % (ln, why, first.strip()))
