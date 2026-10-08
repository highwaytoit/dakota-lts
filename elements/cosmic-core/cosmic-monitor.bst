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
- cosmic-build-meta.bst:core-deps/just.bst
- cosmic-build-meta.bst:core/libcosmic.bst
- freedesktop-sdk.bst:components/libxkbcommon.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

sources:
- kind: git_repo
  url: github:pop-os/cosmic-monitor.git
  track: epoch-1.*
  ref: epoch-1.10.0-0-ga79ce9e7d2259a82150d56978fb7a094bd4ec2f0
- kind: cargo2
  url: 'crates:'
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
