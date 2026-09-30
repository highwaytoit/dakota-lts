# Dakota LTS: Linux 6.18 Kernel and NVIDIA R580

This document records the Dakota LTS work done in September 2026 to keep the
`testing-lts` branch on a long-term-support Linux kernel and NVIDIA driver
branch while preserving Dakota's laptop/hybrid-GPU power-management behavior.

It is intentionally more detailed than a normal changelog entry. The purpose is
to leave enough evidence for the next NVIDIA LTS migration, even if that happens
a year or more later.

## Scope and current policy

Branch:

- `highwaytoit/dakota-lts:testing-lts`

Current Linux policy:

- track only Linux `6.18.x` stable point releases
- current reference at the time of this document:
  `v6.18.54-0-g1b357ecb321392158d507b04672ffee57bfa071d`
- source element: `elements/core/linux-fdsdk.bst`

Current NVIDIA policy:

- long-lived NVIDIA branch: `R580`
- current version: `580.178.04`
- source element: `elements/bluefin-nvidia/nvidia-drivers.bst`
- source SHA-256:
  `5975a86ee45bffcb626f51ae33d1169b108186a2ea47ad651e72f13fa4b6d6f9`

The important lesson is that Linux LTS and NVIDIA LTS are not equivalent
migration problems.

Linux stayed on the same kernel build/install contract and mainly required
changing the tracked stable series plus validating the existing Dakota/fdsdk
kernel recipe.

NVIDIA R580 has a different proprietary `.run` payload contract from the newer
NVIDIA branches used by upstream Dakota. A safe migration therefore requires
auditing the payload, not only replacing the version string.

---

## 1. Linux 6.18 LTS

### Why the kernel move was comparatively simple

Dakota already had a local stable-kernel element based on the freedesktop-sdk
kernel recipe:

`elements/core/linux-fdsdk.bst`

The LTS conversion reused that build recipe. The source tracking changed from
the upstream testing kernel series to:

```yaml
track: v6.18.*
ref: v6.18.54-0-g1b357ecb321392158d507b04672ffee57bfa071d
```

The local worker runs:

```bash
just bst source track core/linux-fdsdk.bst
```

before a build and verifies that:

- the track remains exactly `v6.18.*`
- the resolved ref is a stable `v6.18.N` point release
- release candidates do not match the LTS tracking pattern

The main LTS commit was:

- `a93d4e502c36c3423027dae924f833cc8496ee50`
- **feat(kernel): track Linux 6.18 LTS**
- https://github.com/highwaytoit/dakota-lts/commit/a93d4e502c36c3423027dae924f833cc8496ee50

### Dakota kernel behavior retained

The LTS kernel is not a completely generic upstream kernel element. The local
recipe keeps the Dakota/freedesktop-sdk behavior that the image depends on,
including:

- the freedesktop-sdk 26.08 kernel build structure
- signed module handling
- module stripping before signatures are appended
- Dakota hardware-enablement config from `files/linux/dakota-config.sh`
- `CONFIG_CRYPTO_ZSTD=y`

`CONFIG_CRYPTO_ZSTD=y` is intentional because the image uses
`zswap.compressor=zstd`; the compressor must be built in rather than available
only as a module.

The zswap configuration was also adjusted for Linux 6.18 so the image does not
expect the removed/unsupported `zswap.zpool` parameter.

### Future Linux 6.18 maintenance

For normal Linux 6.18 maintenance, the worker should continue resolving the
latest `v6.18.*` stable point release.

At a future freedesktop-sdk bump, re-audit the local kernel element against the
new fdsdk kernel recipe and re-sync the vendored kernel scripts/patch queue as
documented in `elements/core/linux-fdsdk.bst`.

Do not assume a future major kernel LTS branch is a pure version-number change;
repeat the config and fdsdk recipe comparison when moving away from 6.18.

---

## 2. Why NVIDIA LTS was different

Upstream Dakota moved forward to newer NVIDIA driver branches while this LTS
fork intentionally selected R580.

At the time of this work, upstream Dakota `testing` used NVIDIA `615.71.09`,
while this branch selected:

```yaml
nvidia-lts-branch: '580'
nvidia-version: '580.178.04'
```

and:

```text
NVIDIA-Linux-x86_64-580.178.04.run
```

The initial assumption was that the existing Dakota packaging recipe could
remain unchanged while only the NVIDIA source/version moved to R580.

That assumption was incomplete.

