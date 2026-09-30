#!/usr/bin/env python3
"""Resolve the newest maintenance release in the configured NVIDIA LTS branch.

The policy branch lives in elements/bluefin-nvidia/nvidia-drivers.bst as
nvidia-lts-branch. This script verifies that NVIDIA still classifies that
branch as LTS, resolves the newest x86_64 release from NVIDIA's official
releases.json, verifies the matching desktop runfile checksum published by
NVIDIA, and rewrites only the local checkout. It does not commit changes.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

RELEASES_URL = "https://docs.nvidia.com/datacenter/tesla/drivers/releases.json"
DOWNLOAD_BASE = "https://us.download.nvidia.com/XFree86/Linux-x86_64"
ELEMENT = Path("elements/bluefin-nvidia/nvidia-drivers.bst")
USER_AGENT = "dakota-lts-nvidia-tracker/1"


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"ERROR: {message}")


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except Exception as exc:
        fail(f"failed to fetch {url}: {exc}")


def version_key(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        fail(f"unexpected NVIDIA version format: {version}")


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        fail(f"could not update exactly one {label} entry")
    return updated


def main() -> None:
    if not ELEMENT.is_file():
        fail(f"missing {ELEMENT}")

    element = ELEMENT.read_text(encoding="utf-8")

    branch_match = re.search(
        r"^\s*nvidia-lts-branch:\s*['\"]?(\d+)['\"]?\s*$",
        element,
        flags=re.MULTILINE,
    )
    if not branch_match:
        fail("nvidia-lts-branch is not declared in nvidia-drivers.bst")
    branch = branch_match.group(1)

    try:
        releases = json.loads(fetch_text(RELEASES_URL))
    except json.JSONDecodeError as exc:
        fail(f"NVIDIA releases.json is invalid JSON: {exc}")

    branch_info = releases.get(branch)
    if not isinstance(branch_info, dict):
        fail(f"NVIDIA branch R{branch} is missing from releases.json")

    branch_type = str(branch_info.get("type", "")).strip().lower()
    if branch_type != "lts branch":
        fail(
            f"NVIDIA branch R{branch} is no longer classified as 'lts branch' "
            f"(reported type: {branch_info.get('type')!r})"
        )

    candidates = []
    for release in branch_info.get("driver_info", []):
        version = str(release.get("release_version", ""))
        architectures = release.get("architectures", [])
        if version.startswith(f"{branch}.") and "x86_64" in architectures:
            candidates.append(release)

    if not candidates:
        fail(f"no x86_64 releases found for NVIDIA LTS branch R{branch}")

    release = max(candidates, key=lambda item: version_key(str(item["release_version"])))
    version = str(release["release_version"])
    if not re.fullmatch(rf"{re.escape(branch)}\.\d+\.\d+", version):
        fail(f"resolved release escaped R{branch}: {version}")

    filename = f"NVIDIA-Linux-x86_64-{version}.run"
    runfile_path = f"XFree86/Linux-x86_64/{version}/{filename}"
    checksum_url = f"{DOWNLOAD_BASE}/{version}/{filename}.sha256sum"
    checksum_text = fetch_text(checksum_url)

    checksum_match = re.search(
        rf"^([0-9a-fA-F]{{64}})\s+{re.escape(filename)}\s*$",
        checksum_text,
        flags=re.MULTILINE,
    )
    if not checksum_match:
        fail(f"no SHA-256 entry for {filename} at NVIDIA")
    sha256 = checksum_match.group(1).lower()

    element = replace_once(
        element,
        r"^(\s*url:\s+nvidia:)XFree86/Linux-x86_64/[^/\s]+/NVIDIA-Linux-x86_64-[^\s]+\.run\s*$",
        rf"\1{runfile_path}",
        "NVIDIA runfile URL",
    )
    element = replace_once(
        element,
        r"^(\s*ref:\s+)[0-9a-fA-F]{64}\s*$",
        rf"\1{sha256}",
        "NVIDIA SHA-256",
    )
    element = replace_once(
        element,
        r"^(\s*filename:\s+)NVIDIA-Linux-x86_64-[^\s]+\.run\s*$",
        rf"\1{filename}",
        "NVIDIA filename",
    )
    element = replace_once(
        element,
        r"^(\s*nvidia-version:\s*)['\"][^'\"]+['\"]\s*$",
        rf"\1'{version}'",
        "nvidia-version",
    )

    ELEMENT.write_text(element, encoding="utf-8")
    print(f"R{branch} {version} sha256={sha256}")


if __name__ == "__main__":
    main()
