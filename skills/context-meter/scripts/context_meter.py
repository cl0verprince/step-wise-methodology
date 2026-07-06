"""Context-usage traffic light for the Claude Code status line.

Reads the status-line JSON on stdin (documented at
https://code.claude.com/docs/en/statusline.md) and prints ONE compact line:

    🟢 12% ctx (98k/1.0M) · next ~15%

- Traffic light 🟢/🟡/🔴 for how full the context window is right now.
- Live token count and the true window size (200k or the extended 1M).
- "next ~N%" — an estimate of where the window will be after the next turn,
  from the moving average of recent per-turn growth. Honest, not precise: the
  dominant unknown is how large the next tool result is, so it is shown as an
  estimate and flagged ⚠ when the next turn is likely to cross the red line.

Everything comes from the stdin JSON — the large transcript JSONL is never
read. Prediction needs cross-invocation memory, so a tiny bounded state file
(the last few readings per session) is kept in a temp dir. Every side effect is
guarded: a status line must NEVER crash or hang, so on any error this prints a
neutral fallback and exits 0. No network, ever.

Usage (wire into settings.json, see the skill's SKILL.md):
    "statusLine": { "type": "command",
                    "command": "python \"…/context_meter.py\"" }
"""
import json
import os
import sys
import tempfile
from pathlib import Path

# Traffic light thresholds, as a percentage of the context window used.
# RED is set below Claude Code's auto-compaction point to give real runway.
GREEN_BELOW = 60      # < 60%  -> 🟢
YELLOW_BELOW = 85     # 60–85% -> 🟡 ; >= 85% -> 🔴

MAX_SAMPLES = 12      # rolling history kept per session for the prediction


def _fmt_tokens(n: int) -> str:
    """98000 -> '98k', 1000000 -> '1.0M'. Compact for a one-line status."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{round(n / 1_000)}k"
    return str(n)


def _light(pct: float) -> str:
    if pct < GREEN_BELOW:
        return "🟢"
    if pct < YELLOW_BELOW:
        return "🟡"
    return "🔴"


def _state_path(session_id: str) -> Path:
    """Per-session history file in a temp dir (never under Claude's own dirs)."""
    base = os.environ.get("CLAUDE_CONTEXT_METER_DIR") or (
        Path(tempfile.gettempdir()) / "claude-context-meter"
    )
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    # Session ids are uuids; strip anything odd just in case it feeds a filename.
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_") or "session"
    return base / f"{safe}.json"


def _update_history(session_id: str, used_tokens: int) -> list:
    """Append used_tokens if it changed (a real turn), return recent samples.

    Guarded: if the state file can't be read or written, prediction is simply
    skipped — it must never take the status line down.
    """
    if not session_id:
        return []
    path = _state_path(session_id)
    samples = []
    try:
        samples = json.loads(path.read_text(encoding="utf-8")).get("samples", [])
    except (OSError, ValueError):
        samples = []

    # Only record a new point when the window actually grew/changed — status
    # lines re-run on a timer too, and those idle re-runs must not skew deltas.
    if not samples or samples[-1] != used_tokens:
        samples.append(used_tokens)
    samples = samples[-MAX_SAMPLES:]

    try:  # atomic-ish write; failure just means no persisted history this run
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"samples": samples}), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass
    return samples


def _predict_next(samples: list, used_tokens: int, window: int) -> int | None:
    """Estimate next-turn used tokens from the mean of recent positive deltas.

    Compaction drops the total; those negative deltas are ignored so a recent
    compaction doesn't make the meter predict shrinkage. Returns None when there
    isn't enough history to say anything honest.
    """
    growths = [b - a for a, b in zip(samples, samples[1:]) if b > a]
    if not growths:
        return None
    avg_growth = sum(growths) / len(growths)
    return min(used_tokens + round(avg_growth), window)


def render(data: dict) -> str:
    """Pure: status JSON -> the one-line string. All logic is testable here."""
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

    samples = _update_history(data.get("session_id", ""), used_tokens)
    predicted = _predict_next(samples, used_tokens, window)

    line = (
        f"{_light(used_pct)} {round(used_pct)}% ctx "
        f"({_fmt_tokens(used_tokens)}/{_fmt_tokens(window)})"
    )
    if predicted is not None:
        pred_pct = predicted / window * 100
        warn = " ⚠" if pred_pct >= YELLOW_BELOW > used_pct else ""
        line += f" · next ~{round(pred_pct)}%{warn}"
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
