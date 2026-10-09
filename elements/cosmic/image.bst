# Stage 4 experimental COSMIC OCI assembly; testing channel only.
# Reuses Razorfin's bootc assembly sequence while composing Dakota's
# COSMIC system stack (including supplemental official Epoch components).
# Image branding/install defaults must be reviewed before deployment.
kind: script

build-depends:
- freedesktop-sdk.bst:components/fakecap.bst
- freedesktop-sdk.bst:components/gzip.bst
- freedesktop-sdk.bst:oci/oci-builder.bst
- freedesktop-sdk.bst:vm/prepare-image.bst
- cosmic-build-meta.bst:oci/cosmic/init-scripts.bst
- filename: freedesktop-sdk.bst:oci/platform-oci.bst
  config:
    location: /parent
- filename: cosmic/filesystem.bst
  config:
    location: /layer

environment:
  LD_PRELOAD: /usr/libexec/fakecap/fakecap.so
  FAKECAP_DB: /fakecap

variables:
  # Distinct from Razorfin and Dakota's GNOME image seed.
  sysroot-seed: 33bf82de-d065-453e-a1d5-38cc5c06a901

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
      comment: "Dakota COSMIC experimental nonpublished build"
      config:
        Labels:
          'org.opencontainers.image.title': 'Dakota COSMIC (experimental)'
          'org.opencontainers.image.description': 'COSMIC bootc testing image (standard edition)'
          'org.opencontainers.image.vendor': 'Dakota LTS'
          'org.opencontainers.image.licenses': 'GPL-3.0-or-later'
          'org.opencontainers.image.source': 'https://github.com/highwaytoit/dakota-lts'
          'containers.bootc': '1'
      index-annotations:
        'org.opencontainers.image.ref.name': 'ghcr.io/highwaytoit/dakota-cosmic:testing'
    EOF
