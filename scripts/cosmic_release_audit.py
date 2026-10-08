#!/usr/bin/env python3
"""Audit the latest stable COSMIC Epoch component set against BuildStream recipes.

Only the tagged upstream Git tree defines the component set. Razorfin's recipe
inventory is a temporary packaging reference; use --core-dir after integration.
No repository files are changed unless --accept is explicitly requested.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


API = "https://api.github.com"
STABLE_TAG = re.compile(r"^epoch-(\d+)\.(\d+)\.(\d+)$")
RECIPE = re.compile(r"^elements/core/([^/]+)\.bst$")
STACK_COMPONENT = re.compile(r"^\s*-\s+core/([^/\s]+)\.bst(?:\s*(?:#.*)?)?$", re.M)
STACK_FILES = ("cosmic-full", "cosmic-session", "cosmic-apps")
REFERENCE_REPO = "RazorfinOS-org/cosmic-build-meta"


class AuditError(Exception):
    pass


def get_json(path):
    url = API + path
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "dakota-cosmic-release-audit"}
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            return json.load(response)
    except (HTTPError, URLError, ValueError) as exc:
        raise AuditError(f"GitHub request failed ({url}): {exc}") from exc


def tagged_commit(tag):
    obj = get_json("/repos/pop-os/cosmic-epoch/git/ref/tags/" + quote(tag))["object"]
    for _ in range(5):
        if obj["type"] == "commit":
            return obj["sha"]
        if obj["type"] != "tag":
            break
        obj = get_json("/repos/pop-os/cosmic-epoch/git/tags/" + obj["sha"])["object"]
    raise AuditError(f"Cannot resolve {tag} to a Git commit")


def github_identity(url):
    parsed = urlparse(url.strip().rstrip("/"))
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise AuditError(f"Unsupported COSMIC submodule URL: {url}")
    value = parsed.path.strip("/").removesuffix(".git").lower()
    if len(value.split("/")) != 2:
        raise AuditError(f"Invalid COSMIC repository identity: {url}")
    return value


def parse_gitmodules(text):
    # .gitmodules is Git config, not INI: upstream can indent a "path" with
    # tabs and the following "url" with spaces. ConfigParser incorrectly
    # interprets that as a multiline value.
    sections = {}
    current = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        section = re.fullmatch(r'\[submodule "([^"]+)"\]', line)
        if section:
            current = section.group(1)
            if current in sections:
                raise AuditError(f"Duplicate .gitmodules section: {current}")
            sections[current] = {}
            continue
        if line.startswith("["):
            current = None
            continue
        if current is None:
            raise AuditError(f"Unexpected .gitmodules content: {line}")
        if "=" not in line:
            raise AuditError(f"Invalid .gitmodules assignment: {line}")
        key, value = (item.strip() for item in line.split("=", 1))
        if key in sections[current]:
            raise AuditError(f"Duplicate .gitmodules key: {current}.{key}")
        sections[current][key] = value

    mapping = {}
    for name, options in sections.items():
        path = options.get("path")
        url = options.get("url")
        if not path or not url or path in mapping:
            raise AuditError(f"Invalid or duplicate .gitmodules entry: {name}")
        mapping[path] = {"name": name, "id": github_identity(url)}
    return mapping

def release_manifest(tag):
    if not STABLE_TAG.fullmatch(tag):
        raise AuditError(f"Not a stable COSMIC Epoch tag: {tag}")
    commit = tagged_commit(tag)
    tree = get_json("/repos/pop-os/cosmic-epoch/git/trees/" + commit)["tree"]
    raw = get_json("/repos/pop-os/cosmic-epoch/contents/.gitmodules?ref=" + quote(commit))
    if raw.get("encoding") != "base64":
        raise AuditError("Unexpected .gitmodules content encoding")
    modules = parse_gitmodules(base64.b64decode(raw["content"]).decode("utf-8"))
    components = []
    identities = set()
    for item in tree:
        if item.get("mode") != "160000" or item.get("type") != "commit":
            continue
        path = item["path"]
        if path not in modules:
            raise AuditError(f"Upstream component {path} is missing from .gitmodules")
        entry = modules[path]
        if entry["id"] in identities:
            raise AuditError(f"Duplicate component identity: {entry['id']}")
        identities.add(entry["id"])
        components.append({
            "id": entry["id"],
            "name": entry["name"],
            "path": path,
            "sha": item["sha"],
        })
    if not components:
        raise AuditError("Stable COSMIC release has no Git submodule commits")
    return {"release": tag, "commit": commit,
            "components": sorted(components, key=lambda x: x["id"])}


def latest_stable():
    release = get_json("/repos/pop-os/cosmic-epoch/releases/latest")
    tag = release.get("tag_name", "")
    if release.get("draft") or release.get("prerelease") or not STABLE_TAG.fullmatch(tag):
        raise AuditError(f"Latest GitHub release is not a stable COSMIC Epoch tag: {tag}")
    return tag


def recipe_names_from_paths(paths):
    return {m.group(1) for p in paths if (m := RECIPE.fullmatch(p))}


def remote_inventory(repo, ref):
    tree = get_json("/repos/" + repo + "/git/trees/" + quote(ref) + "?recursive=1")
    if tree.get("truncated"):
        raise AuditError("Recipe inventory Git tree was truncated")
    recipes = recipe_names_from_paths(v["path"] for v in tree["tree"])
    included = set()
    for name in STACK_FILES:
        file = get_json("/repos/" + repo + "/contents/elements/core/public-stacks/" +
                        name + ".bst?ref=" + quote(ref))
        if file.get("encoding") != "base64":
            raise AuditError(f"Cannot read {name}.bst stack")
        content = base64.b64decode(file["content"]).decode("utf-8")
        included.update(STACK_COMPONENT.findall(content))
    return recipes, included


def local_inventory(core_dir):
    root = Path(core_dir)
    if not root.is_dir():
        raise AuditError(f"Missing local core recipe directory: {root}")
    recipes = {p.stem for p in root.glob("*.bst")}
    included = set()
    for name in STACK_FILES:
        path = root / "public-stacks" / (name + ".bst")
        if not path.is_file():
            raise AuditError(f"Missing local COSMIC stack: {path}")
        included.update(STACK_COMPONENT.findall(path.read_text(encoding="utf-8")))
    return recipes, included



def overlay_inventory(core_dir):
    """Inventory Dakota's additional core recipes and their shared stack."""
    root = Path(core_dir)
    if not root.is_dir():
        raise AuditError(f"Missing COSMIC overlay directory: {root}")
    stack = root / "deps.bst"
    if not stack.is_file():
        raise AuditError(f"Missing COSMIC supplemental stack: {stack}")
    names = set(re.findall(r"^\s*-\s+cosmic-core/([^/\s]+)\.bst(?:\s*(?:#.*)?)?$",
                           stack.read_text(encoding="utf-8"), re.M))
    recipes = set()
    for recipe in root.glob("*.bst"):
        if recipe.name == "deps.bst":
            continue
        text = recipe.read_text(encoding="utf-8")
        # An empty Cargo snapshot means a staged placeholder, not a built
        # and tracked recipe. Do not count it as packaged/ready.
        if "- kind: cargo2" in text and "  ref: []" in text:
            continue
        if "- kind: git_repo" in text and re.search(r"^\s+ref: ", text, re.M):
            recipes.add(recipe.stem)
    return recipes, names

