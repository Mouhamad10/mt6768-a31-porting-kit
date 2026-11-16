# Getting started — what this repo is and how to run it

This repository, **mt6768-a31-porting-kit**, is a complete kit for porting and bringing up custom
Android on the Samsung Galaxy A31 (SM-A315F, MediaTek MT6768) while keeping the stock Android 12
vendor. It gathers everything learned bringing up modern kernels and ROMs on this device: the device
facts, a crash database with root causes and fixes, a data-safe on-device test method, the kernel
patch stack, the build/packaging tools, the Magisk fix modules, and automation.

## Map of the repo

| area | what's in it |
|------|--------------|
| [`README.md`](../README.md) | the hub index and links to the source repos |
| [`docs/`](../docs) | device facts & partition map, kernel overview, 4.19→5.10 roadmap, automation design, GSI porting |
| [`bring-up/`](../bring-up) | the crash database, recovery-safe test method, modem/4G findings, sdfat exFAT fix, boot-log triage |
| [`patches/`](../patches) | the 29-patch A31 kernel stack |
| [`configs/`](../configs) | `a31_defconfig` and the 4.19 fragment |
| [`tools/`](../tools) | boot-image & DT tools, port scripts, and the boot-log triage scanner + signature DB |
| [`magisk/`](../magisk) | the touch-watchdog and LTE-guard Magisk modules |
| [`AnyKernel3/`](../AnyKernel3) | flashable-ZIP packaging config for the A31 |
| [`gsi/`](../gsi) | GSI flashing + vbmeta-disable guides |
| [`.github/workflows/`](../.github/workflows) | the three GitHub Actions below |

## The three GitHub Actions — how to run them

**All three are _manual_ (`workflow_dispatch`). Nothing runs automatically on push.** To run one you
must trigger it yourself:

1. Open the repo on GitHub → **Actions** tab.
2. In the **left sidebar**, click the workflow you want (e.g. *"Triage a boot log"*).
3. On the right, click the **"Run workflow"** dropdown button (top-right of the run list).
4. Fill the input fields, then click the green **"Run workflow"**.
5. A run appears in the list; click it to watch, read the **Summary**, and download the **Artifact**.

> If you don't see a **"Run workflow"** button: make sure you selected a workflow in the left list
> first (the button is per-workflow), you are on the **main** branch, and you are signed in as the
> repo owner. On a phone browser, use "Desktop site" — the button is easy to miss on mobile.

### 1. Triage a boot log  →  `boot-log-triage.yml`
Point it at a kernel log and it tells you which known fault fired and where the fix is.
- **Inputs:** `log_url` (a direct URL to a log) **or** `repo_path` (a log committed in this repo).
  You must give one of the two, or the run errors with "Provide either log_url or repo_path".
- **Output:** a Markdown triage report in the run **Summary** and as an artifact.
- **Try it now:** set `repo_path` to `examples/sample-bootloop.log` and Run. You'll get a FATAL
  verdict with the eBPF/bpfloader bootloop root-cause callout.

### 2. Port a GSI  →  `gsi-port.yml`
Normalises a GSI (download, decompress, sparse→raw, validate) and builds an A31 flashing kit.
- **Inputs:** `gsi_url` (**required** — a direct link to the `.img`/`.img.xz`/`.gz`/`.zip`/`.7z`;
  leaving it blank is the usual reason this one won't start), `label`, `attach_image` (true to also
  upload the converted image — large/slow).
- **Output:** an A31 flashing-kit ZIP artifact (and optionally the image).

### 3. Build a kernel  →  `build-kernel.yml`
Clones a MT6768 kernel, optionally applies this repo's patch stack, builds, and packages a flashable
ZIP with AnyKernel3.
- **Inputs (all have defaults, so it can run as-is):** `kernel_repo`, `kernel_ref`, `defconfig`
  (`a31_defconfig`), `apply_kit_patches` (`true`/`false`). This one takes many minutes.
- **Output:** a TWRP-flashable kernel ZIP artifact.

## Common reasons a run doesn't happen

- You never clicked **"Run workflow"** — these never trigger on their own (manual only).
- For **Port a GSI**, `gsi_url` was left blank (it is required).
- For **Triage**, both `log_url` and `repo_path` were left blank (give exactly one).
- You were looking at the Actions tab but hadn't selected the specific workflow in the left list.

## Running the triage tool locally (no CI)

```sh
python3 -I tools/triage-bootlog.py examples/sample-bootloop.log
# a real capture (text or a binary ramoops/pmsg dump) works too:
python3 -I tools/triage-bootlog.py path/to/last_kmsg.txt
```

See [`bring-up/boot-log-signatures.md`](../bring-up/boot-log-signatures.md) for how the signature
database and the same-boot correlation work, and how to add a signature for a new crash.
