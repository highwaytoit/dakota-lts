#!/usr/bin/env python3
"""Patch Razorfin's pinned BuildStream recipe snapshot to official stable COSMIC.

Generates a local patch for the COSMIC junction only; no upstream repository
is changed. Run before bst show/build, after the component coverage audit.
"""
import argparse
import base64
import difflib
import json
from pathlib import Path
import re
import sys

from cosmic_release_audit import AuditError, get_json, latest_stable, release_manifest
from cosmic_source_sync import RUST, rust_refs, dump_refs

REFERENCE = "RazorfinOS-org/cosmic-build-meta"
SUPPLEMENTAL = RUST | {"cosmic-sound-theme"}
PATCH_PATH = "patches/cosmic-build-meta/0001-upstream-stable-cosmic.patch"


def source_text(path, revision):
    payload = get_json("/repos/" + REFERENCE + "/contents/" + path + "?ref=" + revision)
    if payload.get("encoding") != "base64":
        raise AuditError("Cannot read complete upstream recipe: " + path)
    return base64.b64decode(payload["content"]).decode("utf-8")


def segment(text, kind):
    first = text.find("- kind: " + kind + "\n")
    if first < 0:
        return None
    next_section = re.search(r"(?m)^(?:- kind: |[a-z][a-z0-9_-]*:)", text[first + 1:])
    end = first + 1 + next_section.start() if next_section else len(text)
    return first, end


def update_recipe(text, component, release, lock):
    src = segment(text, "git_repo")
    if not src:
        raise AuditError("Missing git_repo for " + component["id"])
    start, end = src
    chunk = text[start:end]
    found = re.search(r"(?m)^  url: github:([^\s]+)$", chunk)
    if not found:
        raise AuditError("COSMIC git_repo URL not found for " + component["id"])
    repo = found.group(1).strip("/").removesuffix(".git").lower()
    if repo != component["id"]:
        raise AuditError("COSMIC recipe identity mismatch: " + component["id"] +
                         " vs " + repo)
    old = re.search(r"(?m)^  ref:\s*([^\n]+)$", chunk)
    if not old:
        raise AuditError("COSMIC recipe is missing git revision: " + component["id"])
    ref = release + "-0-g" + component["sha"]
    chunk = chunk[:old.start(1)] + ref + chunk[old.end(1):]
    text = text[:start] + chunk + text[end:]

    cargo = segment(text, "cargo2")
    if cargo:
        if lock is None:
            raise AuditError("Missing upstream Cargo.lock: " + component["id"])
        refs = rust_refs(lock)
        start, end = cargo
        chunk = text[start:end]
        m = re.search(r"(?m)^  ref:\s*(?:\[\])?\s*$", chunk)
        if not m:
            raise AuditError("Missing cargo2 ref: " + component["id"])
        # ref is the last source-level option; the remainder is just the
        # indented crate records. Fail if an additional option appears.
        tail = chunk[m.end():]
        if re.search(r"(?m)^  [a-z][\w-]*:", tail):
            raise AuditError("Unexpected cargo2 fields after ref in " + component["id"])
        chunk = chunk[:m.start()] + dump_refs(refs)
        text = text[:start] + chunk + text[end:]
    return text


def generate(reference_revision, release, *, output, report):
    changes = []
    inventory = []
    all_components = release["components"]
    if len({c["id"] for c in all_components}) != len(all_components):
        raise AuditError("Duplicate official COSMIC repository identity")

    for component in all_components:
        if component["name"] in SUPPLEMENTAL:
            continue
        path = "elements/core/" + component["name"] + ".bst"
        old = source_text(path, reference_revision)
        lock = None
        if segment(old, "cargo2"):
            payload = get_json("/repos/" + component["id"] + "/contents/Cargo.lock?ref=" +
                               component["sha"])
            if payload.get("encoding") != "base64":
                raise AuditError("Cannot read Cargo.lock for " + component["id"])
            lock = base64.b64decode(payload["content"]).decode("utf-8")
        new = update_recipe(old, component, release["release"], lock)
        inventory.append({"id": component["id"], "sha": component["sha"],
                          "changed": old != new})
        if old != new:
            filename = "elements/core/" + component["name"] + ".bst"
            changes.append("diff --git a/" + filename + " b/" + filename + "\n")
            changes.extend(difflib.unified_diff(
                old.splitlines(keepends=True), new.splitlines(keepends=True),
                fromfile="a/" + filename, tofile="b/" + filename,
            ))

    # Avoid leaving a stale patch from a previous release.
    patch = Path(output)
    patch.parent.mkdir(parents=True, exist_ok=True)
    patch.write_text("".join(changes), encoding="utf-8")
    if report:
        dest = Path(report)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps({
            "release": release["release"], "reference": reference_revision,
            "upstream_recipes": inventory, "patch_count": sum(x["changed"] for x in inventory),
        }, indent=2) + "\n", encoding="utf-8")
    print("Stable COSMIC", release["release"], "Razorfin recipes", len(inventory),
          "updated", len([x for x in inventory if x["changed"]]))
    print("Generated local junction patch:", patch, patch.stat().st_size, "bytes")
    return inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junction", default="elements/cosmic-build-meta.bst")
    parser.add_argument("--output", default=PATCH_PATH)
    parser.add_argument("--report", default="cosmic-upstream-source-report.json")
    args = parser.parse_args()
    source = Path(args.junction).read_text(encoding="utf-8")
    m = re.search(r"(?m)^  ref:\s*([0-9a-f]{40})\s*$", source)
    if not m:
        raise AuditError("COSMIC junction reference must be a reviewed 40-character SHA")
    release = release_manifest(latest_stable())
    generate(m.group(1), release, output=args.output, report=args.report)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AuditError, OSError, KeyError, ValueError) as exc:
        print("COSMIC upstream sync failed:", exc, file=sys.stderr)
        sys.exit(1)
