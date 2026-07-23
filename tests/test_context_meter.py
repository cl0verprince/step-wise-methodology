"""End-to-end tests for context_meter.py — run as a subprocess, stdin JSON in,
one line out, exactly as Claude Code's status line invokes it."""
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT = str(
    Path(__file__).resolve().parent.parent
    / "skills/context-meter/scripts/context_meter.py"
)

START = datetime.now(timezone.utc) - timedelta(hours=1, minutes=42)


def ts(minutes: int) -> str:
    return (START + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def jline(**kw) -> str:
    return json.dumps(kw, separators=(",", ":"))


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONTEXT_METER_DIR", str(tmp_path / "state"))
    return tmp_path


def run(payload) -> str:
    data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    p = subprocess.run([sys.executable, SCRIPT], input=data, capture_output=True, timeout=15)
    assert p.returncode == 0, p.stderr
    return p.stdout.decode("utf-8")


def transcript_lines():
    """3 real user prompts, 1 meta, 2 tool results, 3 assistant messages."""
    return [
        jline(type="user", timestamp=ts(0), message={"role": "user", "content": "hello"}),
        jline(type="assistant", timestamp=ts(1), message={"role": "assistant"}),
        jline(type="user", timestamp=ts(2), isMeta=True, message={"content": "<command>"}),
        jline(type="user", timestamp=ts(3), message={"role": "user", "content": "second"}),
        jline(type="assistant", timestamp=ts(4), message={"role": "assistant"}),
        jline(type="user", timestamp=ts(5), toolUseResult={"x": 1}, message={}),
        jline(type="user", timestamp=ts(6), toolUseResult={"x": 2}, message={}),
        jline(type="user", timestamp=ts(7), message={"role": "user", "content": "third"}),
        jline(type="assistant", timestamp=ts(8), message={"role": "assistant"}),
    ]


def payload_for(transcript: Path, session="s1", inp=90_000, out=8_000):
    return {
        "session_id": session,
        "transcript_path": str(transcript),
        "context_window": {
            "context_window_size": 1_000_000,
            "total_input_tokens": inp,
            "total_output_tokens": out,
        },
    }


def test_first_tick_counts_turns_and_duration(env):
    t = env / "t.jsonl"
    t.write_text("\n".join(transcript_lines()) + "\n", encoding="utf-8")
    out = run(payload_for(t))
    assert out.startswith("🟢 10% (98k/1.0M)")
    assert "3 turns" in out          # meta + tool results excluded
    assert "1h4" in out              # ~1h42m elapsed


def test_idle_retick_is_stable(env):
    t = env / "t.jsonl"
    t.write_text("\n".join(transcript_lines()) + "\n", encoding="utf-8")
    run(payload_for(t))
    assert "3 turns" in run(payload_for(t))


def test_incremental_append_and_torn_line(env):
    t = env / "t.jsonl"
    t.write_text("\n".join(transcript_lines()) + "\n", encoding="utf-8")
    run(payload_for(t))
    with t.open("a", encoding="utf-8") as fh:
        fh.write(jline(type="user", timestamp=ts(9), toolUseResult={}, message={}) + "\n")
        fh.write(jline(type="user", timestamp=ts(10), message={"content": "fourth"}) + "\n")
        fh.write('{"type":"user","timestamp":"' + ts(11) + '","message":{"cont')  # torn
    out = run(payload_for(t, inp=120_000))
    assert "4 turns" in out
    assert "next ~" in out           # growth history now exists
    with t.open("a", encoding="utf-8") as fh:
        fh.write('ent":"fifth"}}\n')  # complete the torn line
    out = run(payload_for(t, inp=130_000))
    assert "5 turns" in out


def test_missing_transcript_is_graceful(env):
    out = run(payload_for(env / "nope.jsonl"))
    assert out.startswith("🟢 10% (")
    assert "turns" not in out


def test_no_transcript_path_key(env):
    out = run({
        "session_id": "s2",
        "context_window": {
            "context_window_size": 200_000,
            "total_input_tokens": 180_000,
            "total_output_tokens": 0,
        },
    })
    assert out.startswith("🔴 90% (")


def test_garbage_stdin_never_crashes(env):
    out = run(b"not json")
    assert "ctx n/a" in out


def test_legacy_payload(env):
    assert run({"exceeds_200k_tokens": True}) == "🔴 ctx >200k"


def seed_state(env, session, state):
    d = env / "state"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{session}.json").write_text(json.dumps(state), encoding="utf-8")


def payload_tokens(session, inp, window=200_000, extra=None):
    p = {
        "session_id": session,
        "context_window": {
            "context_window_size": window,
            "total_input_tokens": inp,
            "total_output_tokens": 0,
        },
    }
    if extra:
        p.update(extra)
    return p


def test_red_eta_shown_with_enough_history(env):
    t0 = time.time() - 360
    seed_state(env, "eta", {"samples": [
        [120_000, t0], [130_000, t0 + 120], [140_000, t0 + 240], [150_000, t0 + 360],
    ]})
    out = run(payload_tokens("eta", 150_000))
    # 20k tokens to red at ~83 tok/s -> ~4m; predicted next (160k = 80%) < red
    assert "red ~4m" in out
    assert "next ~" not in out
    assert "handoff" not in out


def test_next_fallback_when_history_thin(env):
    t0 = time.time() - 300
    seed_state(env, "thin", {"samples": [[90_000, t0], [110_000, t0 + 120]]})
    out = run(payload_tokens("thin", 110_000))
    assert "next ~" in out           # 1 growth sample: ETA refuses, next~ steps in
    assert "red ~" not in out


def test_handoff_cue_at_red(env):
    out = run(payload_tokens("red", 180_000))
    assert out.startswith("🔴 90% (")
    assert "→ handoff?" in out


def test_compaction_counter(env):
    t0 = time.time() - 120
    seed_state(env, "comp", {"samples": [[100_000, t0], [120_000, t0 + 60]]})
    out = run(payload_tokens("comp", 60_000))
    assert "↺1" in out


def test_cost_segment_feature_detected(env):
    out = run(payload_tokens("cost", 50_000, extra={"cost": {"total_cost_usd": 0.4234}}))
    assert "$0.42" in out
    out2 = run(payload_tokens("cost2", 50_000))
    assert "$" not in out2


def test_pre_07_int_samples_reset_not_crash(env):
    seed_state(env, "old", {"samples": [90_000, 110_000, 130_000]})
    out = run(payload_tokens("old", 140_000))
    assert out.startswith("🟡 70% (")


def test_big_transcript_incremental_tick_is_fast(env):
    big = env / "big.jsonl"
    lines = transcript_lines()
    with big.open("w", encoding="utf-8") as fh:
        for i in range(20_000):
            fh.write(lines[i % len(lines)] + "\n")
    p = payload_for(big, session="big", inp=50_000, out=0)
    run(p)                                    # first pass pays the full read
    t0 = time.perf_counter()
    run(p)
    assert time.perf_counter() - t0 < 2.0     # incremental tick (mostly startup)


def test_v3_line_drops_ctx_label(env):
    out = run(payload_tokens("fmt", 98_000))
    assert out.startswith("🟢 49% (98k/200k)")
    assert " ctx (" not in out


def test_model_segment(env):
    out = run(payload_tokens("model", 98_000, extra={
        "model": {"id": "claude-fable-5", "display_name": "Claude Fable 5"},
    }))
    assert "· fable" in out


def test_model_segment_unknown_family(env):
    out = run(payload_tokens("model2", 98_000, extra={
        "model": {"display_name": "Futuremodel XL 9"},
    }))
    assert "· futuremodel" in out


def test_model_absent_no_segment(env):
    # No model, transcript, or cost: the line is exactly the gauge.
    assert run(payload_tokens("model3", 98_000)) == "🟢 49% (98k/200k)"


def branch_payload(session, project_dir, inp=98_000):
    return payload_tokens(session, inp, extra={
        "workspace": {"current_dir": str(project_dir)},
    })


def test_branch_segment(env, tmp_path):
    proj = tmp_path / "proj"
    (proj / ".git").mkdir(parents=True)
    (proj / ".git" / "HEAD").write_text("ref: refs/heads/feature-x\n", encoding="utf-8")
    sub = proj / "src"
    sub.mkdir()
    out = run(branch_payload("br1", sub))     # found by walking up from src/
    assert "· feature-x" in out


def test_branch_worktree_gitdir_file(env, tmp_path):
    real = tmp_path / "repo" / ".git" / "worktrees" / "wt"
    real.mkdir(parents=True)
    (real / "HEAD").write_text("ref: refs/heads/wt-branch\n", encoding="utf-8")
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {real}\n", encoding="utf-8")
    out = run(branch_payload("br2", wt))
    assert "· wt-branch" in out


def test_branch_detached_head(env, tmp_path):
    proj = tmp_path / "det"
    (proj / ".git").mkdir(parents=True)
    (proj / ".git" / "HEAD").write_text("a1b2c3d4e5f60718293a4b5c6d7e8f9012345678\n", encoding="utf-8")
    out = run(branch_payload("br3", proj))
    assert "· a1b2c3d" in out


def test_no_git_no_branch_segment(env, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    out = run(branch_payload("br4", plain))
    assert "feature" not in out and "· a1b2c3d" not in out


def project_with_git(tmp_path, name="p"):
    proj = tmp_path / name
    (proj / ".git").mkdir(parents=True)
    (proj / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    return proj


def test_step_segment_in_progress(env, tmp_path):
    proj = project_with_git(tmp_path)
    (proj / "workflow.json").write_text(json.dumps({"steps": [
        {"name": "a", "status": "done"},
        {"name": "b", "status": "in_progress"},
        {"name": "c", "status": "pending"},
    ]}), encoding="utf-8")
    out = run(branch_payload("st1", proj))
    assert "· step 2/3" in out


def test_step_segment_awaiting_approval_counts_as_current(env, tmp_path):
    proj = project_with_git(tmp_path, "p2")
    (proj / "workflow.json").write_text(json.dumps({"steps": [
        {"name": "a", "status": "done"},
        {"name": "b", "status": "awaiting_approval"},
        {"name": "c", "status": "pending"},
    ]}), encoding="utf-8")
    out = run(branch_payload("st2", proj))
    assert "· step 2/3" in out


def test_step_segment_all_done(env, tmp_path):
    proj = project_with_git(tmp_path, "p3")
    (proj / "workflow.json").write_text(json.dumps({"steps": [
        {"name": "a", "status": "done"},
        {"name": "b", "status": "done"},
    ]}), encoding="utf-8")
    out = run(branch_payload("st3", proj))
    assert "· step 2/2" in out


def test_no_workflow_no_step_segment(env, tmp_path):
    proj = project_with_git(tmp_path, "p4")
    out = run(branch_payload("st4", proj))
    assert "step " not in out


def test_broken_workflow_never_crashes(env, tmp_path):
    proj = project_with_git(tmp_path, "p5")
    (proj / "workflow.json").write_text("{not json", encoding="utf-8")
    out = run(branch_payload("st5", proj))
    assert out.startswith("🟢") and "step " not in out


def test_non_object_workflow_never_crashes(env, tmp_path):
    proj = project_with_git(tmp_path, "p6")
    (proj / "workflow.json").write_text("[1, 2, 3]", encoding="utf-8")
    out = run(branch_payload("st6", proj))
    assert out.startswith("🟢") and "step " not in out


def test_non_list_steps_never_crashes(env, tmp_path):
    proj = project_with_git(tmp_path, "p7")
    (proj / "workflow.json").write_text('{"steps": true}', encoding="utf-8")
    out = run(branch_payload("st7", proj))
    assert out.startswith("🟢") and "step " not in out


def test_burn_rate_shown_after_ten_minutes(env):
    t = env / "t.jsonl"
    t.write_text("\n".join(transcript_lines()) + "\n", encoding="utf-8")
    p = payload_for(t)                          # transcript starts ~1h42m ago
    p["cost"] = {"total_cost_usd": 0.42}
    out = run(p)
    assert "· $0.42" in out
    assert "· $0.25/h" in out                   # 0.42 / 1.7h


def test_burn_rate_hidden_early(env):
    t = env / "young.jsonl"
    recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )
    t.write_text(
        jline(type="user", timestamp=recent, message={"role": "user", "content": "hi"})
        + "\n",
        encoding="utf-8",
    )
    p = payload_for(t, session="young")
    p["cost"] = {"total_cost_usd": 0.10}
    out = run(p)
    assert "$0.10" in out and "/h" not in out


def run_env(payload, extra_env):
    import os as _os
    data = json.dumps(payload).encode()
    p = subprocess.run(
        [sys.executable, SCRIPT], input=data, capture_output=True, timeout=15,
        env={**_os.environ, **extra_env},
    )
    assert p.returncode == 0, p.stderr
    return p.stdout.decode("utf-8")


def test_hide_segments(env, tmp_path):
    proj = project_with_git(tmp_path, "hideproj")
    p = branch_payload("hide1", proj)
    p["model"] = {"display_name": "Claude Fable 5"}
    p["cost"] = {"total_cost_usd": 0.42}
    out = run_env(p, {
        "CLAUDE_CONTEXT_METER_DIR": str(env / "state"),
        "CLAUDE_CONTEXT_METER_HIDE": "model,branch,cost",
    })
    assert "fable" not in out
    assert "main" not in out
    assert "$" not in out


def test_hide_unset_shows_everything(env, tmp_path):
    proj = project_with_git(tmp_path, "showproj")
    p = branch_payload("hide2", proj)
    p["model"] = {"display_name": "Claude Fable 5"}
    out = run(p)
    assert "· fable" in out and "· main" in out
