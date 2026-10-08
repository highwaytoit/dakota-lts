# Reuse the complete COSMIC desktop that Razorfin packages, plus Dakota's
# supplemental components discovered from System76's stable Epoch manifest.
# This is not a standalone bootable image; it is a graph-resolution target.
kind: stack

depends:
- cosmic-build-meta.bst:core/public-stacks/cosmic-full.bst
- cosmic-core/deps.bst