The Dakota NVIDIA element contains explicit expectations about files shipped by
the NVIDIA `.run` payload. Some of those expectations were added while Dakota
was already on newer NVIDIA branches. R580 does not ship every one of those
files in the same way.

That is the central rule for future NVIDIA LTS work:

> Treat an NVIDIA branch change as a payload-contract migration, not as a simple
> version bump.

---

## 3. NVIDIA R580 resolver fix

The local resolver updates the R580 source URL, SHA-256, filename, and version in
`elements/bluefin-nvidia/nvidia-drivers.bst`.

An early R580 workflow failed in the resolver with:

```text
re.PatternError: invalid group reference 15 at position 1
```

The SHA-256 began with digits, so replacements written as `\1...` could be
parsed as a larger regex group number.

The resolver was corrected to use explicit group syntax:

```python
\g<1>
```

Commit:

- `7deef5b7731f94ac6d2c8e8eecb96443ede4ad2f`
- **fix(nvidia): use explicit regex group references**
- https://github.com/highwaytoit/dakota-lts/commit/7deef5b7731f94ac6d2c8e8eecb96443ede4ad2f

This fix is independent of NVIDIA power management. It only makes the resolver
safe for source strings whose replacement text begins with digits.

---

## 4. Dakota's laptop NVIDIA suspend contract

This part must be preserved.

Dakota had already fixed a real NVIDIA suspend/resume problem on laptops and
hybrid systems. Upstream commit:

- `db17346afdad0acfb7162b30e4983568e5b7cb9b`
- **fix(nvidia): ship the suspend units the driver's PM contract requires**
- https://github.com/projectbluefin/dakota/commit/db17346afdad0acfb7162b30e4983568e5b7cb9b

That work made the NVIDIA systemd power-management path a hard requirement
because Dakota sets:

```text
NVreg_PreserveVideoMemoryAllocations=1
```

When that option is enabled, NVIDIA suspend/resume is not just a normal kernel
callback path. The NVIDIA systemd services perform the required
`/proc/driver/nvidia/suspend` handshake and save/restore GPU memory.

The LTS branch still retains all of this.

### PM services that remain required

The R580 build still requires and installs:

- `nvidia-suspend.service`
- `nvidia-resume.service`
- `nvidia-hibernate.service`
- `nvidia-suspend-then-hibernate.service`

It also requires and installs:

- `systemd/nvidia-sleep.sh`
- `systemd/system-sleep/nvidia`

The image preset enables all four NVIDIA PM services.

### VRAM preservation settings that remain in place

`elements/bluefin-nvidia/nvidia-modprobe-config.bst` still installs:

```text
options nvidia NVreg_PreserveVideoMemoryAllocations=1
options nvidia NVreg_TemporaryFilePath=/var/tmp
```

The second setting is important because the NVIDIA VRAM save file should not be
written to a tmpfs-backed `/tmp`. On GPUs with several GiB of VRAM, that can
turn suspend into a large RAM allocation. Dakota therefore uses `/var/tmp`.

Official NVIDIA R580 power-management reference:

- https://download.nvidia.com/XFree86/Linux-x86_64/580.178.04/README/powermanagement.html

### Why this matters for hybrid laptops

The purpose of preserving this design is not merely theoretical. Hybrid laptops
such as Dell Precision/mobile-workstation systems have both an integrated GPU
and a discrete NVIDIA GPU. Suspend/resume must preserve NVIDIA state without
leaving the graphical session or the dGPU in a broken state after wake.

Therefore an R580 compatibility change must never "solve" a packaging failure by
removing the Dakota PM services or disabling
`NVreg_PreserveVideoMemoryAllocations`.

---

## 5. R580 incompatibility #1: no-freeze systemd drop-ins

### Failure

Upstream Dakota expected the NVIDIA `.run` payload to provide systemd
no-freeze drop-ins under paths such as:

```text
systemd/system/systemd-*.service.d/nvidia-suspend-nofreeze.conf
```

R580.178.04 did not provide those drop-ins in the layout expected by the Dakota
recipe.

The build therefore failed with:

```text
ERROR: no nvidia-suspend-nofreeze drop-ins in payload
```

### Why the no-freeze policy matters

The no-freeze policy prevents systemd from freezing the graphical user session
before `nvidia-sleep.sh` performs its VT/session work.

The intended policy is:

```ini
[Service]
Environment=SYSTEMD_SLEEP_FREEZE_USER_SESSIONS=false
```

