"""Context-usage traffic light for the Claude Code status line.

Reads the status-line JSON on stdin (documented at
https://code.claude.com/docs/en/statusline.md) and prints ONE compact line:

    🟡 71% (142k/200k) · red ~35m · opus · main · step 3/7 · 23 turns · 1h42m · $0.42 · $0.25/h ↺1

- Traffic light 🟢/🟡/🔴 for how full the context window is right now.
- Live token count and the true window size (200k or the extended 1M).
- "red ~35m" — estimated time until usage crosses the red line, from the
  median growth rate of recent turns. Shown only once there is enough
  history to be honest (else it falls back to "next ~N%", the estimated
  usage after one more turn). "→ handoff?" appears when usage is at or
  predicted to cross red — the cue to run the session-handoff skill.
- "23 turns · 1h42m" — exchanges (real user prompts) and session runtime,
  from the transcript JSONL.
- "$0.42" — session cost, when the payload carries a cost block.
- "↺1" — how many context compactions have been detected this session.

Token math comes from the stdin JSON alone. The transcript is read
INCREMENTALLY: a byte offset is kept per session, so each status-line tick
reads only the lines appended since the last one — one full pass is paid only
the first time a session is seen. Turns are counted by cheap substring checks
(no per-line JSON parsing): a turn is a user-typed prompt, not a tool result
flowing back and not a meta entry.

Cross-invocation memory (timestamped samples, transcript offset/tally,
compaction count) lives in a tiny bounded state file per session in a temp
dir. Every side effect is guarded: a status line must NEVER crash or hang, so
on any error this prints a neutral fallback and exits 0. No network, ever.

Usage (wire into settings.json, see the skill's SKILL.md):
    "statusLine": { "type": "command",
                    "command": "python \"…/context_meter.py\"" }
"""
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Traffic light thresholds, as a percentage of the context window used.
# RED is set below Claude Code's auto-compaction point to give real runway.
GREEN_BELOW = 60      # < 60%  -> 🟢
YELLOW_BELOW = 85     # 60–85% -> 🟡 ; >= 85% -> 🔴 (also the handoff cue line)

# Learned red line: compactions are observed when token usage drops.
RED_MARGIN = 5.0      # stay this many points under an observed compaction
RED_FLOOR = 50.0      # never learn a red line below this

MAX_SAMPLES = 12      # rolling history kept per session for the estimates
MIN_ETA_GROWTHS = 3   # growth samples needed before "red ~Xm" is honest
MIN_ETA_SPAN = 60.0   # seconds of history needed before a rate means anything
IDLE_GAP = 600.0      # cap each inter-sample gap at 10min in burn-rate math
BURN_MIN_AGE = 600.0  # seconds of session age before $/h is meaningful


