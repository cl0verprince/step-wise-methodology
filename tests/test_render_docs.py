"""Tests for render_docs.py — escaping, status colors, determinism."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills/browser-readable-project-docs/scripts/render_docs.py"
)

spec = importlib.util.spec_from_file_location("render_docs", SCRIPT)
render_docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_docs)


def test_reflection_escapes_html():
    page = render_docs.render_reflection(
        [{"date": "2026-07-13", "decision": "<script>alert(1)</script>", "rationale": 'a "b" & c'}]
    )
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
    assert "&amp;" in page


def test_workflow_statuses_get_distinct_colors():
    steps = [
        {"name": "s0", "status": "done"},
        {"name": "s1", "status": "in_progress"},
        {"name": "s2", "status": "awaiting_approval"},
        {"name": "s3", "status": "pending"},
    ]
    page = render_docs.render_workflow(steps)
    used = {fill for fill, _ in render_docs.STATUS_COLORS.values() if fill in page}
    assert len(used) == 4, "each canonical status must render its own color"


def test_unknown_status_falls_back_to_pending():
    page = render_docs.render_workflow([{"name": "s", "status": "no-such-status"}])
    assert render_docs.STATUS_COLORS["pending"][0] in page


def test_empty_inputs_render():
    assert "No decisions logged yet" in render_docs.render_reflection([])
    assert "<svg" in render_docs.render_workflow([])


def test_cli_is_deterministic(tmp_path):
    (tmp_path / "decisions.json").write_text(
        json.dumps([{"date": "2026-07-13", "decision": "d", "rationale": "r"}]), "utf-8"
    )
    (tmp_path / "workflow.json").write_text(
        json.dumps({"steps": [{"name": "step0", "status": "done"}]}), "utf-8"
    )

    def render() -> tuple[bytes, bytes]:
        subprocess.run(
            [sys.executable, str(SCRIPT), "--decisions", "decisions.json",
             "--workflow", "workflow.json", "--out-dir", "."],
            cwd=tmp_path, check=True, capture_output=True, timeout=15,
        )
        return ((tmp_path / "reflection.html").read_bytes(),
                (tmp_path / "workflow.html").read_bytes())

    assert render() == render(), "same data must produce identical pages"
