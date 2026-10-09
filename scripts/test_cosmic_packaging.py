#!/usr/bin/env python3
"""Offline checks for Dakota's supplemental COSMIC packaging and CI isolation."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
COMPONENTS = ("cosmic-monitor", "cosmic-osk", "cosmic-viewer")


class CosmicPackagingTests(unittest.TestCase):
    def test_strip_tool_is_staged_in_all_three_rust_recipes(self):
        for name in COMPONENTS:
            with self.subTest(component=name):
                text = (ROOT / "elements" / "cosmic-core" / (name + ".bst")).read_text(
                    encoding="utf-8"
                )
                dependencies = text.split("build-depends:\n", 1)[1].split(
                    "\ndepends:\n", 1
                )[0]
                self.assertEqual(
                    dependencies.count("- freedesktop-sdk.bst:components/stripper.bst"),
                    1,
                )
                self.assertIn("  - '%{strip-binaries}'", text)
                self.assertNotIn("strip-binaries: ''", text)

    def test_individual_build_failures_do_not_skip_following_components(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "cosmic-component-validation.yml").read_text(encoding="utf-8")
        for name in ("compositor", "monitor", "osk", "viewer"):
            with self.subTest(component=name):
                self.assertIn("id: " + name + "\n", workflow)
        self.assertEqual(workflow.count("continue-on-error: true"), 4)
        self.assertIn("Verify all individual components succeeded", workflow)
        self.assertIn("if: always()", workflow)
        self.assertNotIn("ghcr.io", workflow)
        self.assertNotIn("podman system prune", workflow)


if __name__ == "__main__":
    unittest.main()
