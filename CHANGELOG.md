# Changelog

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

## 0.7.0 — 2026-07-14
- **New skill: `adopting-existing-projects`** — brings the methodology to
  codebases that weren't built with it. Read-only survey first, then the
  human chooses the depth: **Ride** (learn conventions into `CLAUDE.md`, no
  restructuring), **Adopt** (state model mapped onto existing structures —
  the project's Makefile *is* the conductor; history as forward-only
  baseline / milestones / full reconstruction), or **Rebuild**
  (double-confirmed re-engineering). Test-less projects get a
  characterization safety net before any behavior change.
  `stepwise-delivery` Phase R now routes here when a non-empty repo has no
  state files.
- **context-meter v2**: `red ~35m` time-to-red from the median burn rate
  (timestamped samples; falls back to `next ~N%` until history suffices),
  `→ handoff?` cue at/predicted red, session cost (`$0.42`,
  feature-detected), compaction counter (`↺1`), median instead of mean for
  growth. Pre-0.7 state files reset gracefully.

## 0.6.0 — 2026-07-13
- **New `awaiting_approval` step status** (built, UAT green, stopped at the human
  gate) — added to `workflow.json`'s vocabulary, `render_docs.py` (purple),
  `stepwise-delivery`, and the `HANDOFF.md` template (which previously used a
  non-canonical `blocked`).
- **Fixed** the Stage D branch-protection command in `pipeline-architect`: the
  boolean/integer fields now use `gh api -F` (typed) — with `-f` GitHub rejects
  the request with HTTP 422.
- **Least-privilege CI template**: `ci.yml` permissions moved to job level —
  `gates` (which runs project code) is read-only; only `release` can write.
- Conductor template hardening: `conductor.sh` drops `eval` (function-per-step)
  and fixes a progress-bar off-by-one; `conductor.py` no longer KeyErrors on a
  seedless `config.json`; `conductor.mjs` exits non-zero on a failed step.
- Added `LICENSE` (MIT — previously declared but not present), this changelog,
  a `tests/` suite for the bundled scripts, and a CI workflow for this repo.
- `plan.md` template's step0 now mentions the CI pipeline; marketplace keywords
  extended (ci-cd, github, pipeline, testing).

## 0.5.0 — 2026-07-13
- **Project state model** codified: `plan.md` (contract) / `workflow.json`
  (canonical step status) / `pipeline.md` (delivery posture) / `HANDOFF.md`
  (volatile session memory), with the house re-entry rule: detect before
  create, reconcile and extend, never re-scaffold.
- `stepwise-delivery`: **Phase R re-entry** — read the state files, report the
  project's position, resume at the right phase.
- Re-invocation flows added to `authoring-the-master-plan` (review/amend),
  `deterministic-conductors` (extend, don't rebuild), `secret-safe-commits`
  (merge an existing `.gitignore`), `agentic-step-execution` (reuse roles).
- `context-meter`: **turn count + session duration** in the status line, via
  incremental (byte-offset) transcript tailing; never-crash guarantee kept.

## 0.4.0 — 2026-07-13
- `pipeline-architect` rebuilt around a **staged, approval-gated flow**
  (bootstrap → classify → commit → branch protection → first green run),
  including git/GitHub bootstrap with existing-state detection.
- **Gate maturity ladder (L0–L3)** with a per-project selection rubric and new
  unit-test / lint+format / coverage / type-check gates; state recorded in the
  project's `pipeline.md` (new template).

## 0.3.0 — 2026-07-10
- Added the `pipeline-architect` skill (archetype classification + CI baseline).

## 0.2.0 — 2026-07-08
- Model policy: Opus designs/reviews, Sonnet executes.

## 0.1.0 — 2026-07-07
- Initial skills: `stepwise-delivery`, `authoring-the-master-plan`,
  `deterministic-conductors`, `browser-readable-project-docs`,
  `secret-safe-commits`, `craftsmanship-bar`, `agentic-step-execution`,
  `context-meter`, `session-handoff`.
