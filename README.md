# Dakota LTS

Dakota LTS is a downstream variant of [Bluefin Dakota](https://github.com/projectbluefin/dakota).

The goal is simple: keep the modern Dakota desktop and userspace while using a slower-moving Linux and NVIDIA base for long-term stability.

## What is different

- Linux stays on the **6.18 LTS** series and follows stable 6.18.x point releases.
- The NVIDIA image stays on the **R580 LTS** driver branch.
- Normal Dakota desktop, userspace, application, codec, and platform improvements continue to follow upstream.
- Upstream changes that touch the kernel, NVIDIA, initramfs/module coupling, or NVIDIA power-management behavior are reviewed before they are brought into Dakota LTS.

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

The LTS contract is the branch family, not one frozen point release:

- Linux: `v6.18.*`
- NVIDIA: R580

Stable point releases inside those LTS branches can move forward through the existing resolver/tracking workflow.

Changes outside those LTS families are explicit maintenance decisions and are not inherited automatically.

## Upstream

Dakota LTS is based on and follows [projectbluefin/dakota](https://github.com/projectbluefin/dakota).

General Dakota issues and documentation belong upstream. Fork-specific Linux 6.18 LTS, NVIDIA R580, and Dakota LTS integration work belong in this repository.
