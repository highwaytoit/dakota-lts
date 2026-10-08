# Graph-only target for Razorfin's COSMIC bootc runtime stack with Dakota's
# SDK/kernel junction and all four missing stable COSMIC components.
# Stage 3 validates this graph. OCI packaging/publishing come later.
kind: stack

depends:
- cosmic-build-meta.bst:oci/cosmic/stack.bst
- cosmic-core/deps.bst