def _fmt_tokens(n: int) -> str:
    """98000 -> '98k', 1000000 -> '1.0M'. Compact for a one-line status."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{round(n / 1_000)}k"
    return str(n)


def _fmt_duration(seconds: float) -> str:
    """95s -> '1m', 6120s -> '1h42m'. Coarse on purpose — it's a glance."""
    minutes = int(seconds // 60)
    if minutes < 1:
        return f"{max(int(seconds), 0)}s"
    if minutes < 60:
        return f"{minutes}m"
    return f"{minutes // 60}h{minutes % 60:02d}m"


def _light(pct: float, red_pct: float) -> str:
    if pct >= red_pct:
        return "🔴"
    if pct >= GREEN_BELOW:
        return "🟡"
    return "🟢"


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


def _hidden() -> set:
    """Segment names the user opted out of, e.g. HIDE='branch,model'."""
    raw = os.environ.get("CLAUDE_CONTEXT_METER_HIDE", "")
    return {s.strip().lower() for s in raw.split(",") if s.strip()}


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
    except (OSError, ValueError, TypeError, AttributeError):
        seg = None
    state["workflow"] = {"path": str(wf), "mtime": mtime, "seg": seg}
    return seg


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


def _state_path(session_id: str) -> Path:
    """Per-session state file in a temp dir (never under Claude's own dirs)."""
    base = os.environ.get("CLAUDE_CONTEXT_METER_DIR") or (
        Path(tempfile.gettempdir()) / "claude-context-meter"
    )
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    # Session ids are uuids; strip anything odd just in case it feeds a filename.
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_") or "session"
    return base / f"{safe}.json"


def _load_state(path: Path) -> dict:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(path: Path, state: dict) -> None:
    """Atomic-ish write; failure just means no persisted memory this run."""
    try:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def _append_sample(state: dict, used_tokens: int, now: float, window: int | None) -> list:
    """Record [tokens, timestamp] if tokens changed (a real turn).

    Status lines re-run on a timer too; those idle re-runs must not skew the
    growth estimates, so unchanged readings are not appended. A drop in the
    total is a compaction — counted, then sampled like any other point (the
    negative delta is filtered out of the growth math downstream).
    Pre-0.7 state files held bare ints; those are reset, not migrated.
    """
    samples = state.get("samples")
    if not isinstance(samples, list) or any(
        not (isinstance(s, list) and len(s) == 2) for s in samples
    ):
        samples = []
    if samples and used_tokens < samples[-1][0]:
        state["compactions"] = state.get("compactions", 0) + 1
        if window:
            pcts = state.get("compaction_pcts") or []
            pcts.append(round(samples[-1][0] / window * 100, 1))
            state["compaction_pcts"] = pcts[-5:]
    if not samples or samples[-1][0] != used_tokens:
        samples.append([used_tokens, now])
    state["samples"] = samples[-MAX_SAMPLES:]
    return state["samples"]


def _growths(samples: list) -> list:
    """Positive per-turn token deltas (compaction drops filtered out)."""
    return [b - a for (a, _), (b, _) in zip(samples, samples[1:]) if b > a]


def _predict_next(samples: list, used_tokens: int, window: int) -> int | None:
    """Median-growth estimate of next-turn usage (robust to one huge turn)."""
    growths = _growths(samples)
    if not growths:
        return None
    return min(used_tokens + round(_wmedian(growths)), window)


def _red_eta(samples: list, used_tokens: int, window: int, red_pct: float) -> float | None:
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
    tokens_to_red = window * red_pct / 100 - used_tokens
    if tokens_to_red <= 0 or growth_total <= 0:
        return None
    return tokens_to_red / (growth_total / span_eff)


def _tally_transcript(state: dict, transcript_path: str) -> None:
    """Incrementally tally turns + session start from the transcript JSONL.

    Only bytes appended since the stored offset are read; the offset is rewound
    to the start of a trailing half-written line so it is re-read complete next
    tick. A turn = a line with a user type marker but no tool-result payload
    and no meta flag — substring checks keep this O(new bytes) with no JSON
    parsing. Errors leave the previous tally untouched.
    """
    if not transcript_path:
        return
    try:
        size = os.path.getsize(transcript_path)
    except OSError:
        return

    t = state.get("transcript")
    if (
        not isinstance(t, dict)
        or t.get("path") != transcript_path
        or t.get("offset", 0) > size          # file was replaced/truncated
    ):
        t = {"path": transcript_path, "offset": 0, "turns": 0, "start": None}

    try:
        with open(transcript_path, "rb") as fh:
            fh.seek(t["offset"])
            chunk = fh.read(size - t["offset"])
    except OSError:
        return

    lines = chunk.split(b"\n")
    partial = lines.pop()                     # possibly half-written last line
    t["offset"] = size - len(partial)

    for line in lines:
        if (b'"type":"user"' in line or b'"type": "user"' in line) and (
            b'"toolUseResult"' not in line and b'"isMeta":true' not in line
        ):
            t["turns"] += 1
        if t["start"] is None:
            marker = b'"timestamp":"'
            i = line.find(marker)
            if i >= 0:
                start = i + len(marker)
                t["start"] = line[start : start + 32].split(b'"')[0].decode(
                    "ascii", "replace"
                )

    state["transcript"] = t


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


def render(data: dict) -> str:
    """Status JSON -> the one-line string. All logic lives here, guarded."""
    cw = data.get("context_window") or {}
    window = cw.get("context_window_size")

    # Fallback for older Claude Code that predates context_window on stdin.
    if not window:
        if data.get("exceeds_200k_tokens"):
            return "🔴 ctx >200k"
        return "⚪ ctx n/a"

    used_tokens = (cw.get("total_input_tokens") or 0) + (
        cw.get("total_output_tokens") or 0
    )
    if used_tokens <= 0:
        return "⚪ ctx warming up"

    used_pct = cw.get("used_percentage")
    if used_pct is None:
        used_pct = used_tokens / window * 100

    session_id = data.get("session_id", "")
    state_file = _state_path(session_id) if session_id else None
    state = _load_state(state_file) if state_file else {}

    hide = _hidden()

    samples = _append_sample(state, used_tokens, time.time(), window)
    red = _red_pct(state)
    predicted = _predict_next(samples, used_tokens, window)
    eta = _red_eta(samples, used_tokens, window, red)
    try:
        _tally_transcript(state, data.get("transcript_path") or "")
    except Exception:
        pass                                  # tally is a bonus, never a risk

    root = _project_root(
        (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or ""
    )
    branch = _git_branch(root) if root else None
    step = _step_segment(root, state) if root else None

    if state_file:
        _save_state(state_file, state)

    line = (
        f"{_light(used_pct, red)} {round(used_pct)}% "
        f"({_fmt_tokens(used_tokens)}/{_fmt_tokens(window)})"
    )
    # Trajectory: the time-to-red ETA when history can carry it, else the
    # one-turn-ahead estimate. One of them, never both — the line is a glance.
    if eta is not None:
        line += f" · red ~{_fmt_duration(eta)}"
    elif predicted is not None:
        line += f" · next ~{round(predicted / window * 100)}%"

    # The cue the methodology promises: at (or predicted to cross) red,
    # point at the session-handoff skill.
    pred_pct = predicted / window * 100 if predicted is not None else 0
    if used_pct >= red or pred_pct >= red:
        line += " → handoff?"

    model = _short_model(data)
    if model and "model" not in hide:
        line += f" · {model}"

    if branch and "branch" not in hide:
        line += f" · {branch}"

    if step and "step" not in hide:
        line += f" · {step}"

    line += _session_suffix(state, hide)

    cost = (data.get("cost") or {}).get("total_cost_usd")
    if isinstance(cost, (int, float)) and cost > 0:
        if "cost" not in hide:
            line += f" · ${cost:.2f}"
        elapsed = _session_elapsed(state)
        if "burn" not in hide and elapsed and elapsed >= BURN_MIN_AGE:
            line += f" · ${cost / (elapsed / 3600):.2f}/h"

    compactions = state.get("compactions", 0)
    if compactions and "compactions" not in hide:
        line += f" ↺{compactions}"
    return line


def _emit(text: str) -> None:
    """Write UTF-8 bytes directly. The status line uses emoji, but a Windows
    console defaults to cp1252 and would crash encoding them on every redraw —
    writing to the byte buffer sidesteps the console's text encoder entirely.
    """
    try:
        sys.stdout.buffer.write(text.encode("utf-8"))
    except Exception:
        sys.stdout.write(text)  # last resort if there's no binary buffer


def main() -> None:
    try:
        _emit(render(json.load(sys.stdin)))
    except Exception:
        # A status line must never error-spam. Stay silent-but-safe.
        _emit("⚪ ctx n/a")


if __name__ == "__main__":
    main()
