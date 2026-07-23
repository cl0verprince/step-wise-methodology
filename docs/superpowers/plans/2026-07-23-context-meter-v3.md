# Context-Meter v3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the bundled status-line meter to v3 — golden-fixture regression net, dashboard segments (model · branch · step · cost + burn rate), a segment-hide env var, honest-er predictions (idle-aware ETA, recency-weighted growth, learned red line), and an agent-led setup flow with interpreter auto-detection.

**Architecture:** Everything stays in the single stdlib-only `skills/context-meter/scripts/context_meter.py` (owner decision 2026-07-23: **Python-only, no Node.js**). Tests extend the existing subprocess pattern in `tests/test_context_meter.py` (stdin JSON in → one line out); a new golden-fixture harness pins exact output lines. The SKILL.md's setup section becomes an install flow the agent performs (probe interpreter → write settings → verify against a bundled sample payload).

**Tech Stack:** Python 3 stdlib only; pytest for tests (already in repo CI).

## Global Constraints

- **Python-only. No Node.js anywhere** (owner decision recorded in spec §1.1).
- Script must be **stdlib-only** — no imports outside the standard library.
- **Never crash the status line:** any error → print `⚪ ctx n/a`, exit 0. Every new feature must be wrapped so its failure drops only its own segment.
- **No network, ever.** No subprocess spawns from the meter (git branch is read from files, not `git`).
- Emoji output written as **UTF-8 bytes** via the existing `_emit` (Windows cp1252 consoles).
- All tunable numbers are **named constants at the top of the script**.
- State stays in the existing per-session temp-dir JSON file, bounded in size.
- The transcript is read **incrementally** (O(new bytes)); nothing here may add a full-file re-read per tick.
- The spec is `docs/superpowers/specs/2026-07-22-v0.8-improvement-round-design.md` §1; the v3 target line is:
  `🟡 71% (142k/200k) · red ~35m · opus · main · step 3/7 · 23 turns · 1h42m · $0.42 · $0.25/h ↺1`
  (note: v3 **drops the `ctx` label** from the main line; the fallback lines `⚪ ctx n/a`, `⚪ ctx warming up`, `🔴 ctx >200k` keep it).
- `workflow.json` schema (from `browser-readable-project-docs` SKILL.md): `{"steps": [{"name": "...", "status": "done"|"in_progress"|"awaiting_approval"|"pending"}]}`.

## File Structure

- `skills/context-meter/scripts/context_meter.py` — the meter (modified; stays one file).
- `skills/context-meter/scripts/sample.json` — new: bundled sample payload the setup flow pipes through the configured command to verify it works.
- `skills/context-meter/SKILL.md` — rewritten setup + display docs.
- `tests/test_context_meter.py` — feature tests appended (existing helpers reused).
- `tests/test_context_meter_fixtures.py` — new: golden-fixture harness.
- `tests/fixtures/context-meter/*.input.json` + `*.expected.txt` — new: fixture pairs.
- `CHANGELOG.md` — Unreleased entry (final task).

---

### Task 1: Golden-fixture harness + baseline fixtures

Pin the meter's exact current output before touching it, so every later task's
display change is a deliberate fixture edit, never an accident.

**Files:**
- Create: `tests/test_context_meter_fixtures.py`
- Create: `tests/fixtures/context-meter/green.input.json`, `green.expected.txt`
- Create: `tests/fixtures/context-meter/red-handoff.input.json`, `red-handoff.expected.txt`
- Create: `tests/fixtures/context-meter/na.input.json`, `na.expected.txt`

**Interfaces:**
- Produces: fixture convention — `<case>.input.json` is the exact stdin payload; `<case>.expected.txt` is the exact stdout line (single line, trailing newline stripped on compare). Later tasks add/edit pairs; the harness auto-discovers them.

- [ ] **Step 1: Write the harness**

`tests/test_context_meter_fixtures.py`:

```python
"""Golden-fixture regression tests for context_meter.py.

Each tests/fixtures/context-meter/<case>.input.json is piped to the script
exactly as Claude Code would; <case>.expected.txt is the exact line it must
print. Fixtures use payload-only features (no transcript, no git dir, fresh
state) so they are fully deterministic.
"""
import json
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
    p = subprocess.run(
        [sys.executable, SCRIPT],
        input=case.read_bytes(),
        capture_output=True,
        timeout=15,
        env={**os.environ, "CLAUDE_CONTEXT_METER_DIR": str(tmp_path)},
    )
    assert p.returncode == 0, p.stderr
    assert p.stdout.decode("utf-8") == expected.read_text(encoding="utf-8").rstrip("\n")
```

