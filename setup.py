"""Build hook that ships Agent Skill Mastery Engine's own skill files inside the wheel.

Project metadata lives in pyproject.toml. This file exists only because setuptools
package data cannot name files outside the package directory, while the canonical
SKILL.md, PURPOSE.md, NOTICE.md, LICENSE, and references/ stay at the repository root.
At wheel-build time they are copied to ``asme/skill/`` so that
``asme.skill_assets.skill_root()`` finds them after a pip or uv install. Editable
installs skip the copy and read the repository root directly.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

ROOT = Path(__file__).resolve().parent


def _skill_assets():
    location = ROOT / "src" / "asme" / "skill_assets.py"
    spec = importlib.util.spec_from_file_location("_asme_skill_assets", location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class build_py(_build_py):
    def run(self) -> None:
        super().run()
        if getattr(self, "editable_mode", False):
            return
        assets = _skill_assets()
        target = Path(self.build_lib) / "asme" / assets.PACKAGED_SUBDIRECTORY
        if target.exists():
            shutil.rmtree(target)
        assets.copy_skill_tree(ROOT, target)


setup(cmdclass={"build_py": build_py})
