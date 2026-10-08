#!/usr/bin/env python3
"""Synchronize Dakota's supplemental COSMIC recipes to the latest stable Epoch.

The official tagged cosmic-epoch submodules define authoritative source SHAs.
Cargo dependency snapshots come from each matching upstream Cargo.lock.
Run this before any BuildStream build; --write changes local worktree only.
"""
import argparse
import base64
from pathlib import Path
import re
import sys
import tomllib
from urllib.parse import urlsplit

from cosmic_release_audit import AuditError, get_json, latest_stable, release_manifest

RUST = {"cosmic-monitor", "cosmic-osk", "cosmic-viewer"}
EXTRA = RUST | {"cosmic-sound-theme"}


def source_text(repo, path, commit):
    data = get_json("/repos/" + repo + "/contents/" + path + "?ref=" + commit)
    if data.get("encoding") != "base64":
        raise AuditError("GitHub did not return a full base64 source file: " + path)
    return base64.b64decode(data["content"]).decode("utf-8")


def rust_refs(lock_text):
    lock = tomllib.loads(lock_text)
    refs = []
    for item in lock.get("package", []):
        source = item.get("source")
        if not source:
            continue
        if not item.get("name") or not item.get("version"):
            raise AuditError("Cargo.lock entry lacks name or version")
        if source.startswith("registry+"):
            checksum = item.get("checksum")
            if not checksum or not re.fullmatch(r"[0-9a-f]{64}", checksum):
                raise AuditError("Cargo.lock lacks a valid registry checksum: " + item["name"])
            refs.append({"kind": "registry", "name": item["name"],
                         "version": str(item["version"]), "sha": checksum})
        elif source.startswith("git+"):
            parsed = urlsplit(source[4:])
            hosts = {
                "github.com": "github",
                "gitlab.com": "gitlab",
                "gitlab.freedesktop.org": "freedesktop",
                "gitlab.gnome.org": "gnome",
                "codeberg.org": "codeberg",
                "git.sr.ht": "srht",
            }
            if parsed.scheme != "https" or parsed.hostname not in hosts:
                raise AuditError("Unsupported Rust git dependency: " + source)
            # Preserve Cargo.lock's URL spelling (including a repeated slash
            # or .git suffix). Cargo matches vendored git sources by their
            # exact URL, not by equivalent normalized repository identities.
            raw_path = parsed.path.lstrip("/")
            parts = [part for part in raw_path.split("/") if part]
            if (len(parts) < 2 or any(part in (".", "..") for part in parts)
                    or (parsed.hostname == "github.com" and len(parts) != 2)
                    or not re.fullmatch(r"[0-9a-f]{40}", parsed.fragment)):
                raise AuditError("Unsupported Rust git revision: " + source)
            data = {"kind": "git", "commit": parsed.fragment,
                    "repo": hosts[parsed.hostname] + ":" + raw_path,
                    "name": item["name"],
                    "version": str(item["version"])}
            if parsed.query:
                query = {}
                for part in parsed.query.split("&"):
                    if "=" not in part:
                        raise AuditError("Invalid Rust git query: " + source)
                    key, value = part.split("=", 1)
                    if key in query or key not in {"branch", "tag", "rev"} or not value:
                        raise AuditError("Invalid Rust git query: " + source)
                    query[key] = value
                data["query"] = query
            refs.append(data)
        else:
            raise AuditError("Unsupported Cargo.lock source: " + source)
    if len(refs) < 20:
        raise AuditError("Suspiciously small Cargo.lock dependency set")
    return sorted(refs, key=lambda x: (x["name"], x["version"], x.get("repo", ""), x.get("commit", "")))


def dump_refs(refs):
    lines = ["  ref:"]
    for item in refs:
        lines.append("  - kind: " + item["kind"])
        for key in ("commit", "repo", "query", "name", "version", "sha"):
            value = item.get(key)
            if isinstance(value, dict):
                lines.append("    " + key + ":")
                for k, v in sorted(value.items()):
                    lines.append("      " + k + ": " + repr(str(v)))
            elif value is not None:
                lines.append("    " + key + ": " + repr(str(value)))
    return "\n".join(lines) + "\n"


def update_recipe(text, name, release, sha, refs):
    # Limit replacement to the first source. No unrelated recipe fields change.
    expr = re.compile(r"(- kind: git_repo\n(?:[^\n]*\n)*?  ref: )[^\n]+")
    match = expr.search(text)
    if not match:
        raise AuditError("COSMIC recipe lacks a pinned git_repo source: " + name)
    text, count = expr.subn(lambda m: m.group(1) + f"{release}-0-g{sha}", text, count=1)
    if count != 1:
        raise AuditError("Could not update upstream git pin: " + name)
    if name in RUST:
        first = text.find("- kind: cargo2\n")
        last = text.find("\nconfig:\n", first)
        if first < 0 or last < 0:
            raise AuditError("Rust recipe is missing cargo2 or config section: " + name)
        block = "- kind: cargo2\n  url: 'crates:crates/'\n  vendor-dir: .vendored\n" + dump_refs(refs)
        text = text[:first] + block + text[last:]
    return text


def sync(core, release, *, write):
    source = {c["path"]: c for c in release["components"]}
    if EXTRA - source.keys():
        raise AuditError("Stable COSMIC release removed a supplemental component: " +
                         ", ".join(sorted(EXTRA - source.keys())))
    records = []
    for name in sorted(EXTRA):
        recipe = core / (name + ".bst")
        if not recipe.is_file():
            raise AuditError("Missing Dakota supplemental recipe: " + str(recipe))
        c = source[name]
        cargo = rust_refs(source_text(c["id"], "Cargo.lock", c["sha"])) if name in RUST else []
        previous = recipe.read_text(encoding="utf-8")
        updated = update_recipe(previous, name, release["release"], c["sha"], cargo)
        records.append((recipe, updated, c["sha"], len(cargo),
                        previous != updated))
    if write:
        # No writes until *all* upstream lock files and all recipes have validated.
        for recipe, updated, _, _, changed in records:
            if changed:
                recipe.write_text(updated, encoding="utf-8")
    return [{"name":p.stem, "sha":sha, "cargo_packages":size, "changed":changed}
            for p, _, sha, size, changed in records]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-dir", default="elements/cosmic-core")
    parser.add_argument("--write", action="store_true",
                        help="Update local BuildStream recipes (never commits/pushes)")
    args = parser.parse_args()
    release = release_manifest(latest_stable())
    inventory = sync(Path(args.core_dir), release, write=args.write)
    print("Resolved", release["release"], "components", len(release["components"]))
    for row in inventory:
        print(row["name"], row["sha"][:12], "Cargo entries:", row["cargo_packages"],
              "changed:", row["changed"])
    print("Local worktree updated" if args.write else "Dry-run only; no files modified")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AuditError, OSError, KeyError, ValueError, tomllib.TOMLDecodeError) as exc:
        print("COSMIC source sync failed:", exc, file=sys.stderr)
        sys.exit(1)
