# COSMIC stable release discovery — experimental

Scope: `cosmic-lts-integration` only. This is a source-audit tool, not an
OS build, a GNOME change, a driver update, or an automated package generator.

## Source of truth

System76's latest stable `pop-os/cosmic-epoch` GitHub release
(`epoch-X.Y.Z`) determines the upstream release. We peel the annotated tag,
read its root Git tree, and collect only actual `160000` submodule gitlinks.
Their repository identities come from that release's `.gitmodules`.

We compare the full component inventory with the accepted baseline
(`release-baseline.json`). The baseline records *what we last accepted*,
not the version that a future image must use. Each audit resolves the newest
stable release afresh. Every source SHA is reported for reproducibility.

Crucial distinction: the upstream release's component list is **not** a
complete list of packages, dependencies or desktop applications. System76
ships supporting libraries and packaging outside that submodule list. This
audit can guarantee coverage of the release's listed submodules only.

## Conservative initial rules

- **Stop** when any previously accepted component disappears, even if the
  total number of components did not decrease.
- **Stop** when the component count decreases.
- **Stop** when an upstream component has no matching BuildStream recipe, or
  has a recipe but is not represented in the COSMIC desktop stacks.
- **Continue** when source revisions change without missing components.
- **Continue** when components are added and they have packaged/stacked recipes.
- Compare upstream repository identities instead of paths, so legitimate
  submodule directory renames do not count as removals.
- A failed GitHub lookup, malformed manifest, or unsupported submodule URL
  is an error; never silently continue with an incomplete component list.

A component might be provided indirectly by another upstream package or
stack. The coverage check is intentionally conservative; investigate false
positives rather than silently create an exception list.

## Running

From Dakota's repository root, sync the latest official stable source
revisions and matching Rust Cargo.lock snapshots before BuildStream runs:

- `python3 scripts/cosmic_source_sync.py --write`
- `python3 scripts/cosmic_release_audit.py --report cosmic-audit.json`
- `python3 scripts/cosmic_upstream_sync.py`
- `python3 -m unittest discover -s scripts -p 'test_cosmic_*.py' -v`

The GitHub-hosted audit job verifies the release and generates the source
patch; the existing Dakota worker repeats both synchronizers before it
runs BuildStream graph checks. These files live only in the ephemeral
checkout, are never pushed to GitHub, and do not publish images.
Every later image-build job must follow the same order.

The audit currently combines Razorfin's `main` packaging inventory with
Dakota's four supplemental recipes in `elements/cosmic-core/`, including
`elements/cosmic-core/deps.bst`. Razorfin is only a packaging reference;
the official tagged COSMIC Epoch tree defines the component inventory.

To accept a newer stable release as the next comparison baseline, run
`python3 scripts/cosmic_release_audit.py --accept` after the source sync
and after any missing components have been packaged. This will fail if any
blocking change is unresolved. Keep baseline acceptance a reviewed action.

The pinned Razorfin BuildStream subproject is consumed via
`elements/cosmic-build-meta.bst` with Dakota's freedesktop-sdk and
BuildStream plugin junctions. The upstream source synchronizer checks
**all** Razorfin COSMIC component recipes against the tagged stable Epoch
manifest and generates a local Git patch for any changed source revisions
(and their matching Rust Cargo.lock dependencies). Already-correct recipes
are left untouched. The patch is applied by BuildStream's patch_queue
source, never committed to Dakota or pushed to Razorfin.

`cosmic/desktop.bst` and `cosmic/system.bst` are graph-only targets.
Both graph checks passed on Dakota's existing worker (565 and 840 elements,
respectively), including all four supplemental components and the shared
`core/linux-fdsdk.bst` kernel. **No COSMIC source binaries, OCI images,
boot tests, or NVIDIA COSMIC variants have been built yet.**

## Verified initial reference

COSMIC Epoch 1.10.0 (October 8, 2026): **30** actual tagged Git submodules,
compared against Razorfin's existing `core/` BuildStream recipes:
26 were already available; four supplemental recipe definitions were added
to Dakota's experimental branch:

- `pop-os/cosmic-monitor`
- `pop-os/cosmic-osk`
- `pop-os/cosmic-sound-theme`
- `pop-os/cosmic-viewer`

The initial live audit correctly stopped on these four entries. After
the supplemental recipes and per-component Rust lockfile sync were added,
the live inventory audit passed. Actual BuildStream compilation remains
unverified.

Release source:
https://github.com/pop-os/cosmic-epoch/releases/tag/epoch-1.10.0

Packaging reference:
https://github.com/RazorfinOS-org/cosmic-build-meta
