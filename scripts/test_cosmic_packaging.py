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

    def test_full_cosmic_uses_verified_cosmic_source_plugin(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "cosmic-build.yml").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/cosmic_ci_plugin.py", workflow)
        self.assertIn("python3 -m unittest discover -s scripts", workflow)
        self.assertIn("just bst build cosmic/image.bst", workflow)
        self.assertIn("Verify COSMIC OCI graph", workflow)
        self.assertNotIn("podman push", workflow)
        self.assertNotIn("docker push", workflow)
        self.assertNotIn("podman system prune", workflow)


    def test_nvidia_build_reuses_dakota_driver_without_gnome_stack(self):
        system = (ROOT / "elements" / "cosmic" / "nvidia-system.bst").read_text(encoding="utf-8")
        self.assertIn("- cosmic/system.bst", system)
        self.assertIn("- bluefin-nvidia/nvidia-drivers.bst", system)
        self.assertIn("- bluefin-nvidia/nvidia-kargs.bst", system)
        self.assertIn("- bluefin-nvidia/nvidia-modprobe-config.bst", system)
        self.assertIn("- bluefin-nvidia/nvidia-device-nodes.bst", system)
        self.assertIn("depmod -a", system)
        self.assertIn("6.18.*", system)
        self.assertNotIn("bluefin-nvidia/deps.bst", system)
        self.assertNotIn("bluefin-nvidia/os-release.bst", system)
        self.assertNotIn("oci/layers/bluefin", system)
        self.assertNotIn("cosmic-deps-nvidia/", system)

    def test_nvidia_oci_is_separate_unpublished_cosmic_edition(self):
        cosmic = (ROOT / "elements" / "cosmic")
        image = (cosmic / "nvidia-image.bst").read_text(encoding="utf-8")
        fs = (cosmic / "nvidia-filesystem.bst").read_text(encoding="utf-8")
        init = (cosmic / "nvidia-init-scripts.bst").read_text(encoding="utf-8")
        self.assertIn("- cosmic/nvidia-init-scripts.bst", image)
        self.assertIn("filename: cosmic/nvidia-filesystem.bst", image)
        self.assertIn("freedesktop-sdk.bst:oci/platform-oci.bst", image)
        self.assertIn("Dakota COSMIC NVIDIA (experimental)", image)
        self.assertIn("LicenseRef-NVIDIA-SLA", image)
        self.assertIn("nvidia-drm_gbm.so", image)
        self.assertIn("- cosmic/nvidia-system.bst", fs)
        self.assertIn("bootc-defaults-cosmic-nvidia.bst", fs)
        self.assertIn("- cosmic/nvidia-system.bst", init)
        self.assertNotIn("oci/bluefin", image)

    def test_nvidia_ci_reuses_worker_with_no_publication_or_pruning(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "cosmic-nvidia-build.yml").read_text(encoding="utf-8")
        self.assertIn("runs-on: [self-hosted, Linux, X64, dakota-worker]", workflow)
        self.assertIn("group: dakota-testing-lts-worker", workflow)
        self.assertIn("python3 scripts/cosmic_source_sync.py --write", workflow)
        self.assertIn("python3 scripts/cosmic_ci_plugin.py", workflow)
        self.assertIn("just bst build cosmic/nvidia-image.bst", workflow)
        self.assertIn("core/linux-fdsdk.bst", workflow)
        self.assertIn("bluefin-nvidia/nvidia-drivers.bst", workflow)
        self.assertIn("scripts/resolve_nvidia_lts.py", workflow)
        for forbidden in ("podman push", "docker push", "podman system prune",
                          "podman image prune", "sudo podman system reset"):
            self.assertNotIn(forbidden, workflow)

    def test_nvidia_cache_check_strips_ansi_colors(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "cosmic-nvidia-build.yml").read_text(encoding="utf-8")
        self.assertIn('re.sub(r"\\x1b\\[[0-9;]*m"', workflow)
        self.assertNotIn('re.sub(r"\\\\x1b\\\\[[0-9;]*m"', workflow)
        self.assertIn('states == ["cached"]', workflow)

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
