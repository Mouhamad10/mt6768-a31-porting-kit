#!/usr/bin/env bash
# Read-only audit of SELinux ioctl-xperms support in a kernel source tree.
set -Eeuo pipefail

ROOT="${1:-.}"
ROOT="$(cd "$ROOT" && pwd)"
SELINUX="$ROOT/security/selinux"

if [[ ! -d "$SELINUX" ]]; then
  echo "ERROR: '$ROOT' does not look like a kernel source tree (missing security/selinux)." >&2
  exit 2
fi

section() { printf '\n===== %s =====\n' "$1"; }
show_matches() {
  local label="$1"; shift
  section "$label"
  local found=0
  for f in "$@"; do
    [[ -f "$f" ]] || continue
    echo "--- ${f#$ROOT/}"
    if grep -nE 'POLICYDB_VERSION_(XPERMS_IOCTL|MAX)|CONFIG_SECURITY_SELINUX_POLICYDB_VERSION_MAX|AVTAB_XPERMS|xperms|extended_perms|security_compute_xperms_decision|sel_read_policyvers' "$f" | head -n 80; then
      found=1
    else
      echo "(no matching markers)"
    fi
  done
  [[ $found -eq 1 ]] || true
}

show_matches "Policy version constants" \
  "$SELINUX/include/security.h" \
  "$SELINUX/ss/policydb.h" \
  "$SELINUX/ss/policydb.c"

show_matches "AV table / binary policy xperms implementation" \
  "$SELINUX/ss/avtab.h" \
  "$SELINUX/ss/avtab.c" \
  "$SELINUX/ss/policydb.c"

show_matches "Runtime xperms evaluation" \
  "$SELINUX/ss/services.h" \
  "$SELINUX/ss/services.c" \
  "$SELINUX/avc.c"

show_matches "Kernel-reported policy version interface" \
  "$SELINUX/selinuxfs.c"

section "Kconfig and built configuration caps"
if [[ -f "$ROOT/.config" ]]; then
  grep -nE 'CONFIG_SECURITY_SELINUX|POLICYDB_VERSION' "$ROOT/.config" || true
else
  echo "No .config at source root; checking common defconfig locations."
  find "$ROOT/arch" -type f \( -name '*defconfig' -o -name '*_defconfig' \) -print0 2>/dev/null |
    xargs -0 -r grep -nHE 'CONFIG_SECURITY_SELINUX|POLICYDB_VERSION' || true
fi

section "Current device policy version (run separately on booted rooted device)"
echo 'adb shell su -c "cat /sys/fs/selinux/policyvers 2>/dev/null || cat /sys/fs/selinux/policyvers"'
echo 'Expected for ioctl-xperm format: >= 30, but only advertise 30 after the source audit proves full support.'

echo
cat <<'NOTE'
Interpretation:
- POLICYDB_VERSION_XPERMS_IOCTL=30 plus complete AVTAB_XPERMS parsing/writing and runtime evaluation:
  candidate for exposing policy version 30 after a build and policy-load test.
- Constant absent or implementation paths absent/incomplete:
  do NOT merely raise POLICYDB_VERSION_MAX; backport the complete compatible xperms implementation.
- A max version of 29 explains why init invokes secilc with policy version 29, but the source audit is needed
  to identify whether this is a config cap or missing kernel code.
NOTE
