# Razorfin COSMIC BuildStream recipes, reused by Dakota without a second SDK.
# This is a recipe snapshot, not a COSMIC release version lock.
# The upstream COSMIC source refs must be reconciled to the official
# stable cosmic-epoch manifest before production builds.
kind: junction

sources:
- kind: git_repo
  url: github:RazorfinOS-org/cosmic-build-meta.git
  track: main
  ref: 83aec8dac411da245077ecdd7fcf1641ec4c5aa6

config:
  options:
    arch: '%{arch}'
    x86_64_v3: false
    gaming: false
  overrides:
    # Dakota already owns FDSDK 26.08 + Linux 6.18 LTS.
    # Do not bring Razorfin's kernel and SDK overrides into this build.
    freedesktop-sdk.bst: freedesktop-sdk.bst
