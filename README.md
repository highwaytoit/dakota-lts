# Dakota LTS

Dakota LTS is a downstream variant of [Bluefin Dakota](https://github.com/projectbluefin/dakota).

The goal is simple: keep the modern Dakota desktop and userspace while using a slower-moving Linux and NVIDIA base for long-term stability.

## What is different

- The current Linux baseline is **6.18 LTS**, following stable 6.18.x point releases.
- The current NVIDIA baseline is the **R580 LTS** driver branch.
- Normal Dakota desktop, userspace, application, codec, and platform improvements continue to follow upstream.
- Kernel, NVIDIA, initramfs/module coupling, and NVIDIA power-management changes are reviewed before entering the LTS release lane.
- Routine Linux 6.18.x and NVIDIA R580 maintenance releases are resolved at build time without changing the approved LTS generation.

This repository does not replace upstream Dakota documentation. For Dakota features, design, feedback workflows, and general project documentation, use the [upstream Dakota repository](https://github.com/projectbluefin/dakota).

## Branch and release model

- `testing-lts` — LTS adoption/candidate branch. The upstream source for LTS adoption is `projectbluefin/dakota:testing`. Selected changes are validated here in a VM and, when appropriate, on physical hardware.
- `main` — stable production source branch.

The intended flow is:

**Upstream Dakota `testing` → `testing-lts` → validation → `main`**

Stable promotion is `testing-lts` → `main`; do not independently replay the same commits onto `main`.

The fork `testing` branch may continue to exist for upstream-derived/integration purposes, but it is not part of the Dakota LTS release chain.

Image channels:

- `ghcr.io/highwaytoit/dakota-lts:testing-lts`
- `ghcr.io/highwaytoit/dakota-nvidia-lts:testing-lts`
- `ghcr.io/highwaytoit/dakota-lts:stable`
- `ghcr.io/highwaytoit/dakota-nvidia-lts:stable`

`:testing-lts` is the candidate/testing channel. `:stable` is the normal production channel.

## Release cadence

Code and integration changes move through `testing-lts` before they reach `main`.

The stable publisher runs from `main`:

- automatically every Friday at **07:00 UTC** (02:00 EST),
- automatically after a push to `main`,
- manually through GitHub Actions when needed.

Each stable run resolves the newest maintenance release inside the approved Linux 6.18 and NVIDIA R580 branches, builds both images, validates them, pushes immutable build tags, and then moves `:stable` only after both images build successfully.

A new Linux LTS generation or NVIDIA LTS generation is not automatic. Changing either baseline is an explicit maintenance decision that goes through `testing-lts` validation first.

## Validation status

Both image variants are now running on physical hardware.

- **Dell Latitude 7210 2-in-1** — non-NVIDIA Dakota LTS image, running without known issues observed.
- **Dell Precision 5570** — NVIDIA Dakota LTS image on an NVIDIA RTX A2000 8GB Laptop GPU, running without known issues observed.
- NVIDIA R580.178.04 has been validated on the Precision 5570 with the driver loaded and `nvidia-smi` reporting the RTX A2000 correctly.
- VM-level validation has also passed for the LTS images.

Hardware coverage will continue to grow as the project is used on more systems.

## LTS maintenance policy

Current baseline:

- Linux: `v6.18.*`
- NVIDIA: R580

Dakota LTS follows a slow-moving LTS cadence rather than tracking the newest kernel and NVIDIA driver generations.

A baseline can remain in use while it remains supported and compatible with the rest of Dakota. A newer LTS baseline may replace it earlier when maintaining the older generation begins to hold back hardware support, security, graphics, or the desktop stack.

Moving to a new Linux LTS or NVIDIA long-lived driver generation is always reviewed and validated before adoption.

## Upstream

Dakota LTS is based on and follows [projectbluefin/dakota](https://github.com/projectbluefin/dakota).

General Dakota issues and documentation belong upstream. Fork-specific Linux LTS, NVIDIA long-lived driver, release-channel, and Dakota LTS integration work belong in this repository.