- [ ] **Step 2: Write the three baseline fixture pairs**

`tests/fixtures/context-meter/green.input.json`:

```json
{
  "session_id": "fx-green",
  "context_window": {
    "context_window_size": 200000,
    "total_input_tokens": 90000,
    "total_output_tokens": 8000
  }
}
```

`tests/fixtures/context-meter/green.expected.txt` (current v2 format — updated in Task 2):

```
🟢 49% ctx (98k/200k)
```

`tests/fixtures/context-meter/red-handoff.input.json`:

```json
{
  "session_id": "fx-red",
  "context_window": {
    "context_window_size": 200000,
    "total_input_tokens": 172000,
    "total_output_tokens": 8000
  }
}
```

`tests/fixtures/context-meter/red-handoff.expected.txt`:

```
🔴 90% ctx (180k/200k) → handoff?
```

`tests/fixtures/context-meter/na.input.json`:

```json
{}
```

`tests/fixtures/context-meter/na.expected.txt`:

```
⚪ ctx n/a
```

- [ ] **Step 3: Run the fixture tests — all three must pass against the current script**

Run: `pytest tests/test_context_meter_fixtures.py -v`
Expected: 3 PASSED (`green`, `na`, `red-handoff`). If any fails, the expected file does not match real current behavior — fix the expected file, not the script.

- [ ] **Step 4: Run the whole suite to confirm nothing else broke**

Run: `pytest tests/ -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_context_meter_fixtures.py tests/fixtures/context-meter/
git commit -m "test: golden-fixture harness pinning context-meter output"
```

---

### Task 2: v3 line format (drop `ctx` label) + model segment

**Files:**
- Modify: `skills/context-meter/scripts/context_meter.py` (docstring example, `render`)
- Modify: `tests/test_context_meter.py` (5 assertions), fixtures `green.expected.txt`, `red-handoff.expected.txt`
- Create: `tests/fixtures/context-meter/model.input.json`, `model.expected.txt`

**Interfaces:**
- Produces: `_short_model(data: dict) -> str | None` — family word (`fable`/`opus`/`sonnet`/`haiku`/`mythos`) if present in `model.display_name`, else first word lowercased (≤12 chars), else `None`. Main line format is now `{light} {pct}% ({used}/{window})`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_context_meter.py`)

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context_meter.py -q -k "v3_line or model"`
Expected: FAIL — output still contains `% ctx (` and no `· fable`.

- [ ] **Step 3: Implement**

In `context_meter.py`, add after `_light`:

```python
def _short_model(data: dict) -> str | None:
    """'Claude Fable 5' -> 'fable'. Family word if recognized, else first word."""
    name = ((data.get("model") or {}).get("display_name") or "").strip()
    if not name:
        return None
    low = name.lower()
    for family in ("fable", "opus", "sonnet", "haiku", "mythos"):
        if family in low:
            return family
    return low.split()[0][:12]
```

In `render()`, change the line assembly:

```python
    line = (
        f"{_light(used_pct)} {round(used_pct)}% "
        f"({_fmt_tokens(used_tokens)}/{_fmt_tokens(window)})"
    )
```

and insert immediately after the handoff-cue block (before `line += _session_suffix(state)`):

```python
    model = _short_model(data)
    if model:
        line += f" · {model}"
```

Update the docstring's example line (top of module) to:

```
    🟡 71% (142k/200k) · red ~35m · opus · main · step 3/7 · 23 turns · 1h42m · $0.42 · $0.25/h ↺1
```

- [ ] **Step 4: Update the 5 existing assertions that pin the old label**

In `tests/test_context_meter.py`:
- `test_first_tick_counts_turns_and_duration`: `out.startswith("🟢 10% ctx (98k/1.0M)")` → `out.startswith("🟢 10% (98k/1.0M)")`
- `test_missing_transcript_is_graceful`: `out.startswith("🟢 10% ctx")` → `out.startswith("🟢 10% (")`
- `test_no_transcript_path_key`: `out.startswith("🔴 90% ctx")` → `out.startswith("🔴 90% (")`
- `test_handoff_cue_at_red`: `out.startswith("🔴 90% ctx")` → `out.startswith("🔴 90% (")`
- `test_pre_07_int_samples_reset_not_crash`: `out.startswith("🟡 70% ctx")` → `out.startswith("🟡 70% (")`

