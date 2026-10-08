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
revisions and matching Rust Cargo.lock snapshots **before** the audit:

- `python3 scripts/cosmic_source_sync.py --write`
- `python3 scripts/cosmic_release_audit.py --report cosmic-audit.json`
- `python3 -m unittest discover -s scripts -p 'test_cosmic_*.py' -v`

The CI workflow runs the same sequence on an ephemeral GitHub-hosted worker.
It does not push synced snapshots or published images. The source sync edits
only the worker's local checkout. A later image workflow must likewise run
the sync before BuildStream resolves or builds the graph.

The audit currently combines Razorfin's `main` packaging inventory with
Dakota's four supplemental recipes in `elements/cosmic-core/`, including
`elements/cosmic-core/deps.bst`. Razorfin is only a packaging reference;
the official tagged COSMIC Epoch tree defines the component inventory.

To accept a newer stable release as the next comparison baseline, run
`python3 scripts/cosmic_release_audit.py --accept` after the source sync
and after any missing components have been packaged. This will fail if any
blocking change is unresolved. Keep baseline acceptance a reviewed action.

These steps **do not yet synchronize Razorfin's 26 existing recipe source
revisions** into a Dakota-owned BuildStream graph. The four supplemental
recipes are ready for BuildStream graph integration, but have not been
built. Graph wiring, upstream-source revision control for all recipes,
Rust plugin compatibility, dependency checks, and OCI image builds are
separate milestones. A green inventory audit is not proof of a bootable
COSMIC image.

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
