#!/usr/bin/env python3
"""Check whether a GSI/system image still ships the sepolicy mapping .cil file a vendor needs.

This is the OTHER half of bring-up/crash-database.md#5 (cause #1, unconfirmed/compounding):
a vendor declares its platform sepolicy API level in /vendor/etc/selinux/plat_sepolicy_vers.txt.
The system side must ship a matching /system/etc/selinux/mapping/<that version>.0.cil to
translate the vendor's (older) policy into the platform's (newer) policy. If the GSI dropped
that mapping file (common when pairing an old vendor with a much newer GSI), init::SetupSelinux()
aborts during policy LOAD - independent of enforcing/permissive and independent of the
"stale partition" cause (cause #2), which tools/patch_vendor_fstab.sh handles.

This script does NOT patch anything - it only tells you whether the pairing can work, since
there is no safe automatic fix (pulling an old mapping file into a newer GSI is a manual,
per-case decision, not something to script blindly).

Usage:
  python3 tools/check_sepolicy_mapping.py <vendor_plat_sepolicy_vers e.g. 31.0> <system_image_or_mounted_dir>

For a system.img (ext4 or erofs), the image's OWN root is the content of /system (true for every
modern GSI - "system-as-root"), so this looks for ./etc/selinux/mapping at the image's root, not
system/etc/selinux/mapping.

Extraction support:
  - ext4   : via debugfs (no mount/root needed)
  - erofs  : via `fsck.erofs --extract=<tmp> --path=/etc/selinux/mapping <img>` (needs a
             reasonably recent erofs-utils; the gsi-port.yml workflow already installs it).
             If your erofs-utils is too old for --path, extract the image yourself and pass
             the extracted directory instead.
  - a directory : used as-is (e.g. you already mounted or extracted the image).
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MAPPING_RE = re.compile(r"^(\d+)\.0\.cil$")


def detect_fs(img: Path) -> str:
    with open(img, "rb") as f:
        data = f.read(2048)
    if data[1024:1028] == bytes.fromhex("e2e1f5e0"):
        return "erofs"
    if data[1080:1082] == bytes.fromhex("53ef"):
        return "ext4"
    return "unknown"


def list_mapping_ext4(img: Path) -> list[str]:
    out = subprocess.run(
        ["debugfs", "-R", "ls -l /etc/selinux/mapping", str(img)],
        capture_output=True, text=True,
    )
    names = []
    for line in out.stdout.splitlines():
        parts = line.split()
        if parts and MAPPING_RE.match(parts[-1]):
            names.append(parts[-1])
    return names


def list_mapping_erofs(img: Path) -> list[str]:
    if not shutil.which("fsck.erofs"):
        print("fsck.erofs not found (install erofs-utils) - cannot auto-extract an erofs image.",
              file=sys.stderr)
        return []
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(
            ["fsck.erofs", f"--extract={tmp}", "--path=/etc/selinux/mapping", str(img)],
            capture_output=True, text=True,
        )
        mapping_dir = Path(tmp) / "etc" / "selinux" / "mapping"
        if not mapping_dir.is_dir():
            print("could not extract /etc/selinux/mapping from this erofs image - your "
                  "erofs-utils may be too old for --path. stderr:\n" + r.stderr, file=sys.stderr)
            return []
        return [p.name for p in mapping_dir.iterdir() if MAPPING_RE.match(p.name)]


def list_mapping_dir(d: Path) -> list[str]:
    mapping_dir = d / "etc" / "selinux" / "mapping"
    if not mapping_dir.is_dir():
        return []
    return [p.name for p in mapping_dir.iterdir() if MAPPING_RE.match(p.name)]


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    vendor_vers = sys.argv[1].strip()
    if not re.match(r"^\d+(\.0)?$", vendor_vers):
        print(f"'{vendor_vers}' does not look like a plat_sepolicy_vers.txt value (e.g. 31.0)")
        sys.exit(1)
    major = vendor_vers.split(".")[0]
    needed = f"{major}.0.cil"

    target = Path(sys.argv[2])
    if not target.exists():
        print(f"not found: {target}")
        sys.exit(1)

    if target.is_dir():
        found = list_mapping_dir(target)
    else:
        fs = detect_fs(target)
        print(f"detected image type: {fs}")
        if fs == "ext4":
            found = list_mapping_ext4(target)
        elif fs == "erofs":
            found = list_mapping_erofs(target)
        else:
            print("could not identify filesystem (not ext4/erofs) - pass an extracted directory instead")
            sys.exit(1)

    print(f"vendor needs mapping file: {needed}")
    print(f"mapping files found on target ({len(found)}): {', '.join(sorted(found)) or '(none found)'}")
    if needed in found:
        print(f"OK: {needed} is present - this is not the (cause #1) sepolicy mapping gap.")
        sys.exit(0)
    else:
        print(f"MISSING: {needed} is NOT present on the target. This GSI/system cannot translate "
              f"this vendor's sepolicy API level {vendor_vers} - init::SetupSelinux() will fail to "
              f"load the merged policy regardless of enforcing/permissive "
              f"(crash-database.md#5, cause #1). Options: pull {needed} forward from an older "
              f"system image into this GSI's /etc/selinux/mapping/, or use a GSI build that still "
              f"ships it, or move the vendor forward if a newer vendor exists for this device.")
        sys.exit(2)


if __name__ == "__main__":
    main()
