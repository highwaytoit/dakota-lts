# Generated COSMIC source patch directory

The experimental COSMIC CI workflow generates
`0001-upstream-stable-cosmic.patch` here **locally**, from the official
System76 stable Epoch release, before it runs BuildStream.

The patch directory is created at runtime, and contains only patch files.

The generated patch overrides Razorfin's individual COSMIC recipe source
revisions and Rust Cargo.lock snapshots. It is not committed, does not
modify the Razorfin GitHub repository, and has no effect on GNOME.

If the release or upstream recipe structure is incompatible, generation
must fail rather than silently omit a component.

Do not manually edit this patch; review the accompanying source report.