Independent R580 distro packaging showed the same approach: R580 packagers
create the systemd override themselves rather than relying on a matching file
inside the NVIDIA payload.

Useful R580 reference:

- CachyOS R580 packaging:
  https://github.com/CachyOS/CachyOS-PKGBUILDS/blob/master/nvidia/nvidia-580xx/nvidia-580xx-utils/PKGBUILD

### LTS adaptation

The LTS branch now creates the drop-ins explicitly for:

- `systemd-suspend.service`
- `systemd-hibernate.service`
- `systemd-hybrid-sleep.service`
- `systemd-suspend-then-hibernate.service`

Commits:

- `717f7ed50f64ff3f2ddddd8f79160525c384c0fb`
  - **fix(nvidia): install R580 no-freeze systemd drop-ins**
  - https://github.com/highwaytoit/dakota-lts/commit/717f7ed50f64ff3f2ddddd8f79160525c384c0fb
- `d236d5bfef89d37a8409d9d9e6c3c4b9a239cb25`
  - **fix(nvidia): repair R580 no-freeze drop-in YAML**
  - https://github.com/highwaytoit/dakota-lts/commit/d236d5bfef89d37a8409d9d9e6c3c4b9a239cb25

Important: this adaptation **preserves** Dakota's laptop suspend behavior. It
does not remove it.

---

## 6. Separate worker lifecycle failure

During this work there was also a self-hosted-runner/rootless-Podman problem.
That was a separate infrastructure failure and must not be confused with an
NVIDIA packaging failure.

Relevant runs:

- https://github.com/highwaytoit/dakota-lts/actions/runs/36682142650
- https://github.com/highwaytoit/dakota-lts/actions/runs/36683434149

The observed chain was:

1. the worker's SSH login session closed
2. the user had `Linger=no`
3. systemd-logind removed the login session
4. the per-user systemd manager stopped
5. rootless Podman/libpod scopes were stopped with it
6. `/run/user/1000` was removed
7. the system-level GitHub runner remained alive and reported the build failure

A later run successfully passed the rootless Podman preflight and reached the
NVIDIA BuildStream element. That separation was important: it proved the next
failure was inside NVIDIA packaging rather than another worker/runtime failure.

Do not "fix" NVIDIA failures by changing `crun`, recreating
`/run/user/1000/containers`, changing Podman storage paths, or reintroducing
the discarded temporary `XDG_RUNTIME_DIR` workaround unless new evidence
specifically points there.

---

## 7. R580 incompatibility #2: dlsnetparams.csv

### Where the newer requirement came from

Upstream Dakota added a hard requirement for `dlsnetparams.csv` while updating
to NVIDIA 610.57.04:

