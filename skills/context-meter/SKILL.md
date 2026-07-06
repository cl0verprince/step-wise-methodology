---
name: context-meter
description: Use when the user wants to see context-window usage in Claude Code — a traffic-light status line showing how full the context is now and an estimate of where it lands after the next turn, embedded at the bottom of the Claude Code pane in PyCharm / VS Code (or any terminal). Explains how to enable the bundled context_meter.py status-line script.
---

# Context Meter

## Overview
A **status-line script** that turns Claude Code's per-turn token data into one
glanceable line:

```
🟢 12% ctx (98k/1.0M) · next ~15%
```

- **Traffic light** — 🟢 under 60%, 🟡 60–85%, 🔴 at/above 85% of the window.
- **Live usage** — real tokens in the window and the true window size
  (`200k`, or `1.0M` on extended-context models — read from the JSON, never
  guessed from the model name).
- **`next ~N%`** — an estimate of the window after the next turn. It shows a
  `⚠` when that next turn is likely to cross into the red.

It renders at the **bottom of the Claude Code pane** — which, running inside
the PyCharm or VS Code integrated terminal / extension, is where "embedded in
the IDE" happens. A plugin has no other native panel; the status line is the
surface.

## How the numbers are computed (so you can trust — and correct — them)
Claude Code passes the status line a JSON object on stdin containing a
`context_window` block (`context_window_size`, `total_input_tokens`,
`used_percentage`, …). The script uses **only that** — it never opens the
transcript JSONL, so it stays instant and cannot choke on a large session.

**The estimate is deliberately honest, not falsely precise.** Current usage is a
floor: it carries forward as cache each turn, so context only grows (until a
compaction). `next ~N%` = current + the **moving average of recent per-turn
growth**, kept in a tiny per-session history file. The real unknown is how big
the next tool result is — genuinely unpredictable — so treat `next` as a
trend signal ("am I about to run out of room?"), not a promise. Thresholds live
as named constants (`GREEN_BELOW`, `YELLOW_BELOW`) at the top of the script;
change them there if your compaction point differs.

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

- **Windows:** use `python`. **macOS / Linux:** use `python3`.
- If `${CLAUDE_PLUGIN_ROOT}` isn't expanded in your Claude Code version, replace
  it with the absolute path to the installed plugin (or copy `context_meter.py`
  anywhere and point at that copy — it has no dependencies).
- Reload Claude Code. The line appears at the bottom of the pane and updates as
  the conversation grows.

## Guarantees (it must never get in the way)
- **Never crashes the status line.** Any error → it prints a neutral `⚪ ctx n/a`
  and exits 0. Emoji are written as UTF-8 bytes so a Windows cp1252 console
  can't fail on them.
- **No network, ever.** Reads stdin, writes one line.
- **Tiny, bounded state.** Prediction history is a few numbers per session in a
  temp dir (override with `CLAUDE_CONTEXT_METER_DIR`); it never touches Claude's
  own directories and is capped in size.
