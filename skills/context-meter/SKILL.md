---
name: context-meter
description: Use when the user wants to see context-window usage, time until the context runs red, session turn count, duration, or cost in Claude Code — a traffic-light status line at the bottom of the Claude Code pane in PyCharm / VS Code (or any terminal), with a handoff cue when context runs out. Explains how to enable the bundled context_meter.py status-line script. Shows model, git branch, current step, cost and burn rate; segments can be hidden via CLAUDE_CONTEXT_METER_HIDE.
---

# Context Meter

## Overview
A **status-line script** that turns Claude Code's per-turn data into one
glanceable line:

```
🟡 71% (142k/200k) · red ~35m · opus · main · step 3/7 · 23 turns · 1h42m · $0.42 · $0.25/h ↺1
```

- **Traffic light** — 🟢 under 60%, 🟡 60–85%, 🔴 at/above 85% of the window.
- **Live usage** — real tokens in the window and the true window size
  (`200k`, or `1.0M` on extended-context models — read from the JSON, never
  guessed from the model name).
- **`red ~35m`** — estimated time until usage crosses the red line, from the
  median observed burn rate, with idle gaps capped at 10 minutes. Early in a
  session (before the history can carry that claim) it falls back to
  **`next ~N%`**, the estimate one turn ahead (recency-weighted) — one of the
  two shows, never both.
- **`→ handoff?`** — appears when usage is at red, or predicted to cross it
  next turn. This is the cue the methodology promises: see `session-handoff`.
- **`opus` / `main` / `step 3/7`** — the model you're on, the git branch
  (read from `.git/HEAD`, worktrees included — no git subprocess), and the
  current step from `workflow.json` when the project is step-wise. Segments
  that don't apply simply don't appear — in a non-stepwise repo the meter
  stays a plain context gauge.
- **`23 turns · 1h42m`** — how many exchanges (real user prompts — tool
  results and meta entries don't count) the session has had, and how long it
  has been running.
- **`$0.42 · $0.25/h`** — session cost and its burn rate (shown once the
  session is ≥ 10 minutes old), when Claude Code sends a `cost` block.
- **Hiding segments** — set `CLAUDE_CONTEXT_METER_HIDE` to a comma-separated
  list from: `model`, `branch`, `step`, `turns`, `duration`, `cost`, `burn`,
  `compactions`. The context gauge, trajectory, and handoff cue always show.
- **`↺1`** — how many context compactions have been detected (explains a
  percentage that suddenly dropped).
- **The red line learns.** When a compaction is observed below the assumed
  85% mark, the red threshold adapts down (never below 50%) — observed truth
  beats the guessed constant.

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
