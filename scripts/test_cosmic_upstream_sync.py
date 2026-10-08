#!/usr/bin/env python3
"""Offline tests for generated COSMIC patch to the Razorfin junction."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cosmic_upstream_sync as upstream
from cosmic_release_audit import AuditError


class UpstreamSyncTests(unittest.TestCase):
    def setUp(self):
        self.component = {
            "name": "cosmic-comp",
            "path": "cosmic-comp",
            "id": "pop-os/cosmic-comp",
            "sha": "b" * 40,
        }
        self.source = """kind: manual
sources:
- kind: git_repo
  url: github:pop-os/cosmic-comp.git
  track: master
  ref: epoch-1.10.0-1-gaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
- kind: cargo2
  url: "crates:"
  ref:
  - kind: registry
    name: old
    version: 0.1
    sha: 1234
config:
  build-commands:
  - just build-release
"""

    def rust_lock(self):
        items = [
            "[[package]]\nname = 'crate%d'\nversion = '1.0.0'\n"
            "source = 'registry+https://github.com/rust-lang/crates.io-index'\n"
            "checksum = '%064x'\n" % (i, i + 1)
            for i in range(20)
        ]
        return "version = 4\n\n" + "\n".join(items)

    def test_rewrites_git_and_cargo_sources_from_release(self):
        s = upstream.update_recipe(self.source, self.component,
                                   "epoch-1.10.0", self.rust_lock())
        self.assertIn("ref: epoch-1.10.0-0-g" + "b" * 40, s)
        self.assertIn("name: 'crate0'", s)
        self.assertNotIn("name: old", s)
        self.assertIn("config:\n  build-commands:", s)

    def test_preserves_unrelated_sidecar_source(self):
        s = self.source.replace("- kind: cargo2", """- kind: remote
  url: github-raw:some/asset.jpg
  ref: 1234
- kind: cargo2""")
        actual = upstream.update_recipe(s, self.component,
                                        "epoch-1.10.0", self.rust_lock())
        self.assertIn("url: github-raw:some/asset.jpg", actual)
        self.assertIn("ref: 1234", actual)
        self.assertIn("name: 'crate0'", actual)

    def test_wrong_recipe_repository_fails(self):
        s = self.source.replace("github:pop-os/cosmic-comp.git",
                                "github:somebody/cosmic-comp.git")
        with self.assertRaises(AuditError):
            upstream.update_recipe(s, self.component,
                                   "epoch-1.10.0", self.rust_lock())

    def test_no_cargo_recipe_keeps_other_fields(self):
        s = """kind: manual
sources:
- kind: git_repo
  url: github:pop-os/cosmic-comp.git
  track: master
  ref: epoch-1.9.0-0-gaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
config:
  build-commands: []
"""
        actual = upstream.update_recipe(s, self.component, "epoch-1.10.0", None)
        self.assertIn("ref: epoch-1.10.0-0-g" + "b" * 40, actual)
        self.assertIn("config:\n  build-commands: []", actual)

    def test_generated_patch_is_a_git_apply_compatible_diff(self):
        no_cargo = self.source[:self.source.index("- kind: cargo2")] + """config:
  build-commands: []
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = root / "cosmic-core"
            overlay.mkdir()
            (overlay / "deps.bst").write_text("kind: stack\n", encoding="utf-8")
            dest = root / "patches" / "0001.patch"
            report = root / "report.json"
            with patch.object(upstream, "source_text", return_value=no_cargo):
                result = upstream.generate(
                    "a" * 40, {"release": "epoch-1.10.0",
                               "components": [self.component]},
                    output=str(dest), report=str(report),
                    overlay_dir=str(overlay))
            content = dest.read_text(encoding="utf-8")
            self.assertEqual(len(result), 1)
            self.assertIn("diff --git a/elements/core/cosmic-comp.bst", content)
            self.assertIn("--- a/elements/core/cosmic-comp.bst", content)
            self.assertIn("+++ b/elements/core/cosmic-comp.bst", content)
            self.assertTrue(report.is_file())

    def test_supplemental_component_is_discovered_not_manually_listed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            overlay = root / "cosmic-core"
            overlay.mkdir()
            (overlay / "deps.bst").write_text("kind: stack\n", encoding="utf-8")
            (overlay / "cosmic-comp.bst").write_text("kind: manual\n", encoding="utf-8")
            dest = root / "patches" / "0001.patch"
            with patch.object(upstream, "source_text") as fn:
                result = upstream.generate(
                    "a" * 40, {"release": "epoch-1.10.0",
                               "components": [self.component]},
                    output=str(dest), report=None,
                    overlay_dir=str(overlay))
            self.assertEqual(result, [])
            fn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
