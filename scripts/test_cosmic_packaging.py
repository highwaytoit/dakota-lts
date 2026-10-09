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

    def test_viewer_has_a_real_make_binary_for_cmake_generator(self):
        recipe = (ROOT / "elements" / "cosmic-core" /
                  "cosmic-viewer.bst").read_text(encoding="utf-8")
        build_deps = recipe.split("build-depends:\n", 1)[1].split(
            "\ndepends:\n", 1
        )[0]
        self.assertEqual(
            build_deps.count("- freedesktop-sdk.bst:components/make.bst"),
            1,
        )
        self.assertIn("- freedesktop-sdk.bst:components/cmake.bst", build_deps)

    def test_full_mesa_uses_verified_cosmic_source_plugin(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "cosmic-mesa-build.yml").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/cosmic_ci_plugin.py", workflow)
        self.assertIn("python3 -m unittest discover -s scripts", workflow)
        self.assertIn("just bst build cosmic/image.bst", workflow)
        self.assertIn("Verify COSMIC Mesa OCI graph", workflow)
        self.assertNotIn("podman push", workflow)
        self.assertNotIn("docker push", workflow)
        self.assertNotIn("podman system prune", workflow)

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
