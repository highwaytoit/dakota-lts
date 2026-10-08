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

From the Dakota repository root:

- `python3 scripts/cosmic_release_audit.py --report cosmic-audit.json`
- `python3 -m unittest scripts/test_cosmic_release_audit.py`

Until local COSMIC elements are integrated, the audit uses Razorfin's
`main` branch as the **packaging reference only**, not as the authority
for which components belong to an official stable release.

After integrating local COSMIC recipes, use:
`python3 scripts/cosmic_release_audit.py --core-dir elements/core --report cosmic-audit.json`

To accept a newer stable release as the next comparison baseline, run
`python3 scripts/cosmic_release_audit.py --core-dir elements/core --accept`.
That action is intentionally explicit and will **not** run if there are
unresolved blockers. Do not automate baseline acceptance or publishing
without a separate reviewed change.

The audit currently reads the upstream source SHAs and reports them. It does
**not yet rewrite BuildStream `git_repo` refs or Rust `cargo2` source metadata**.
That wiring belongs to the later COSMIC integration work; do not claim a
successful audit proves that a build uses the reported revisions.

## Verified initial reference

COSMIC Epoch 1.10.0 (October 8, 2026): **30** actual tagged Git submodules,
compared against Razorfin's existing `core/` BuildStream recipes:
26 recognized; four missing packaging recipes:

- `pop-os/cosmic-monitor`
- `pop-os/cosmic-osk`
- `pop-os/cosmic-sound-theme`
- `pop-os/cosmic-viewer`

The conservative first audit is therefore expected to stop. This is the
correct result, and the missing items become inputs to integration work.

Release source:
https://github.com/pop-os/cosmic-epoch/releases/tag/epoch-1.10.0

Packaging reference:
https://github.com/RazorfinOS-org/cosmic-build-meta
