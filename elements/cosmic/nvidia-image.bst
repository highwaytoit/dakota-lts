# Stage 5 experimental COSMIC NVIDIA OCI image; testing channel only.
# Reuse COSMIC's full system stack, Dakota's R580 driver, and the
# shared freedesktop-sdk OCI platform rather than adding a second kernel.
kind: script

build-depends:
- freedesktop-sdk.bst:components/fakecap.bst
- freedesktop-sdk.bst:components/gzip.bst
- freedesktop-sdk.bst:oci/oci-builder.bst
- freedesktop-sdk.bst:vm/prepare-image.bst
- cosmic/nvidia-init-scripts.bst
- filename: freedesktop-sdk.bst:oci/platform-oci.bst
  config:
    location: /parent
- filename: cosmic/nvidia-filesystem.bst
  config:
    location: /layer

environment:
  LD_PRELOAD: /usr/libexec/fakecap/fakecap.so
  FAKECAP_DB: /fakecap

variables:
  # Unique image UUID seed, distinct from the standard COSMIC edition.
  sysroot-seed: d6d46e88-b8e0-41bf-9df9-ad6b526fa841

config:
  commands:
  - mkdir /fakecap
  - |
    systemd-sysusers --root /layer
  - |
    prepare-image.sh \
      --sysroot /layer \
      --initscripts /initial_scripts \
      --seed "%{sysroot-seed}" \
      --noroot --noboot >/dev/null
  - |
    ln -sf /dev/null /layer/etc/systemd/system/getty@tty1.service
  - |
    if [ -d /layer/usr/etc ]; then
      mkdir -p /layer/etc
      cp -a /layer/usr/etc/. /layer/etc/
      rm -rf /layer/usr/etc
    fi
  - |
    # FDSDK's Mesa and NVIDIA GBM backends must coexist for hybrid GPUs.
    GBM_DIR="/layer%{libdir}/GL/lib/gbm"
    if [ ! -L "$GBM_DIR" ]; then
      echo "FATAL: FDSDK GL/lib/gbm symlink is missing" >&2
      exit 1
    fi
    for backend in dri_gbm.so nvidia-drm_gbm.so; do
      if [ ! -e "$GBM_DIR/$backend" ]; then
        echo "FATAL: GBM backend $backend missing from COSMIC NVIDIA sysroot" >&2
        exit 1
      fi
    done
  - |
    cd "%{install-root}"
    build-oci <<EOF
    mode: oci
    gzip: disabled
    images:
    - os: linux
      architecture: "%{go-arch}"
      parent:
        image: /parent
      layer: /layer
      comment: "Dakota COSMIC NVIDIA experimental nonpublished build"
      config:
        Labels:
          'org.opencontainers.image.title': 'Dakota COSMIC NVIDIA (experimental)'
          'org.opencontainers.image.description': 'COSMIC bootc testing image with Dakota NVIDIA R580 LTS'
          'org.opencontainers.image.vendor': 'Dakota LTS'
          'org.opencontainers.image.licenses': 'GPL-3.0-or-later AND LicenseRef-NVIDIA-SLA'
          'org.opencontainers.image.source': 'https://github.com/highwaytoit/dakota-lts'
          'containers.bootc': '1'
      index-annotations:
        'org.opencontainers.image.ref.name': 'ghcr.io/highwaytoit/dakota-cosmic-nvidia:testing'
    EOF
