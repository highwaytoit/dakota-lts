# Stage 4: local COSMIC Mesa OCI filesystem, including all stable Epoch pieces.
# No GHCR publication; this remains an experimental BuildStream artifact.
kind: compose

build-depends:
- cosmic/system.bst
- cosmic-build-meta.bst:oci/integration/bootc-defaults-cosmic.bst

config:
  exclude:
  - debug
  - devel
  - doc
  - extra
  - static-blocklist
