from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_stdlib_smoke_reaches_done_without_network(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
    }
    completed = subprocess.run(
        [sys.executable, str(root / "scripts/stdlib_smoke.py")],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result == {
        "domain_id": "stdlib-smoke",
        "isolation": "unsandboxed",
        "network_used": False,
        "phase": "DONE",
        "score": 1.0,
        "trace_fidelity": "final_only",
    }