Update the two affected fixture expecteds:
- `green.expected.txt` → `🟢 49% (98k/200k)`
- `red-handoff.expected.txt` → `🔴 90% (180k/200k) → handoff?`

Add the model fixture pair — `model.input.json`:

```json
{
  "session_id": "fx-model",
  "context_window": {
    "context_window_size": 200000,
    "total_input_tokens": 130000,
    "total_output_tokens": 12000
  },
  "model": {"id": "claude-sonnet-5", "display_name": "Claude Sonnet 5"}
}
```

`model.expected.txt`:

```
🟡 71% (142k/200k) · sonnet
```

(`na.expected.txt` is untouched — fallback lines keep the `ctx` label.)

- [ ] **Step 5: Run the whole suite**

Run: `pytest tests/ -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add skills/context-meter/scripts/context_meter.py tests/
git commit -m "feat(context-meter): v3 line format + model segment"
```

---

### Task 3: Git branch segment (no subprocess)

**Files:**
- Modify: `skills/context-meter/scripts/context_meter.py`
- Modify: `tests/test_context_meter.py`

**Interfaces:**
- Consumes: nothing new from earlier tasks.
- Produces: `_project_root(start: str) -> Path | None` (nearest ancestor of `start` containing `.git` or `workflow.json`); `_git_branch(root: Path) -> str | None` (branch name, or 7-char SHA when detached; worktree `gitdir:` indirection supported). Task 4 reuses `_project_root`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_context_meter.py`)

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context_meter.py -q -k branch`
Expected: FAIL — no branch segment exists yet.

- [ ] **Step 3: Implement** (add after `_short_model` in `context_meter.py`)

```python
def _project_root(start: str) -> Path | None:
    """Nearest ancestor (including start) containing .git or workflow.json."""
    if not start:
        return None
    try:
        p = Path(start).resolve()
        for candidate in (p, *p.parents):
            if (candidate / ".git").exists() or (candidate / "workflow.json").is_file():
                return candidate
    except OSError:
        pass
    return None


def _git_branch(root: Path) -> str | None:
    """Current branch from .git/HEAD — no git subprocess (status lines must be
    fast). Worktrees ('.git' is a file with 'gitdir: <path>') and detached
    HEAD (short SHA) are handled; anything unreadable just drops the segment."""
    try:
        git = root / ".git"
        if git.is_file():
            target = git.read_text(encoding="utf-8", errors="replace").strip()
            if not target.startswith("gitdir:"):
                return None
            git = (root / target[len("gitdir:"):].strip()).resolve()
        head = (git / "HEAD").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if head.startswith("ref: "):
        return head.rsplit("/", 1)[-1] or None
    return head[:7] or None
```

In `render()`, before the `if state_file: _save_state(...)` block, compute:

```python
    root = _project_root(
        (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or ""
    )
    branch = _git_branch(root) if root else None
```

and in the assembly, right after the model segment:

```python
    if branch:
        line += f" · {branch}"
```

- [ ] **Step 4: Run tests to verify they pass, then the whole suite**

Run: `pytest tests/test_context_meter.py -q -k branch` then `pytest tests/ -q`
Expected: all pass (fixtures untouched: their payloads carry no `workspace`, so no branch segment appears).

- [ ] **Step 5: Commit**

```bash
git add skills/context-meter/scripts/context_meter.py tests/test_context_meter.py
git commit -m "feat(context-meter): git branch segment read from .git/HEAD"
```

---

### Task 4: Step segment from workflow.json

**Files:**
- Modify: `skills/context-meter/scripts/context_meter.py`
- Modify: `tests/test_context_meter.py`

**Interfaces:**
- Consumes: `_project_root` from Task 3.
- Produces: `_step_segment(root: Path, state: dict) -> str | None` — `"step {i}/{total}"`; `i` = 1-based index of the first `in_progress` step, else first step whose status ≠ `done`, else `total` (all done). Caches by mtime under `state["workflow"] = {"path", "mtime", "seg"}`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_context_meter.py`)

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context_meter.py -q -k step_segment`
Expected: FAIL — no step segment exists yet.

- [ ] **Step 3: Implement** (add after `_git_branch`)

