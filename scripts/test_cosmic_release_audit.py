#!/usr/bin/env python3
"""Offline regression tests for the COSMIC stable release audit."""
import base64
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cosmic_release_audit as audit


def component(name, *, identity=None, path=None, sha="1" * 40):
    return {
        "id": identity or f"pop-os/{name}",
        "name": name,
        "path": path or name,
        "sha": sha,
    }


def manifest(tag, components):
    return {"release": tag, "commit": "0" * 40, "components": components}


class CosmicReleaseAuditTests(unittest.TestCase):
    def setUp(self):
        self.original = manifest("epoch-1.8.0", [
            component("cosmic-comp"),
            component("cosmic-panel"),
        ])
        self.recipes = {"cosmic-comp", "cosmic-panel"}
        self.included = set(self.recipes)

    def test_same_components_new_versions_pass(self):
        updated = manifest("epoch-1.9.0", [
            component("cosmic-comp", sha="2" * 40),
            component("cosmic-panel"),
        ])
        report = audit.check(updated, self.original, self.recipes, self.included)
        self.assertFalse(report["blockers"])
        self.assertEqual(report["changes"]["updated"], ["pop-os/cosmic-comp"])

    def test_added_component_with_recipe_passes(self):
        updated = manifest("epoch-1.9.0", [
            *self.original["components"], component("cosmic-viewer")
        ])
        self.recipes.add("cosmic-viewer")
        self.included.add("cosmic-viewer")
        report = audit.check(updated, self.original, self.recipes, self.included)
        self.assertEqual(report["current_count"], 3)
        self.assertFalse(report["blockers"])
        self.assertEqual([x["id"] for x in report["changes"]["added"]],
                         ["pop-os/cosmic-viewer"])

    def test_added_component_without_recipe_stops(self):
        updated = manifest("epoch-1.9.0", [
            *self.original["components"], component("cosmic-viewer")
        ])
        report = audit.check(updated, self.original, self.recipes, self.included)
        self.assertIn("MISSING_RECIPES", report["blockers"])
        self.assertIn("pop-os/cosmic-viewer", report["missing_recipes"])

    def test_existing_recipe_not_shipped_stops(self):
        updated = manifest("epoch-1.9.0", [
            *self.original["components"], component("cosmic-viewer")
        ])
        self.recipes.add("cosmic-viewer")
        report = audit.check(updated, self.original, self.recipes, self.included)
        self.assertIn("NOT_IN_COSMIC_STACK", report["blockers"])
        self.assertIn("pop-os/cosmic-viewer", report["not_in_cosmic_stack"])

    def test_decreasing_count_stops(self):
        updated = manifest("epoch-1.9.0", [component("cosmic-comp")])
        report = audit.check(updated, self.original, self.recipes, self.included)
        self.assertIn("COMPONENT_COUNT_DECREASED", report["blockers"])
        self.assertIn("COMPONENT_REMOVED", report["blockers"])

    def test_component_replacement_at_equal_count_stops(self):
        updated = manifest("epoch-1.9.0", [
            component("cosmic-comp"), component("cosmic-viewer")
        ])
        self.recipes.add("cosmic-viewer")
        self.included.add("cosmic-viewer")
        report = audit.check(updated, self.original, self.recipes, self.included)
        self.assertEqual(report["current_count"], report["reference_count"])
        self.assertIn("COMPONENT_REMOVED", report["blockers"])

    def test_directory_rename_same_repo_identity_passes(self):
        renamed = component("cosmic-applibrary", path="cosmic-app-library",
                            identity="pop-os/cosmic-applibrary")
        before = manifest("epoch-1.9.0", [
            component("cosmic-applibrary", identity="pop-os/cosmic-applibrary")
        ])
        after = manifest("epoch-1.10.0", [renamed])
        report = audit.check(after, before, {"cosmic-applibrary"},
                             {"cosmic-applibrary"})
        self.assertFalse(report["blockers"])
        self.assertEqual(report["changes"]["renamed"][0]["new_path"],
                         "cosmic-app-library")

    def test_gitmodules_normalizes_git_urls(self):
        text = '''[submodule "cosmic-viewer"]
    path = cosmic-viewer
    url = https://github.com/pop-os/cosmic-viewer.git
[submodule "simple-wrapper"]
    path = simple-wrapper
    url = https://github.com/pop-os/simple-wrapper
'''
        entries = audit.parse_gitmodules(text)
        self.assertEqual(entries["cosmic-viewer"]["id"], "pop-os/cosmic-viewer")
        self.assertEqual(entries["simple-wrapper"]["id"], "pop-os/simple-wrapper")

    def test_unknown_submodule_url_fails_closed(self):
        with self.assertRaises(audit.AuditError):
            audit.parse_gitmodules('''[submodule "bad"]
    path = bad
    url = https://example.com/foreign/component
''')

    def test_nonstable_release_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.release_manifest("epoch-1.11.0-beta.1")

    def test_manifest_only_uses_actual_gitlinks(self):
        gitmodules = '''[submodule "cosmic-panel"]
    path = cosmic-panel
    url = https://github.com/pop-os/cosmic-panel
[submodule "simple-wrapper"]
    path = simple-wrapper
    url = https://github.com/pop-os/simple-wrapper
'''
        metadata = {
            "encoding": "base64",
            "content": base64.b64encode(gitmodules.encode()).decode()
        }
        tree = {"tree": [
            {"path": "cosmic-panel", "type": "commit", "mode": "160000",
             "sha": "1" * 40},
            {"path": "README.md", "type": "blob", "mode": "100644",
             "sha": "2" * 40},
        ]}
        def mock_get(path):
            if "/git/ref/tags/" in path:
                return {"object": {"sha": "a" * 40, "type": "commit"}}
            if "/git/trees/" in path:
                return tree
            if "/contents/.gitmodules" in path:
                return metadata
            raise AssertionError("Unexpected GitHub path: " + path)
        with patch.object(audit, "get_json", side_effect=mock_get):
            result = audit.release_manifest("epoch-1.10.0")
        self.assertEqual(len(result["components"]), 1)
        self.assertEqual(result["components"][0]["id"], "pop-os/cosmic-panel")


if __name__ == "__main__":
    unittest.main()
