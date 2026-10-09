# Full COSMIC NVIDIA runtime sysroot; no GNOME or Bluefin branding.
# Same filter and bootc-defaults pattern as the standard COSMIC image.
# Bootc update target/branding will be reviewed before any deployment.
kind: compose

build-depends:
- cosmic/nvidia-system.bst
- cosmic-build-meta.bst:oci/integration/bootc-defaults-cosmic-nvidia.bst

config:
  exclude:
  - debug
  - devel
  - doc
  - extra
  - static-blocklist