```python
def _step_segment(root: Path, state: dict) -> str | None:
    """'step 3/7' from the project's workflow.json (the methodology's canonical
    step status). First in_progress step wins; else the first not-done step;
    all done -> total/total. Parsed only when the file's mtime changes."""
    wf = root / "workflow.json"
    try:
        mtime = wf.stat().st_mtime
    except OSError:
        return None
    cache = state.get("workflow") or {}
    if cache.get("path") == str(wf) and cache.get("mtime") == mtime:
        return cache.get("seg")
    seg = None
    try:
        steps = (json.loads(wf.read_text(encoding="utf-8")) or {}).get("steps") or []
        total = len(steps)
        if total:
            current = next(
                (i for i, s in enumerate(steps, 1)
                 if isinstance(s, dict) and s.get("status") == "in_progress"),
                None,
            )
            if current is None:
                current = next(
                    (i for i, s in enumerate(steps, 1)
                     if isinstance(s, dict) and s.get("status") != "done"),
                    total,
                )
            seg = f"step {current}/{total}"
    except (OSError, ValueError):
        seg = None
    state["workflow"] = {"path": str(wf), "mtime": mtime, "seg": seg}
    return seg
```

In `render()`, next to the branch computation add:

```python
    step = _step_segment(root, state) if root else None
```

(this must run **before** `_save_state` so the mtime cache persists), and in the assembly after the branch segment:

```python
    if step:
        line += f" · {step}"
```

- [ ] **Step 4: Run tests to verify they pass, then the whole suite**

Run: `pytest tests/test_context_meter.py -q -k "step_segment or workflow"` then `pytest tests/ -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add skills/context-meter/scripts/context_meter.py tests/test_context_meter.py
git commit -m "feat(context-meter): step x/y segment from workflow.json"
```

---

### Task 5: Cost burn rate

**Files:**
- Modify: `skills/context-meter/scripts/context_meter.py`
- Modify: `tests/test_context_meter.py`
- Create: `tests/fixtures/context-meter/cost.input.json`, `cost.expected.txt`

**Interfaces:**
- Produces: `_session_elapsed(state: dict) -> float | None` (seconds since the transcript's first timestamp; refactored out of `_session_suffix`, which now calls it); constant `BURN_MIN_AGE = 600.0`. Burn segment format: `· $X.XX/h`, shown only when cost > 0 and elapsed ≥ `BURN_MIN_AGE`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_context_meter.py`)

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context_meter.py -q -k burn`
Expected: FAIL — no `/h` segment exists.

- [ ] **Step 3: Implement**

Add the constant next to the others at the top:

```python
BURN_MIN_AGE = 600.0  # seconds of session age before $/h is meaningful
```

Refactor the elapsed computation out of `_session_suffix` into:

```python
def _session_elapsed(state: dict) -> float | None:
    """Seconds since the transcript's first timestamp, or None."""
    start = (state.get("transcript") or {}).get("start")
    if not start:
        return None
    try:
        begun = datetime.fromisoformat(start.replace("Z", "+00:00"))
    except ValueError:
        return None
    if begun.tzinfo is None:
        begun = begun.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - begun).total_seconds()
    return elapsed if elapsed >= 0 else None
```

and rewrite `_session_suffix` to use it:

```python
def _session_suffix(state: dict) -> str:
    """' · 23 turns · 1h42m' from the tallied transcript state, or ''."""
    t = state.get("transcript") or {}
    parts = []
    if t.get("turns"):
        parts.append(f"{t['turns']} turn{'s' if t['turns'] != 1 else ''}")
    elapsed = _session_elapsed(state)
    if elapsed is not None:
        parts.append(_fmt_duration(elapsed))
    return ("".join(f" · {p}" for p in parts)) if parts else ""
```

In `render()`, replace the cost block with:

```python
    cost = (data.get("cost") or {}).get("total_cost_usd")
    if isinstance(cost, (int, float)) and cost > 0:
        line += f" · ${cost:.2f}"
        elapsed = _session_elapsed(state)
        if elapsed and elapsed >= BURN_MIN_AGE:
            line += f" · ${cost / (elapsed / 3600):.2f}/h"
