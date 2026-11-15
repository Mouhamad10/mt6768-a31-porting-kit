# GSI porting automation

Give the [`gsi-port.yml`](../.github/workflows/gsi-port.yml) workflow a **GSI URL** and it does the
deterministic half of "porting a GSI to the A31":

1. Downloads the GSI from the URL.
2. Normalises it: decompresses `.xz` / `.gz` / `.zip` / `.7z`, converts an Android **sparse** image
   to raw, and validates it is an `ext4`/`erofs` system image.
3. Builds an **A31 flashing kit** ZIP (fastbootd/recovery steps + the vbmeta-disable note), uploaded
   as an artifact. Optionally (toggle `attach_image`) it also converts and uploads the flashable
   `system` image itself.

## What is and isn't automatable (be realistic)

- **Deterministic (this workflow):** fetch, decompress, sparse↔raw, validate, and package the flash
  steps. This always works and saves you the manual conversion.
- **Not automatable from CI:** making a *specific* GSI actually boot and have working RIL, sensors,
  fingerprint, etc. That depends on the GSI build vs. the A31's A12 vendor, and can only be
  confirmed by **flashing and booting on the device**. CI has no A31 to boot on. The common per-GSI
  fixups are listed in the flashing kit's README.

## Picking a GSI that has a chance on the A31

- **arm64, A-only** (the A31 is A-only, not A/B).
- Start with a **vndklite** + **permissive** build to confirm the base boots, then move to a normal
  enforcing build.
- Android 13–16 GSIs commonly boot on an A12 vendor with vndklite; a GSI that demands a newer vendor
  than A12 would need a separate vendor port.

## Flow

1. Run the workflow with your GSI URL → download the flashing kit (and optionally the image).
2. Follow the kit's README: fastbootd, disable vbmeta, `fastboot flash system`, wipe data.
3. If it bootloops or a subsystem is dead, try a different GSI variant (type/version/permissive) —
   that trial-and-error is the real "porting", and it is done on the device, not in CI.
