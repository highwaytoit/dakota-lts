#!/usr/bin/env python3
"""Select Razorfin's COSMIC cargo2 plugin in this ephemeral CI checkout only.

Dakota's committed project.conf and its GNOME plugin configuration stay unchanged.
Do not run this against a persistent or production checkout.
"""
from pathlib import Path
import sys

COMMUNITY = """    sources:
      - gen_cargo_lock
      - cargo2
      - git_module"""
COSMIC = """  - origin: junction
    junction: cosmic-build-meta.bst
    sources:
      - cargo2

"""
ANCHOR = """  - origin: junction
    junction: gnome-build-meta.bst
    elements:
      - collect_initial_scripts
"""


def select_cosmic_plugin(config):
    if config.count(COMMUNITY) != 1 or config.count(ANCHOR) != 1:
        raise ValueError("Expected existing Dakota plugin declarations not found")
    config = config.replace(COMMUNITY, COMMUNITY.replace("      - cargo2\n", ""), 1)
    config = config.replace(ANCHOR, COSMIC + ANCHOR, 1)
    return config


def main():
    file = Path("project.conf")
    before = file.read_text(encoding="utf-8")
    after = select_cosmic_plugin(before)
    file.write_text(after, encoding="utf-8")
    print("COSMIC Cargo plugin selected for current CI worktree only")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        print("COSMIC worktree setup failed:", exc, file=sys.stderr)
        sys.exit(1)
