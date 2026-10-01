# Dakota LTS

Dakota LTS is a downstream variant of [Bluefin Dakota](https://github.com/projectbluefin/dakota).

The goal is simple: keep the modern Dakota desktop and userspace while using a slower-moving Linux and NVIDIA base for long-term stability.

## What is different

- The current Linux baseline is **6.18 LTS**, following stable 6.18.x point releases while that LTS generation is in use.
- The current NVIDIA baseline is the **R580 LTS** driver branch.
- Dakota LTS follows a **slow-moving LTS cadence**. Linux 6.18 and NVIDIA R580 are the current baseline, not permanent choices for the full lifetime of those branches.
- Normal Dakota desktop, userspace, application, codec, and platform improvements continue to follow upstream.
- Changes that touch the kernel, NVIDIA, initramfs/module coupling, or NVIDIA power-management behavior are reviewed before they are brought into Dakota LTS.

This repository does not replace upstream Dakota documentation. For Dakota features, design, feedback workflows, and general project documentation, use the [upstream Dakota repository](https://github.com/projectbluefin/dakota).

## Branch model

- `testing` — upstream integration lane. Current upstream Dakota changes are reviewed here first.
- `testing-lts` — active Dakota LTS development branch.

The intended maintenance flow is:

**Upstream Dakota `testing` → fork `testing` → review → `testing-lts`**

This keeps the upstream connection intact while protecting the LTS kernel and NVIDIA choices.

## Development images

Current development images:

- `ghcr.io/highwaytoit/dakota-lts:testing-lts`
- `ghcr.io/highwaytoit/dakota-nvidia-lts:testing-lts`

These are development/testing images and are not a stable release channel yet.

## Validation status

- Linux 6.18 LTS image builds successfully.
- NVIDIA R580 image builds successfully.
- VM-level validation has passed for the LTS images.
- Physical NVIDIA hardware validation is still required before stable promotion, including driver loading, `nvidia-smi`, Wayland, suspend/resume, repeated sleep cycles, and power-management behavior.

## LTS maintenance policy

Dakota LTS follows a slow-moving LTS cadence rather than tracking the newest kernel and NVIDIA driver generations.

Current baseline:

- Linux: `v6.18.*`
- NVIDIA: R580

Stable point releases inside the active LTS branches can move forward through the existing resolver and tracking workflow.

Linux 6.18 and NVIDIA R580 are the current baseline, not permanent requirements for Dakota LTS.

A baseline may remain supported for a longer period when there is a practical reason or user demand, as long as both the kernel and NVIDIA driver remain supported and the rest of the Dakota desktop can continue to work cleanly with them.

A newer LTS baseline may also replace the current one before either component reaches end of life. This is expected when maintaining the older kernel or NVIDIA generation begins to hold back the desktop, hardware support, security, graphics stack, or other parts of Dakota.

The timing of a baseline change is therefore driven by compatibility and maintainability rather than by a fixed yearly schedule or by the published end-of-life date of a single component.

Moving to a new Linux LTS or NVIDIA long-lived driver generation is an explicit Dakota LTS maintenance decision and is reviewed and validated before adoption.

## Upstream

Dakota LTS is based on and follows [projectbluefin/dakota](https://github.com/projectbluefin/dakota).

General Dakota issues and documentation belong upstream. Fork-specific Linux LTS, NVIDIA long-lived driver, and Dakota LTS integration work belong in this repository.
