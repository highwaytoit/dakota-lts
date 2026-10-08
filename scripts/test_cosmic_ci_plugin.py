#!/usr/bin/env python3
"""Offline guardrails for COSMIC-only CI plugin selection."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cosmic_ci_plugin as plugin


class CosmicPluginIsolationTests(unittest.TestCase):
    def test_plugin_selection_in_ephemeral_copy(self):
        source = (Path(__file__).resolve().parent.parent / "project.conf").read_text(
            encoding="utf-8")
        edited = plugin.select_cosmic_plugin(source)
        self.assertIn("    junction: cosmic-build-meta.bst\n    sources:\n      - cargo2", edited)
        self.assertIn("    junction: plugins/buildstream-plugins-community.bst", edited)
        self.assertIn("    junction: gnome-build-meta.bst", edited)
        self.assertEqual(edited.count("      - cargo2\n"), 1)
        self.assertEqual(edited.count("      - gen_cargo_lock\n"), 1)
        self.assertNotEqual(source, edited)

    def test_fail_closed_on_unrecognized_project_layout(self):
        with self.assertRaises(ValueError):
            plugin.select_cosmic_plugin("plugins: []\n")

    def test_second_application_refused(self):
        original = (Path(__file__).resolve().parent.parent / "project.conf").read_text(
            encoding="utf-8")
        first = plugin.select_cosmic_plugin(original)
        with self.assertRaises(ValueError):
            plugin.select_cosmic_plugin(first)


if __name__ == "__main__":
    unittest.main()