def check(current, baseline, recipes, included):
    old = {x["id"]: x for x in baseline["components"]}
    now = {x["id"]: x for x in current["components"]}
    changes = {
        "added": [now[x] for x in sorted(now.keys() - old.keys())],
        "removed": [old[x] for x in sorted(old.keys() - now.keys())],
        "renamed": [{"id": x, "old_path": old[x]["path"], "new_path": now[x]["path"]}
                    for x in sorted(old.keys() & now.keys())
                    if old[x]["path"] != now[x]["path"]],
        "updated": [x for x in sorted(old.keys() & now.keys())
                    if old[x]["sha"] != now[x]["sha"]],
    }
    # Match names from the official .gitmodules metadata, not a fixed package list.
    # A directory rename does not make a working upstream repository disappear.
    missing = []
    not_shipped = []
    for component in current["components"]:
        options = {component["name"], component["path"],
                   component["id"].rsplit("/", 1)[-1]}
        if not (options & recipes):
            missing.append(component["id"])
        elif not (options & included):
            not_shipped.append(component["id"])
    blockers = []
    if len(now) < len(old):
        blockers.append("COMPONENT_COUNT_DECREASED")
    if changes["removed"]:
        blockers.append("COMPONENT_REMOVED")
    if missing:
        blockers.append("MISSING_RECIPES")
    if not_shipped:
        blockers.append("NOT_IN_COSMIC_STACK")
    return {
        "reference_release": baseline["release"],
        "resolved_release": current["release"],
        "reference_count": len(old),
        "current_count": len(now),
        "changes": changes,
        "missing_recipes": missing,
        "not_in_cosmic_stack": not_shipped,
        "blockers": blockers,
        "components": current["components"],
    }


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="cosmic/release-baseline.json")
    parser.add_argument("--core-dir", help="Local elements/core directory after integration")
    parser.add_argument("--overlay-dir", default="elements/cosmic-core",
                        help="Dakota supplemental COSMIC recipes, used with Razorfin inventory")
    parser.add_argument("--reference-repo", default=REFERENCE_REPO)
    parser.add_argument("--reference-ref", default="main")
    parser.add_argument("--report", help="Write JSON report to this path")
    parser.add_argument("--accept", action="store_true",
                        help="Accept the resolved release only if audit has no blockers")
    args = parser.parse_args()
    baseline_file = Path(args.baseline)
    if not baseline_file.is_file():
        raise AuditError(f"Missing release baseline: {baseline_file}")
    baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    if not STABLE_TAG.fullmatch(baseline["release"]):
        raise AuditError("Baseline release must be a stable Epoch tag")
    current = release_manifest(latest_stable())
    if tuple(map(int, STABLE_TAG.fullmatch(current["release"]).groups())) < tuple(
            map(int, STABLE_TAG.fullmatch(baseline["release"]).groups())):
        raise AuditError("Resolved release is older than the accepted baseline")
    recipes, included = (local_inventory(args.core_dir) if args.core_dir
                         else remote_inventory(args.reference_repo, args.reference_ref))
    extra_recipes, extra_included = overlay_inventory(args.overlay_dir)
    recipes |= extra_recipes
    included |= extra_included
    report = check(current, baseline, recipes, included)
    print(f"COSMIC {report['resolved_release']}: {report['current_count']} components "
          f"(baseline {report['reference_release']}: {report['reference_count']})")
    for name in ("added", "removed", "renamed"):
        items = report["changes"][name]
        if items:
            print(f"{name}: " + ", ".join(
                x.get("id", x.get("path", "")) for x in items))
    for name in ("missing_recipes", "not_in_cosmic_stack", "blockers"):
        if report[name]:
            print(f"{name}: " + ", ".join(report[name]))
    if args.report:
        destination = Path(args.report)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if report["blockers"]:
        print("STOP: review the component audit before continuing.", file=sys.stderr)
        return 1
    if args.accept:
        baseline_file.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        print(f"Accepted {current['release']} as the new comparison baseline")
    print("PASS: component count and recipe coverage are safe to continue")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except (AuditError, OSError, KeyError, ValueError) as exc:
        print(f"COSMIC audit failed: {exc}", file=sys.stderr)
        sys.exit(1)