```

- [ ] **Step 4: Add the cost fixture pair**

`cost.input.json`:

```json
{
  "session_id": "fx-cost",
  "context_window": {
    "context_window_size": 200000,
    "total_input_tokens": 90000,
    "total_output_tokens": 8000
  },
  "cost": {"total_cost_usd": 0.42}
}
```

`cost.expected.txt` (no transcript → no elapsed → no burn segment):

```
🟢 49% (98k/200k) · $0.42
```

- [ ] **Step 5: Run the whole suite**

Run: `pytest tests/ -q`
Expected: all pass (including `test_cost_segment_feature_detected` unchanged — no transcript, so no burn).

- [ ] **Step 6: Commit**

```bash
git add skills/context-meter/scripts/context_meter.py tests/
git commit -m "feat(context-meter): $/h burn rate once the session is 10m old"
```

---

### Task 6: `CLAUDE_CONTEXT_METER_HIDE` segment opt-out

**Files:**
- Modify: `skills/context-meter/scripts/context_meter.py`
- Modify: `tests/test_context_meter.py`

**Interfaces:**
- Produces: `_hidden() -> set[str]` reading env var `CLAUDE_CONTEXT_METER_HIDE` (comma-separated, case-insensitive). Segment names: `model`, `branch`, `step`, `turns`, `duration`, `cost`, `burn`, `compactions`. (The context gauge, trajectory, and handoff cue are the meter's core and cannot be hidden.)

- [ ] **Step 1: Write the failing tests** (append to `tests/test_context_meter.py`)

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context_meter.py -q -k hide`
Expected: `test_hide_segments` FAILS (segments still shown); `test_hide_unset_shows_everything` passes already.

- [ ] **Step 3: Implement**

Add near the other helpers:

```python
def _hidden() -> set:
    """Segment names the user opted out of, e.g. HIDE='branch,model'."""
    raw = os.environ.get("CLAUDE_CONTEXT_METER_HIDE", "")
    return {s.strip().lower() for s in raw.split(",") if s.strip()}
```

In `render()`, compute `hide = _hidden()` right after `state` is loaded, then guard each optional segment:

- model: `if model and "model" not in hide:`
- branch: `if branch and "branch" not in hide:`
- step: `if step and "step" not in hide:`
- cost: `if "cost" not in hide: line += f" · ${cost:.2f}"` (inside the existing `isinstance` check)
- burn: `if "burn" not in hide and elapsed and elapsed >= BURN_MIN_AGE:`
- compactions: `if compactions and "compactions" not in hide:`

Change `_session_suffix(state)` to `_session_suffix(state, hide)`:

```python
def _session_suffix(state: dict, hide: set) -> str:
    """' · 23 turns · 1h42m' from the tallied transcript state, or ''."""
    t = state.get("transcript") or {}
    parts = []
    if t.get("turns") and "turns" not in hide:
        parts.append(f"{t['turns']} turn{'s' if t['turns'] != 1 else ''}")
    if "duration" not in hide:
        elapsed = _session_elapsed(state)
        if elapsed is not None:
            parts.append(_fmt_duration(elapsed))
    return ("".join(f" · {p}" for p in parts)) if parts else ""
```

and update its call site in `render()` to `line += _session_suffix(state, hide)`.

Note: the cost block needs `elapsed` even when `cost` is hidden but `burn` isn't — compute `elapsed = _session_elapsed(state)` before the two guards.

- [ ] **Step 4: Run the whole suite**

Run: `pytest tests/ -q`
Expected: all pass (fixture runs have no HIDE var set — the harness passes only `CLAUDE_CONTEXT_METER_DIR`, and `os.environ` in CI has no HIDE).

- [ ] **Step 5: Commit**

```bash
git add skills/context-meter/scripts/context_meter.py tests/test_context_meter.py
git commit -m "feat(context-meter): CLAUDE_CONTEXT_METER_HIDE segment opt-out"
```

---

### Task 7: Idle-aware time-to-red

**Files:**
- Modify: `skills/context-meter/scripts/context_meter.py` (`_red_eta`)
- Modify: `tests/test_context_meter.py`

**Interfaces:**
- Produces: constant `IDLE_GAP = 600.0`; `_red_eta` keeps its signature `(samples, used_tokens, window) -> float | None` but each inter-sample gap contributes at most `IDLE_GAP` seconds to the burn-rate span.

- [ ] **Step 1: Write the failing test** (append to `tests/test_context_meter.py`)

```python
def test_red_eta_ignores_idle_gap(env):
    now = time.time()
    seed_state(env, "idle", {"samples": [
        [100_000, now - 3780],
        [110_000, now - 3720],
        [120_000, now - 3660],   # then a 1h lunch break
        [130_000, now - 120],
    ]})
    out = run(payload_tokens("idle", 140_000))
    # growths 4x10k over an effective span of 60+60+600(capped)+~120 ≈ 840s
    # -> ~47.6 tok/s; 30k tokens to red (85% of 200k) -> ~10m.
    # Without idle capping the span would be ~3780s -> a wildly wrong ~47m.
    assert "red ~10m" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_context_meter.py -q -k idle_gap`