- `ed2bea83b12cd9ebcd3b708e1006e4d607dbc040`
- **feat(nvidia): update to 610.57.04 and ship its missing data files (#1277)**
- https://github.com/projectbluefin/dakota/commit/ed2bea83b12cd9ebcd3b708e1006e4d607dbc040

That upstream block required all three:

```text
systemd/system/nvidia-powerd.service
nvidia-dbus.conf
dlsnetparams.csv
```

and failed the build if any one was absent.

This requirement therefore came from a newer NVIDIA payload contract. It was not
a timeless requirement of all NVIDIA Linux branches.

### Independent R580 vs newer-branch audit

The R580 audit compared several packaging sources.

R580.178.04 packaging provides the important Dynamic Boost pieces:

- `nvidia-powerd`
- `nvidia-powerd.service`
- `nvidia-dbus.conf`

but does not ship/install `dlsnetparams.csv` the way the newer branch does.

Useful references:

- CachyOS R580:
  https://github.com/CachyOS/CachyOS-PKGBUILDS/blob/master/nvidia/nvidia-580xx/nvidia-580xx-utils/PKGBUILD
- CachyOS newer NVIDIA package:
  https://github.com/CachyOS/CachyOS-PKGBUILDS/blob/master/nvidia/nvidia-utils/PKGBUILD
- negativo17 R580:
  https://github.com/negativo17/nvidia-580/blob/master/nvidia-driver/nvidia-driver.spec
- negativo17 newer NVIDIA package:
  https://github.com/negativo17/nvidia-driver/blob/master/nvidia-driver.spec
- example R580.178.04 installer log:
  https://github.com/lz3450/LFS/blob/8ba98e5823759e255dd9dbcec3a3532f26cbf4f2/config/nvidia/driver-install.log

The same audit also showed that the ordinary R580 graphics stack remains
present: Vulkan JSON, EGL external-platform JSON, application profiles,
firmware, NGX/Wine components, OptiX data, userspace libraries, and the NVIDIA
open kernel module sources.

---

## 8. Exact worker evidence for dlsnetparams.csv

The decisive evidence came from the self-hosted worker, not from inference.

Exact log:

```text
/home/worker/.cache/buildstream/logs/bluefin/bluefin-nvidia-nvidia-drivers/278f219c-build.20260930-074924.log
```

The log showed:

- the build was using `580.178.04`
- NVIDIA kernel modules compiled far enough to reach userspace packaging
- the suspend/hibernate service checks passed
- the `nvidia-sleep.sh` and system-sleep hook checks passed
- the build reached the Dynamic Boost payload check

The fatal line was:

```text
ERROR: dlsnetparams.csv missing from driver payload
```

Because the required-file loop checked files in this order:

```text
systemd/system/nvidia-powerd.service
nvidia-dbus.conf
dlsnetparams.csv
```

and reported the third file as missing, the same worker run proved that:

- `nvidia-powerd.service` was present
- `nvidia-dbus.conf` was present
- `dlsnetparams.csv` was absent

Relevant workflow run:

- https://github.com/highwaytoit/dakota-lts/actions/runs/36685889444
- job: `109791542942`

This run also showed the rootless worker problem was no longer the blocker: the
worker preflight succeeded and the build reached the real NVIDIA element
failure.

---

## 9. R580 Dynamic Boost repair

The repair deliberately did **not** remove Dynamic Boost.

Commit:

- `bfff3fc5fc06fda90763d4759f192baa637ce3ca`
- **fix(nvidia): make R580 powerd data optional**
- https://github.com/highwaytoit/dakota-lts/commit/bfff3fc5fc06fda90763d4759f192baa637ce3ca

The resulting policy is:

### Still mandatory

- `nvidia-powerd.service`
- `nvidia-dbus.conf`

### Conditional

- `dlsnetparams.csv`

The element now installs `dlsnetparams.csv` only when the selected NVIDIA
payload actually provides it.

Conceptually:

```bash
for f in systemd/system/nvidia-powerd.service nvidia-dbus.conf; do
    if [ ! -f "$f" ]; then
        echo "ERROR: $f missing from driver payload" >&2
        exit 1
    fi
done

install -Dm644 systemd/system/nvidia-powerd.service ...
install -Dm644 nvidia-dbus.conf ...

if [ -f dlsnetparams.csv ]; then
    install -Dm644 dlsnetparams.csv ...
fi
```

This is a compatibility adaptation for the R580 payload. It is not a removal of
the feature.

---

## 10. What is still preserved after the R580 changes

The LTS branch still carries the laptop/hybrid-GPU protections that motivated
the upstream Dakota fixes.

### Suspend/resume path

Still present:

- `nvidia-suspend.service`
- `nvidia-resume.service`
- `nvidia-hibernate.service`
- `nvidia-suspend-then-hibernate.service`
- `nvidia-sleep.sh`
- `systemd/system-sleep/nvidia`

### Session freeze handling

Still present:

```ini
[Service]
Environment=SYSTEMD_SLEEP_FREEZE_USER_SESSIONS=false
```

for the relevant systemd sleep units.

### VRAM preservation

Still present:

```text
NVreg_PreserveVideoMemoryAllocations=1
NVreg_TemporaryFilePath=/var/tmp
```

### Dynamic Boost

Still present:

- `nvidia-powerd`
- `nvidia-powerd.service`
- `nvidia-dbus.conf`

Only the newer-branch-only `dlsnetparams.csv` data-file assumption became
conditional.

Therefore the R580 work is intended to preserve Dakota's NVIDIA laptop behavior,
not reduce it.

---

## 11. Build/run timeline

Useful workflow references from this debugging sequence:

| Run | Meaning |
|---|---|
| https://github.com/highwaytoit/dakota-lts/actions/runs/36668409334 | known-good default/non-NVIDIA worker build; useful worker baseline, **not** proof that NVIDIA worked |
| https://github.com/highwaytoit/dakota-lts/actions/runs/36678048408 | NVIDIA resolver failed before the explicit regex-group fix |
| https://github.com/highwaytoit/dakota-lts/actions/runs/36678721349 | R580 packaging reached the missing no-freeze payload assumption |
| https://github.com/highwaytoit/dakota-lts/actions/runs/36682142650 | build interrupted by user-manager/rootless-Podman teardown |
| https://github.com/highwaytoit/dakota-lts/actions/runs/36683434149 | rootless Podman preflight failed while the normal user runtime directory was absent |
| https://github.com/highwaytoit/dakota-lts/actions/runs/36685889444 | rootless preflight succeeded; real NVIDIA failure identified as missing `dlsnetparams.csv` |

Do not use the successful default build as evidence for NVIDIA. Its NVIDIA
resolver/build path was skipped.

---

## 12. Future NVIDIA LTS migration checklist

When R580 eventually reaches end of support and Dakota LTS moves to another
long-lived NVIDIA branch, do **not** start by copying the newest upstream Dakota
driver version into this branch.

Use this sequence.

### A. Identify the target branch

Record:

- NVIDIA branch, for example `Rxxx`
- exact driver version
- official `.run` URL
- SHA-256
- support/EOL rationale

### B. Compare the new payload before editing the recipe

Extract or otherwise inspect the target NVIDIA `.run` payload and compare it
against the current BuildStream expectations.

At minimum check:

- `.manifest` format and TYPE names
- native libraries and symlinks
- COMPAT32 libraries
- Vulkan ICD/layer JSON
- EGL vendor/external-platform JSON
- application profile files
- GSP firmware
- OpenCL ICD
- OptiX data
- NGX/Wine files
- `nvidia-powerd`
- `nvidia-dbus.conf`
- any Dynamic Boost data files
- all NVIDIA suspend/resume/hibernate units
- `nvidia-sleep.sh`
- system-sleep hook
- systemd no-freeze policy/drop-ins
- license/EULA file layout

### C. Preserve the laptop PM contract

Unless NVIDIA upstream explicitly replaces this mechanism, keep and verify:

- `NVreg_PreserveVideoMemoryAllocations=1`
- `NVreg_TemporaryFilePath=/var/tmp`
- NVIDIA suspend/resume/hibernate services
- `nvidia-sleep.sh`
- system-sleep hook
- no-freeze session handling

Do not silently make these optional just to make a build pass.

### D. Distinguish branch-specific files from required functionality

The R580 work demonstrated this exact distinction:

- required **functionality**: suspend/resume handshake, VRAM preservation,
  Dynamic Boost unit/D-Bus policy
- branch-specific **file layout/data**: payload-provided no-freeze drop-ins and
  `dlsnetparams.csv`

If a future branch moves or removes a file, first determine whether the feature
was replaced, relocated, or genuinely removed.

### E. Use the worker log as the final source of truth

If BuildStream fails, capture the complete element log from:

```text
~/.cache/buildstream/logs/bluefin/bluefin-nvidia-nvidia-drivers/
```

Do not diagnose from GitHub's final 20-line command tail alone. That tail can
show the end of a large shell command rather than the command that actually
failed.

### F. Validate on real laptop hardware

A successful image build is not enough for an NVIDIA LTS transition.

On a hybrid NVIDIA laptop, validate at least:

1. NVIDIA modules load
2. Wayland session uses the expected GPU stack
3. `nvidia-smi` works
4. suspend succeeds
5. resume succeeds
6. graphical session survives wake
7. repeated suspend/resume cycles work
8. hibernate/suspend-then-hibernate behavior if those paths are used
9. no NVIDIA PM unit is left failed
10. Dynamic Boost service behavior is sane on supported hardware

This is particularly important because the upstream Dakota PM fix was created
to solve real suspend failures, not only build-time packaging problems.

---

## 13. Status at the time this document was created

The repository change making `dlsnetparams.csv` conditional was committed as:

`bfff3fc5fc06fda90763d4759f192baa637ce3ca`

A new NVIDIA build was started after that change.

This document intentionally does **not** record that post-fix build as successful
yet. Final build and hardware validation should be added only after the result is
observed and verified.

The known facts at this point are:

- Linux 6.18 LTS tracking is in place.
- R580.178.04 source resolution works.
- R580 kernel-module compilation reaches packaging.
- the R580 no-freeze payload mismatch has been adapted without removing Dakota's
  laptop PM behavior.
- the exact worker failure caused by the newer-branch
  `dlsnetparams.csv` assumption was proven.
- `nvidia-powerd.service` and `nvidia-dbus.conf` remain mandatory.
- `dlsnetparams.csv` is now conditional.
- the Dakota NVIDIA suspend/resume/VRAM-preservation stack remains in place.

Update this section after the post-`bfff3fc5` build and real-hardware suspend
tests are complete.
