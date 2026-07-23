"""Golden-fixture regression tests for context_meter.py.

Each tests/fixtures/context-meter/<case>.input.json is piped to the script
exactly as Claude Code would; <case>.expected.txt is the exact line it must
print. Fixtures use payload-only features (no transcript, no git dir, fresh
state) so they are fully deterministic.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = str(
    Path(__file__).resolve().parent.parent
    / "skills/context-meter/scripts/context_meter.py"
)
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "context-meter"
CASES = sorted(FIXTURES.glob("*.input.json"))


@pytest.mark.parametrize(
    "case", CASES, ids=[c.name[: -len(".input.json")] for c in CASES]
)
def test_golden(case, tmp_path):
    expected = case.with_name(case.name.replace(".input.json", ".expected.txt"))
    env = {**os.environ, "CLAUDE_CONTEXT_METER_DIR": str(tmp_path)}
    env.pop("CLAUDE_CONTEXT_METER_HIDE", None)
    p = subprocess.run(
        [sys.executable, SCRIPT],
        input=case.read_bytes(),
        capture_output=True,
        timeout=15,
        env=env,
    )
    assert p.returncode == 0, p.stderr
    assert p.stdout.decode("utf-8") == expected.read_text(encoding="utf-8").rstrip("\n")
