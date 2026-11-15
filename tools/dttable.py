#!/usr/bin/env python3
"""dttable.py wrap <in.dtb> <out.bin> [--like <stock_wrapped_dtb>]
           unwrap <wrapped> <out.dtb>
Android DT table (magic 0xd7b7ab1e) with one entry, as in the A31 boot image dtb.
--like copies page_size/version and the entry id/rev/custom fields from the stock blob."""
import struct
import sys
from pathlib import Path

MAGIC = 0xd7b7ab1e


def read_tbl(b):
    hdr = struct.unpack(">8I", b[:32])
    assert hdr[0] == MAGIC, "not a DT table"
    ent = struct.unpack(">8I", b[hdr[5]:hdr[5] + 32])
    return hdr, ent


cmd = sys.argv[1]
if cmd == "unwrap":
    b = Path(sys.argv[2]).read_bytes()
    hdr, ent = read_tbl(b)
    Path(sys.argv[3]).write_bytes(b[ent[1]:ent[1] + ent[0]])
    print("entry: size=%d off=%d id=%#x rev=%#x custom=%s" % (ent[0], ent[1], ent[2], ent[3], ent[4:]))
    sys.exit(0)

dtb = Path(sys.argv[2]).read_bytes()
assert dtb[:4] == b"\xd0\x0d\xfe\xed", "input is not a dtb"
page, version, eid, erev, custom = 2048, 0, 0, 0, (0, 0, 0, 0)
if "--like" in sys.argv:
    sb = Path(sys.argv[sys.argv.index("--like") + 1]).read_bytes()
    h, e = read_tbl(sb)
    page, version, eid, erev, custom = h[6], h[7], e[2], e[3], e[4:8]
total = 32 + 32 + len(dtb)
out = struct.pack(">8I", MAGIC, total, 32, 32, 1, 32, page, version)
out += struct.pack(">8I", len(dtb), 64, eid, erev, *custom)
out += dtb
Path(sys.argv[3]).write_bytes(out)
print("wrapped %d-byte dtb -> %s (%d bytes)" % (len(dtb), sys.argv[3], len(out)))
