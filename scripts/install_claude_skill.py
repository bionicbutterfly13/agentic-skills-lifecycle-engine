#!/usr/bin/env python3
"""Copy Agent Skill Mastery Engine's own agent skill into a Claude Code skill directory.

Standard library only. Mirrors ``asme install``: it copies just the packaged
SKILL.md and companions, refuses staging and archive sources, and never installs an
evolved candidate. Prints one JSON object like the rest of the CLI.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if (_PACKAGE_ROOT / "src" / "asme").is_dir():
    sys.path.insert(0, str(_PACKAGE_ROOT / "src"))

from asme.canonical import ContractError, canonical_bytes
from asme.skill_install import install_skill


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="install_claude_skill.py",
        description=(
            "Install Agent Skill Mastery Engine's own skill (SKILL.md and companions) for Claude Code. "
            "Evolved candidates are never installed."
        ),
    )
    parser.add_argument(
        "--target",
        type=Path,
        help="Skill directory to create (default: ~/.claude/skills/asme)",
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="Checkout holding Agent Skill Mastery Engine's SKILL.md; staging and archive roots are refused",
    )
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing asme skill directory"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the plan without writing anything"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = install_skill(
            target=args.target,
            source=args.source,
            force=args.force,
            dry_run=args.dry_run,
        )
    except (ContractError, OSError) as exc:
        sys.stderr.write(f"install_claude_skill: {exc}\n")
        return 2
    sys.stdout.buffer.write(canonical_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