Expected: FAIL — current output says `red ~47m` (uncapped span).

- [ ] **Step 3: Implement**

Add the constant at the top:

```python
IDLE_GAP = 600.0      # cap each inter-sample gap at 10min in burn-rate math
```

Rewrite `_red_eta`:

```python
def _red_eta(samples: list, used_tokens: int, window: int) -> float | None:
    """Seconds until usage crosses the red line, from the observed burn rate.

    Idle-aware: each gap between samples contributes at most IDLE_GAP seconds
    to the span, so a lunch break doesn't dilute the rate into a promise of
    hours of runway. Only answers when the history can carry the claim.
    """
    growth_total = 0
    growth_count = 0
    span_eff = 0.0
    for (a, t1), (b, t2) in zip(samples, samples[1:]):
        span_eff += min(t2 - t1, IDLE_GAP)
        if b > a:                             # compaction drops filtered out
            growth_total += b - a
            growth_count += 1
    if growth_count < MIN_ETA_GROWTHS or span_eff < MIN_ETA_SPAN:
        return None
    tokens_to_red = window * YELLOW_BELOW / 100 - used_tokens
    if tokens_to_red <= 0 or growth_total <= 0:
        return None
    return tokens_to_red / (growth_total / span_eff)
```

- [ ] **Step 4: Run tests to verify pass, then the whole suite**

Run: `pytest tests/test_context_meter.py -q -k "idle_gap or red_eta"` then `pytest tests/ -q`
Expected: all pass — `test_red_eta_shown_with_enough_history` still passes (its gaps are 120s < IDLE_GAP, so nothing is capped).

- [ ] **Step 5: Commit**

```bash
git add skills/context-meter/scripts/context_meter.py tests/test_context_meter.py
git commit -m "feat(context-meter): idle-aware time-to-red (gaps capped at 10m)"
```

---

### Task 8: Recency-weighted next-turn estimate

**Files:**
- Modify: `skills/context-meter/scripts/context_meter.py` (replace `_median` with `_wmedian` in `_predict_next`)
- Modify: `tests/test_context_meter.py`

**Interfaces:**
- Produces: `_wmedian(values: list) -> float` — weighted median where the i-th value (chronological order) carries weight `i+1`. Replaces `_median` (delete `_median`; `_predict_next` is its only caller).

- [ ] **Step 1: Write the failing test** (append to `tests/test_context_meter.py`)

```python
def test_next_estimate_weights_recent_turns(env):
    now = time.time()
    # growths oldest->newest: 9k, 9k, 1k, 1k — the pace has slowed.
    seed_state(env, "recent", {"samples": [
        [100_000, now - 50], [109_000, now - 40], [118_000, now - 30],
        [119_000, now - 20], [120_000, now - 10],
    ]})
    out = run(payload_tokens("recent", 120_000))   # == last sample: no new growth
    # plain median of [9k,9k,1k,1k] = 5k -> next ~62%; recency-weighted
    # median = 1k -> next ~60%. Span < MIN_ETA_SPAN so next~ (not red~) shows.
    assert "next ~60%" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_context_meter.py -q -k weights_recent`
Expected: FAIL — current output says `next ~62%` (plain median).

- [ ] **Step 3: Implement**

Replace `_median` with:

```python
def _wmedian(values: list) -> float:
    """Recency-weighted median: the i-th value (oldest first) carries weight
    i+1, so a change of pace shows quickly while one huge turn still can't
    dominate the estimate."""
    pairs = sorted(zip(values, range(1, len(values) + 1)))
    half = sum(w for _, w in pairs) / 2
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= half:
            return float(v)
    return float(pairs[-1][0])
```

and in `_predict_next` change `round(_median(growths))` to `round(_wmedian(growths))`. Delete the now-unused `_median`.

- [ ] **Step 4: Run the whole suite**

Run: `pytest tests/ -q`
Expected: all pass — `test_red_eta_shown_with_enough_history` asserts on `red ~` (ETA path, unaffected), and `test_next_fallback_when_history_thin` has a single growth (any median of one value is that value).

- [ ] **Step 5: Commit**

```bash
git add skills/context-meter/scripts/context_meter.py tests/test_context_meter.py
git commit -m "feat(context-meter): recency-weighted next-turn estimate"
```

---

### Task 9: Learned red line

**Files:**
- Modify: `skills/context-meter/scripts/context_meter.py`
- Modify: `tests/test_context_meter.py`

