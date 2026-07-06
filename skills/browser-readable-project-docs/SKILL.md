---
name: browser-readable-project-docs
description: Use when keeping a project's decision log and step-flow diagram as offline, double-clickable HTML (reflection.html and workflow.html), updated as decisions are made and the flow changes — for a human who wants to open and read the record in a browser.
---

# Browser-Readable Project Docs

## Overview
Two offline, self-contained HTML pages let a human **double-click and read** the project's living record — no server, no internet:
- `reflection.html` — a log of key decisions, each with its rationale.
- `workflow.html` — a visual diagram of the current step flow.

**Do not hand-write the HTML.** Maintain two small data files and let the bundled script own the markup. Hand-rolled HTML comes out a different size and style every time (observed: 90 vs 300+ lines for the *same* content across agents), drifts on every edit, and burns tokens. Data + one script → one consistent house style, deterministic, auto-escaped, guaranteed offline.

## How to use
1. **At step 0**, copy the bundled `scripts/render_docs.py` into the project (e.g. `scripts/`), and create two data files:
   ```json
   // decisions.json
   [{"date": "2026-07-07", "decision": "...", "rationale": "..."}]
   // workflow.json
   {"steps": [{"name": "step0_setup", "status": "done"},
              {"name": "step1_cli",   "status": "in_progress"}]}
   ```
   `status` is `done` | `in_progress` | `pending`. Convert relative dates ("today") to absolute.
2. **As each decision is made,** append to `decisions.json`; **when the flow changes,** update `workflow.json`. Don't batch — record as it happens.
3. Regenerate the pages:
   ```
   python scripts/render_docs.py --decisions decisions.json --workflow workflow.json --out-dir .
   ```
   Open `reflection.html` / `workflow.html` by double-clicking.

The script is stdlib-only and self-contained (inline CSS + inline SVG). Same data → the same pages, every run. Wire the regenerate command into the conductor so the docs never go stale.
