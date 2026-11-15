#!/usr/bin/env python3
"""a31_bootimg.py - unpack / repack Android boot images (header v0-v2), A31 layout.

  a31_bootimg.py info   <img>
  a31_bootimg.py unpack <img> <outdir>
  a31_bootimg.py repack <img> <out.img> [--kernel F] [--ramdisk F] [--dtb F] [--dtbo F] [--cmdline S]

repack keeps every field of the source header and only replaces the given parts;
the id is recomputed like AOSP mkbootimg (SHA1 over each part + its size)."""
import argparse
import hashlib
import struct
import sys
from pathlib import Path

MAGIC = b"ANDROID!"


def align(n, p):
    return (n + p - 1) // p * p


def parse(d):
    if d[:8] != MAGIC:
        sys.exit("not an Android boot image")
    (ks, ka, rs, ra, ss, sa, ta, ps, hv, osv) = struct.unpack_from("<10I", d, 8)
    h = dict(kernel_size=ks, kernel_addr=ka, ramdisk_size=rs, ramdisk_addr=ra,
             second_size=ss, second_addr=sa, tags_addr=ta, page_size=ps,
             header_version=hv, os_version=osv)
    h["name"] = d[48:64]
    h["cmdline"] = d[64:576]
    h["id"] = d[576:608]
    h["extra_cmdline"] = d[608:1632]
    off = 1632
    if hv >= 1:
        h["recovery_dtbo_size"], h["recovery_dtbo_offset"], h["header_size"] = struct.unpack_from("<IQI", d, off)
        off += 16
    if hv >= 2:
        h["dtb_size"], h["dtb_addr"] = struct.unpack_from("<IQ", d, off)
        off += 12
    ps = h["page_size"]
    parts, pos = {}, ps
    for name, size in [("kernel", ks), ("ramdisk", rs), ("second", ss),
                       ("recovery_dtbo", h.get("recovery_dtbo_size", 0)),
                       ("dtb", h.get("dtb_size", 0))]:
        parts[name] = d[pos:pos + size]
        pos += align(size, ps)
    h["_end"] = pos
    return h, parts


def build(h, parts):
    ps = h["page_size"]
    hv = h["header_version"]
    sha = hashlib.sha1()
    order = ["kernel", "ramdisk", "second"] + (["recovery_dtbo"] if hv >= 1 else []) + (["dtb"] if hv >= 2 else [])
    for n in order:
        sha.update(parts[n])
        sha.update(struct.pack("<I", len(parts[n])))
    img_id = sha.digest().ljust(32, b"\0")
    hdr = bytearray(MAGIC)
    hdr += struct.pack("<10I", len(parts["kernel"]), h["kernel_addr"], len(parts["ramdisk"]), h["ramdisk_addr"],
                       len(parts["second"]), h["second_addr"], h["tags_addr"], ps, hv, h["os_version"])
    hdr += h["name"] + h["cmdline"] + img_id + h["extra_cmdline"]
    if hv >= 1:
        dtbo_off = 0
        if parts["recovery_dtbo"]:
            dtbo_off = ps + align(len(parts["kernel"]), ps) + align(len(parts["ramdisk"]), ps) + align(len(parts["second"]), ps)
        hdr += struct.pack("<IQI", len(parts["recovery_dtbo"]), dtbo_off, h["header_size"])
    if hv >= 2:
        hdr += struct.pack("<IQ", len(parts["dtb"]), h["dtb_addr"])
    out = bytearray(hdr.ljust(ps, b"\0"))
    for n in order:
        out += parts[n].ljust(align(len(parts[n]), ps), b"\0")
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["info", "unpack", "repack"])
    ap.add_argument("img")
    ap.add_argument("out", nargs="?")
    for p in ["kernel", "ramdisk", "dtb", "dtbo"]:
        ap.add_argument("--" + p)
    ap.add_argument("--cmdline")
    a = ap.parse_args()
    d = Path(a.img).read_bytes()
    h, parts = parse(d)
    if a.cmd == "info":
        for k, v in h.items():
            if k.startswith("_"):
                continue
            if isinstance(v, bytes):
                v = v.rstrip(b"\0").decode(errors="replace")
            print("%-20s %s" % (k, hex(v) if isinstance(v, int) and k.endswith("addr") else v))
        print("%-20s %d bytes (image %d)" % ("parts end", h["_end"], len(d)))
        return
    if a.cmd == "unpack":
        o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
        for n, b in parts.items():
            if b:
                (o / n).write_bytes(b)
        (o / "cmdline").write_bytes(h["cmdline"].rstrip(b"\0"))
        print("unpacked to", o)
        return
    for n, key in [("kernel", "kernel"), ("ramdisk", "ramdisk"), ("dtb", "dtb"), ("recovery_dtbo", "dtbo")]:
        f = getattr(a, key)
        if f:
            parts[n] = Path(f).read_bytes()
    if a.cmdline is not None:
        c = a.cmdline.encode()
        if len(c) > 511:
            sys.exit("cmdline too long")
        h["cmdline"] = c.ljust(512, b"\0")
    img = build(h, parts)
    tail = d[h["_end"]:]  # keep anything appended after the parts (e.g. AVB footer / SEANDROID)
    Path(a.out).write_bytes(img + tail)
    print("wrote", a.out, len(img + tail), "bytes; sha1 id", hashlib.sha1(img[:0]).hexdigest()[:0] or img[576:596].hex())


if __name__ == "__main__":
    main()