**Interfaces:**
- Produces: constants `RED_MARGIN = 5.0`, `RED_FLOOR = 50.0`; `_red_pct(state: dict) -> float` (the effective red line: `YELLOW_BELOW`, pulled down to `max(RED_FLOOR, min(observed compaction %) − RED_MARGIN)` once compactions have been observed); `_append_sample(state, used_tokens, now, window)` (gains `window`, records `state["compaction_pcts"]`, last 5 kept); `_light(pct, red_pct)` and `_red_eta(samples, used_tokens, window, red_pct)` (both gain the red threshold parameter).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_context_meter.py`)

```python
def test_compaction_records_observed_pct(env):
    t0 = time.time() - 120
    seed_state(env, "learn", {"samples": [[100_000, t0], [150_000, t0 + 60]]})
    run(payload_tokens("learn", 60_000))          # drop => compaction at 75%
    state = json.loads((env / "state" / "learn.json").read_text(encoding="utf-8"))
    assert state["compaction_pcts"] == [75.0]


def test_learned_red_line_lowers_threshold(env):
    seed_state(env, "learned", {"compaction_pcts": [72.0]})
    out = run(payload_tokens("learned", 136_000))  # 68% >= learned red (67%)
    assert out.startswith("🔴 68% (")
    assert "→ handoff?" in out


def test_default_red_line_without_observations(env):
    out = run(payload_tokens("plain84", 168_000))  # 84% < default red 85%
    assert out.startswith("🟡 84% (")
    assert "handoff" not in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_context_meter.py -q -k "learned or observed_pct or default_red"`
Expected: first two FAIL (no `compaction_pcts`, 68% renders 🟡); third passes already.

- [ ] **Step 3: Implement**

Constants at the top:

```python
RED_MARGIN = 5.0      # stay this many points under an observed compaction
RED_FLOOR = 50.0      # never learn a red line below this
```

Extend `_append_sample` (new `window` parameter; update its call in `render` to `_append_sample(state, used_tokens, time.time(), window)`):

```python
    if samples and used_tokens < samples[-1][0]:
        state["compactions"] = state.get("compactions", 0) + 1
        if window:
            pcts = state.get("compaction_pcts") or []
            pcts.append(round(samples[-1][0] / window * 100, 1))
            state["compaction_pcts"] = pcts[-5:]
```

Add:

```python
def _red_pct(state: dict) -> float:
    """The effective red line: the configured constant, pulled down toward the
    lowest usage %% at which this machine actually compacted (minus a margin).
    Observed truth beats the guessed constant."""
    pcts = [
        p for p in (state.get("compaction_pcts") or [])
        if isinstance(p, (int, float))
    ]
    if not pcts:
        return float(YELLOW_BELOW)
    return max(RED_FLOOR, min(float(YELLOW_BELOW), min(pcts) - RED_MARGIN))
```

Change `_light` to take the threshold:

```python
def _light(pct: float, red_pct: float) -> str:
    if pct >= red_pct:
        return "🔴"
    if pct >= GREEN_BELOW:
        return "🟡"
    return "🟢"
```

Give `_red_eta` the threshold — signature `(samples, used_tokens, window, red_pct)`; replace `window * YELLOW_BELOW / 100` with `window * red_pct / 100`.

In `render()`:

```python
    samples = _append_sample(state, used_tokens, time.time(), window)
    red = _red_pct(state)
    predicted = _predict_next(samples, used_tokens, window)
    eta = _red_eta(samples, used_tokens, window, red)
```

use `_light(used_pct, red)` in the line, and the handoff cue becomes:

```python
    if used_pct >= red or pred_pct >= red:
        line += " → handoff?"
```

- [ ] **Step 4: Run the whole suite**

Run: `pytest tests/ -q`
Expected: all pass — with no observed compactions `_red_pct` returns `YELLOW_BELOW` (85), so every earlier test and fixture is unchanged; `test_compaction_counter` still sees `↺1`.

- [ ] **Step 5: Commit**

```bash
git add skills/context-meter/scripts/context_meter.py tests/test_context_meter.py
git commit -m "feat(context-meter): red line learned from observed compactions"
```

---

### Task 10: SKILL.md v3 (agent-led setup), sample payload, CHANGELOG

**Files:**
- Create: `skills/context-meter/scripts/sample.json`
- Modify: `skills/context-meter/SKILL.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: everything shipped in Tasks 2–9 (documents it).
- Produces: `scripts/sample.json` — the payload the setup flow pipes through the configured command to verify the wiring.

