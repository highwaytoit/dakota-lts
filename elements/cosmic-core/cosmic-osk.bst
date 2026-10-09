# Supplement to Razorfin's upstream COSMIC BuildStream stack.
# Git ref must be refreshed from the latest official cosmic-epoch release.
# Cargo ref is generated from this exact revision's Cargo.lock by source sync.
kind: manual

build-depends:
- cosmic-build-meta.bst:core-deps/sandbox-tools.bst
- freedesktop-sdk.bst:components/rust.bst
- freedesktop-sdk.bst:components/pkg-config.bst
- freedesktop-sdk.bst:components/_private/gcc-base.bst
- freedesktop-sdk.bst:bootstrap/binutils.bst
- freedesktop-sdk.bst:components/stripper.bst
- cosmic-build-meta.bst:core-deps/just.bst
- cosmic-build-meta.bst:core/libcosmic.bst
- freedesktop-sdk.bst:components/libxkbcommon.bst
- freedesktop-sdk.bst:components/systemd.bst
- freedesktop-sdk.bst:components/wayland.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst
- cosmic-build-meta.bst:core/cosmic-icons.bst
sources:
- kind: git_repo
  url: github:pop-os/cosmic-osk.git
  track: epoch-1.*
  ref: epoch-1.10.0-0-g1b7ec698b79d248d6a59ff426f453fc7ce3edc91
- kind: cargo2
  url: 'crates:crates/'
  vendor-dir: .vendored
  ref: []

config:
  configure-commands: []
  build-commands:
  - just build-release
  install-commands:
  - just rootdir="%{install-root}" prefix="%{prefix}" install
  strip-commands:
  - '%{strip-binaries}'
