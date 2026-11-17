"""Executable frontend CIF adapter checks, using the existing Node/pytest boundary."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_cif_tree_adapter():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js 18+ is needed for CIF Tree Splitter checks")
    result = subprocess.run(
        [node, "--test", str(ROOT / "tests/unit/cif_tree_checks.cjs")],
        cwd=ROOT, text=True, capture_output=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
