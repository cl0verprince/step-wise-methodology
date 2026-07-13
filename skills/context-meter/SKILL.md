---
name: context-meter
description: Use when the user wants to see context-window usage, time until the context runs red, session turn count, duration, or cost in Claude Code — a traffic-light status line at the bottom of the Claude Code pane in PyCharm / VS Code (or any terminal), with a handoff cue when context runs out. Explains how to enable the bundled context_meter.py status-line script.
---

# Context Meter

## Overview
A **status-line script** that turns Claude Code's per-turn data into one
glanceable line:

```
🟡 71% ctx (142k/200k) · red ~35m · 23 turns · 1h42m · $0.42 ↺1
```

- **Traffic light** — 🟢 under 60%, 🟡 60–85%, 🔴 at/above 85% of the window.
- **Live usage** — real tokens in the window and the true window size
  (`200k`, or `1.0M` on extended-context models — read from the JSON, never
  guessed from the model name).
- **`red ~35m`** — estimated time until usage crosses the red line, from the
  median observed burn rate. Early in a session (before the history can carry
  that claim) it falls back to **`next ~N%`**, the estimate one turn ahead —
  one of the two shows, never both.
- **`→ handoff?`** — appears when usage is at red, or predicted to cross it
  next turn. This is the cue the methodology promises: see `session-handoff`.
- **`23 turns · 1h42m`** — how many exchanges (real user prompts — tool
  results and meta entries don't count) the session has had, and how long it
  has been running.
- **`$0.42`** — session cost, when the Claude Code payload carries a `cost`
  block (feature-detected; nothing shows on older versions).
- **`↺1`** — how many context compactions have been detected (explains a
  percentage that suddenly dropped).

It renders at the **bottom of the Claude Code pane** — which, running inside
the PyCharm or VS Code integrated terminal / extension, is where "embedded in
the IDE" happens. A plugin has no other native panel; the status line is the
surface.

## How the numbers are computed (so you can trust — and correct — them)
Claude Code passes the status line a JSON object on stdin containing a
`context_window` block (`context_window_size`, `total_input_tokens`,
`total_output_tokens`, `used_percentage`, …) plus `session_id` and
`transcript_path`. Token math uses **only the stdin JSON**.

**Turns and duration come from the transcript, read incrementally.** The
script keeps a byte offset per session and reads only the lines appended
since the last tick — a full pass happens once, the first time a session is
seen (measured ~50ms for a 20k-line transcript). A "turn" is a user-typed
prompt; tool results flowing back and meta entries are filtered out. Session
duration is measured from the first timestamp in the transcript.

**The estimates are deliberately honest, not falsely precise.** Current usage
is a floor: it carries forward as cache each turn, so context only grows
(until a compaction). The script keeps a few **timestamped samples** per
session; `red ~35m` divides the distance to red by the observed token burn
rate, and refuses to answer (falling back to `next ~N%`, the **median**
per-turn growth) until it has at least 3 growth samples over ≥60s. The real
unknown is how big the next tool result is — genuinely unpredictable — so
treat both as trend signals ("am I about to run out of room?"), not promises.
Thresholds live as named constants (`GREEN_BELOW`, `YELLOW_BELOW`,
`MIN_ETA_GROWTHS`, `MIN_ETA_SPAN`) at the top of the script; change them
there if your compaction point differs.

## Enable it
The script is bundled at `scripts/context_meter.py` (stdlib-only, no install).
Add a `statusLine` block to `settings.json` (user-level
`~/.claude/settings.json`, or project `.claude/settings.json`):

```json
{
  "statusLine": {
    "type": "command",
    "command": "python \"${CLAUDE_PLUGIN_ROOT}/skills/context-meter/scripts/context_meter.py\"",
    "padding": 0
  }
}
```

- **A `statusLine` block already exists?** Don't clobber it — a settings file
  has one status line. Ask before replacing, or chain the commands if the
  user wants both.
- **Windows:** use `python`. **macOS / Linux:** use `python3`.
- If `${CLAUDE_PLUGIN_ROOT}` isn't expanded in your Claude Code version, replace
  it with the absolute path to the installed plugin (or copy `context_meter.py`
  anywhere and point at that copy — it has no dependencies).
- Reload Claude Code. The line appears at the bottom of the pane and updates as
  the conversation grows.

## Guarantees (it must never get in the way)
- **Never crashes the status line.** Any error → it prints a neutral `⚪ ctx n/a`
  and exits 0; a transcript that can't be read just drops the turns/duration
  segment. Emoji are written as UTF-8 bytes so a Windows cp1252 console can't
  fail on them.
- **No network, ever.** Reads stdin + appended transcript bytes, writes one line.
- **Tiny, bounded state.** Prediction history and the transcript offset are a
  few values per session in a temp dir (override with
  `CLAUDE_CONTEXT_METER_DIR`); it never touches Claude's own directories and is
  capped in size.
