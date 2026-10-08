#!/usr/bin/env python3
"""Offline tests for safe, deterministic COSMIC Rust source synchronization."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cosmic_release_audit as audit
import cosmic_source_sync as sync


class CosmicSourceSyncTests(unittest.TestCase):
    def test_exact_registry_and_git_lock_references(self):
        packages = ["[[package]]\nname = 'pkg%d'\nversion = '1.0.0'\nsource = 'registry+https://github.com/rust-lang/crates.io-index'\nchecksum = '%064x'\n" % (i, i + 1) for i in range(20)]
        packages += ["""[[package]]
name = 'libcosmic'
version = '1.0.0'
source = 'git+https://github.com/pop-os/libcosmic.git?rev=abc#0123456789abcdef0123456789abcdef01234567'
"""]
        refs = sync.rust_refs("version = 4\n\n" + "\n".join(packages))
        self.assertEqual(len(refs), 21)
        cosm = next(v for v in refs if v["name"] == "libcosmic")
        self.assertEqual(cosm["repo"], "github:pop-os/libcosmic")
        self.assertEqual(cosm["query"], {"rev": "abc"})
        self.assertEqual(cosm["commit"], "0123456789abcdef0123456789abcdef01234567")
        self.assertEqual(sync.dump_refs(refs).count('  - kind:'), 21)

    def test_git_dependency_double_slash_is_normalized(self):
        registry = "\n".join(
            "[[package]]\nname = 'pkg%d'\nversion = '1.0.0'\nsource = 'registry+https://github.com/rust-lang/crates.io-index'\nchecksum = '%064x'\n" % (i, i + 1)
            for i in range(20))
        git = """[[package]]
name = 'cosmic-protocols'
version = '0.1.0'
source = 'git+https://github.com/pop-os//cosmic-protocols?branch=main#c0cff4db14c37ed954983158e4055aa94c7741d9'
"""
        refs = sync.rust_refs("version = 4\n\n" + registry + "\n" + git)
        component = next(x for x in refs if x["name"] == "cosmic-protocols")
        self.assertEqual(component["repo"], "github:pop-os/cosmic-protocols")
        self.assertEqual(component["query"], {"branch": "main"})

    def test_registry_checksum_required(self):
        lock = "version = 4\n\n" + "\n".join(
            "[[package]]\nname = 'pkg%d'\nversion = '1.0.0'\nsource = 'registry+https://github.com/rust-lang/crates.io-index'\n" % i
            for i in range(20))
        with self.assertRaises(audit.AuditError):
            sync.rust_refs(lock)

    def test_gitlab_freedesktop_rust_dependency(self):
        registry = "\n".join(
            "[[package]]\nname = 'pkg%d'\nversion = '1.0.0'\nsource = 'registry+https://github.com/rust-lang/crates.io-index'\nchecksum = '%064x'\n" % (i, i + 1)
            for i in range(20))
        freedesktop = """[[package]]
name = 'pipewire-rs'
version = '0.1.0'
source = 'git+https://gitlab.freedesktop.org/pipewire/pipewire-rs#71022422eebd1bb2cb5a3259362819639fd29b58'
"""
        refs = sync.rust_refs("version = 4\n\n" + registry + "\n" + freedesktop)
        match = next(x for x in refs if x["name"] == "pipewire-rs")
        self.assertEqual(match["repo"], "freedesktop:pipewire/pipewire-rs")

    def test_wrong_git_host_not_silently_ignored(self):
        lock = "version = 4\n\n" + "\n".join(
            "[[package]]\nname = 'pkg%d'\nversion = '1.0.0'\nsource = 'git+https://example.com/fork/repo#0123456789abcdef0123456789abcdef01234567'\n" % i
            for i in range(20))
        with self.assertRaises(audit.AuditError):
            sync.rust_refs(lock)

    def test_recipe_refreshes_exact_upstream_commit(self):
        recipe = """kind: manual
sources:
- kind: git_repo
  url: github:pop-os/cosmic-monitor.git
  track: epoch-1.*
  ref: epoch-1.9.0-0-g1111111111111111111111111111111111111111
- kind: cargo2
  url: 'crates:'
  vendor-dir: .vendored
  ref: []

config:
  install-commands: []
"""
        refs = [{"kind": "registry", "name": "x", "version": "1.2",
                 "sha": "a" * 64}]
        new = sync.update_recipe(recipe, "cosmic-monitor",
                                 "epoch-1.10.0", "b" * 40, refs)
        self.assertIn("ref: epoch-1.10.0-0-g" + ("b" * 40), new)
        self.assertIn("name: 'x'", new)
        self.assertIn("sha: '" + ("a" * 64) + "'", new)
        self.assertNotIn("ref: []", new)
        self.assertIn("url: 'crates:'", new)
        self.assertNotIn("url: crates:", new)
        self.assertIn("config:\n  install-commands: []", new)

    def test_overlay_excludes_unresolved_cargo_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "deps.bst").write_text("kind: stack\ndepends:\n- cosmic-core/cosmic-monitor.bst\n")
            (p / "cosmic-monitor.bst").write_text("kind: manual\nsources:\n- kind: git_repo\n  ref: xx\n- kind: cargo2\n  ref: []\n")
            recipes, included = audit.overlay_inventory(p)
            self.assertNotIn("cosmic-monitor", recipes)
            self.assertIn("cosmic-monitor", included)

    def test_unchanged_recipe_sync_is_deterministic(self):
        recipe = """kind: meson\nsources:\n- kind: git_repo\n  ref: epoch-1.10.0-0-g%s\n""" % ("a" * 40)
        result = sync.update_recipe(recipe, "cosmic-sound-theme",
                                    "epoch-1.10.0", "a" * 40, [])
        self.assertEqual(result, recipe)


if __name__ == "__main__":
    unittest.main()
