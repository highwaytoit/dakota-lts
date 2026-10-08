# COSMIC sound theme: installed sounds and theme metadata (CC-BY-SA-4.0).
# Meson build/install is provided by upstream.
kind: meson

build-depends:
- cosmic-build-meta.bst:core-deps/sandbox-tools.bst
- freedesktop-sdk.bst:components/meson.bst

depends:
- freedesktop-sdk.bst:public-stacks/runtime-minimal.bst

sources:
- kind: git_repo
  url: github:pop-os/cosmic-sound-theme.git
  track: epoch-1.*
  ref: epoch-1.10.0-0-gbf5335fe1af0cb3bee83e1ad2371410ee434658d

variables:
  strip-binaries: ''