- [ ] **Step 1: Create the sample payload**

`skills/context-meter/scripts/sample.json`:

```json
{
  "session_id": "setup-verify",
  "context_window": {
    "context_window_size": 200000,
    "total_input_tokens": 130000,
    "total_output_tokens": 12000
  },
  "model": {"id": "claude-sonnet-5", "display_name": "Claude Sonnet 5"}
}
```

- [ ] **Step 2: Rewrite SKILL.md's display docs and setup section**

Replace the example line at the top of the Overview with:

```
🟡 71% (142k/200k) · red ~35m · opus · main · step 3/7 · 23 turns · 1h42m · $0.42 · $0.25/h ↺1
```

Add to the segment bullet list (keeping the existing bullets for light/usage/red-eta/handoff/turns/cost/compactions, updated to the new format):

```markdown
- **`opus` / `main` / `step 3/7`** — the model you're on, the git branch
  (read from `.git/HEAD`, worktrees included — no git subprocess), and the
  current step from `workflow.json` when the project is step-wise. Segments
  that don't apply simply don't appear — in a non-stepwise repo the meter
  stays a plain context gauge.
- **`$0.42 · $0.25/h`** — session cost and its burn rate (shown once the
  session is ≥ 10 minutes old), when Claude Code sends a `cost` block.
- **Hiding segments** — set `CLAUDE_CONTEXT_METER_HIDE` to a comma-separated
  list from: `model`, `branch`, `step`, `turns`, `duration`, `cost`, `burn`,
  `compactions`. The context gauge, trajectory, and handoff cue always show.
- **The red line learns.** When a compaction is observed below the assumed
  85% mark, the red threshold adapts down (never below 50%) — observed truth
  beats the guessed constant.
```

Replace the whole **Enable it** section with:

```markdown
## Enable it (agent-led — just approve)
Ask Claude to enable the context meter; it will:

1. **Detect your Python** — probe `python`, `python3`, then `py` and use the
   first that runs (`<cmd> --version`). No interpreter found → it says so and
   points at python.org; nothing is written.
2. **Check for an existing status line** — a settings file has one
   `statusLine`. If one exists, Claude asks before replacing or chaining it —
   never clobbers.
3. **Write the block** to `~/.claude/settings.json` (or the project's
   `.claude/settings.json` — your choice):

   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "<detected-python> \"${CLAUDE_PLUGIN_ROOT}/skills/context-meter/scripts/context_meter.py\"",
       "padding": 0
     }
   }
   ```

   If `${CLAUDE_PLUGIN_ROOT}` isn't expanded in your Claude Code version,
   Claude substitutes the absolute plugin path instead (or copies
   `context_meter.py` anywhere — it has no dependencies).
4. **Verify before claiming success** — pipe the bundled
   `scripts/sample.json` through the exact configured command and confirm a
   traffic-light line comes back (`🟡 71% (142k/200k) · sonnet`). Only then
   report it enabled; reload Claude Code and the line appears.
```

Also update the `description:` frontmatter to mention the new segments, e.g. append: `Shows model, git branch, current step, cost and burn rate; segments can be hidden via CLAUDE_CONTEXT_METER_HIDE.`

- [ ] **Step 3: Add the CHANGELOG entry**

At the top of `CHANGELOG.md` (above the latest release section), add:

```markdown
## Unreleased

### context-meter v3
- Dashboard segments: model, git branch (from `.git/HEAD`, worktree-aware),
  current step from `workflow.json`, and cost burn rate (`$/h`).
- `CLAUDE_CONTEXT_METER_HIDE` opt-out for individual segments.
- Idle-aware time-to-red (gaps capped at 10 min), recency-weighted next-turn
  estimate, and a red line learned from observed compactions.
- Agent-led setup: interpreter auto-detection (`python`/`python3`/`py`),
  settings written for you, verified against `scripts/sample.json`.
- Golden-fixture regression suite pinning exact output lines.
```

(If `CHANGELOG.md` uses a different heading convention, match it — but the content above goes in verbatim.)

- [ ] **Step 4: Run the whole suite**

Run: `pytest tests/ -q`
Expected: all pass (`test_skills_structure.py` validates frontmatter — the edited description must remain a single YAML string).

- [ ] **Step 5: Commit**

```bash
git add skills/context-meter/ CHANGELOG.md
git commit -m "docs(context-meter): v3 SKILL.md with agent-led setup + sample payload"
```
