---
name: deterministic-conductors
description: Use when building the entry point that runs a project's pipeline end-to-end, or wiring steps together — to make it a single reproducible "conductor" (same inputs + config produce the same output every run) with a live progress bar, in any language.
---

# Deterministic Conductors

## Overview
A **conductor** is the single entry point that runs the pipeline. It is a **role, not a language** — `conductor.py`, `conductor.mjs`, a `Makefile`, or a shell script all qualify. Two levels:
- **General conductor** — runs the *whole* pipeline in order; reproduces the Required Output from scratch, with no hidden manual steps.
- **Step conductor** — runs *one* step in isolation (its UAT drives this).

**The defining property is determinism:** same inputs + same `config` → **the same output, every run**. A runner that isn't reproducible is not a conductor.

Observed failure this closes: agents readily build a working single entry point, but it produces different output on every run because nothing is seeded.

## Determinism rules
- **Seed all randomness** from `config` — one seed, applied in every step that uses an RNG. If steps run as subprocesses, pass the seed through and each seeds itself.
- **No reliance on wall-clock or unpinned ordering** — don't let `now()` or set/dict iteration order change results.
- **Pin dependency versions.**
- **Make paths configurable** — never hardcode machine-specific absolute paths.
- **Isolate and document** any non-deterministic external service (LLM/API call) as an explicit, labelled boundary.

## Live progress bar (required)
Every conductor run shows a live, **in-place** bar (redraws on the same line via carriage-return) with **percentage, a filled/empty bar, and elapsed time** (add ETA when the total is known); print a final line at 100%. Prefer a small library — `tqdm` / `rich` (Python), `cli-progress` / `ora` (Node), `indicatif` (Rust), `pv` (shell) — over hand-rolled log spam.

## Templates
Start from `templates/conductor.py`, `templates/conductor.mjs`, or `templates/conductor.sh` — each seeds from config, shows an in-place progress bar, and runs the steps in order.

## When re-invoked — extend, don't rebuild
A conductor already exists? Add to it — never generate a fresh skeleton beside
or over it:
- **New step:** register the new step (appended, or inserted mid-list) in the
  existing pipeline list (the templates' `build_pipeline()`), seeded and
  pinned like the rest, in the order `plan.md` states.
- **Keep it in step with `workflow.json`:** the steps the conductor runs and
  the steps the status file tracks are the same list — update both in the
  same change.
- **Wire docs regeneration** as the pipeline's final step — run
  `render_docs.py` (see `browser-readable-project-docs`) so the browser docs
  can never go stale.

## Red flags — STOP
- A second entry point appearing (`run_all.py` next to `conductor.py`) — one conductor, extended
- Two runs with the same config producing different output — that's not a conductor
- A step wired into the conductor but missing from `workflow.json`, or vice versa
- A hardcoded absolute path or an unseeded RNG smuggled in with a new step
