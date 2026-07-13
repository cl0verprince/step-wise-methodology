---
name: stepwise-delivery
description: Use when starting any new project or building a major new feature, component, or subsystem from scratch — greenfield "let's build X" work worth doing in deliberate, planned, acceptance-tested, approval-gated numbered steps — AND when resuming or continuing an existing step-wise project ("continue the project", "where were we", a repo that already has plan.md/workflow.json). Drives the whole phased workflow and calls the other step-wise skills in order.
---

# Stepwise Delivery (orchestrator)

## Overview
This is the **conductor for the methodology itself** — it sequences the other
step-wise skills and enforces the one rule that makes the process safe: **the
human approves every step before the next one starts.** It does not re-implement
planning, testing, or fan-out; it says *when* each concern is active and *who
clears the gate*.

Left to default, agents collapse "build X" into one undifferentiated sprint —
no checkable contract, no per-step stop, docs drifting behind code. This skill
holds the shape.

## The phases (run in order)

**Phase R — Re-enter (whenever the project isn't empty).** Step-wise files
already exist? Read the **project state model** first — `plan.md` (the
contract), `workflow.json` (the canonical step status), `pipeline.md` (the
delivery posture), `HANDOFF.md` (the last session's volatile memory) — then
**report where the project stands** (current step, gate state, open threads)
and continue at the matching phase below. Never re-run scaffolding that
already exists, and never re-open a step marked `done` unless the human asks.
A missing file means that concern hasn't come up yet — supply it when its
phase arrives (a missing `HANDOFF.md` just means no handoff happened), never
by restarting. **No state files at all in a non-empty repo?** The project
predates the methodology — → `adopting-existing-projects` (survey it, then
the human chooses ride / adopt / rebuild).

**Phase 0 — Frame.** Before any file exists, settle *what* and *why*.
→ `superpowers:brainstorming` (required). Do not skip to planning until intent,
requirements, and design are actually explored.

**Phase 1 — Contract.** Write the master `plan.md`: a testable `# Goal`, a
concrete `# Required Output`, then the ordered `# Steps`.
→ `authoring-the-master-plan`. No steps until Goal + Required Output are nailed.

**Phase 2 — Scaffold (step 0).** Stand up the skeleton once:
→ `secret-safe-commits` (`.gitignore` + `.env.example` **before the first commit**),
→ `deterministic-conductors` (the reproducible entry-point skeleton),
→ `browser-readable-project-docs` (copy `render_docs.py`, seed `decisions.json` /
`workflow.json`),
→ `pipeline-architect` (connect the repo to GitHub if it isn't — init, first
push, branch protection — then derive the CI gates from `plan.md`'s Required
Output and the maturity ladder, in staged, per-stage-approved setup; record
the level in `pipeline.md`; deploy/release stays behind the human gate).

**Phase 3 — The step loop.** For each numbered step, in order. `workflow.json`
is the **canonical step status**: mark the step `in_progress` when it starts,
`awaiting_approval` when you stop at its gate (built, UAT reported), and
`done` only when the human clears the gate — `plan.md` stays the contract and
never carries progress markers.
1. Write the step's `stepN_name/design.md` (traces to the Required Output).
2. Build the slice — solo, or via `agentic-step-execution` when independent
   slices fan out. Implement test-first (`superpowers:test-driven-development`).
   Recommend the model for the work (see **Model policy**); the user runs `/model`.
3. Hold the bar (`craftsmanship-bar`): clean code **and** docs updated in the
   same change — including `plan.md`, the `design.md`, `decisions.json`,
   `workflow.json`.
4. Run the step's **UAT** against its acceptance criteria (a subagent may run
   and report; see `agentic-step-execution`).
5. Commit (`secret-safe-commits`: scan the staged diff — mandatory, not a glance).
6. **STOP at the approval gate** (below).

If context runs high mid-step (the `context-meter` shows 🟡/🔴), use
`session-handoff` to write a `HANDOFF.md` and continue in a fresh session — the
gate travels with you: a new session does not clear a step just because the
handoff said "next".

**Phase 4 — SIT & close.** Run the whole general conductor end-to-end and check
the full `# Required Output` (System Integration Test). Regenerate the browser
docs. Then `superpowers:finishing-a-development-branch`.

## Model policy
Since this methodology hands mechanical edits to a cheaper model, be deliberate
about which one: **Opus plans, designs, and reviews; Sonnet executes mechanical
work.** You cannot switch your own model — recommend the best one for each step
and its *why*, and the user runs `/model`.
- **The only downshift is Sonnet.** **Never recommend Haiku for execution** — too
  risky for building steps. **Never recommend or suggest Fable**, ever. If the
  user proposes Haiku or Fable, advise against it and steer back to Opus or Sonnet.

## The approval gate (non-negotiable)
After each step's UAT, **stop and report to the human** — what was built, UAT
result per criterion, what the next step is. **Only the human advances to the
next step.** A subagent, a passing UAT, or your own confidence never clears the
gate. This is the single invariant every other skill defers to.

Stopping at the gate sets the step to `awaiting_approval` in `workflow.json`
(inside the step's own commit — item 5). When the human clears the gate, flip
it to `done` (and the next step to `in_progress` as it starts) in a small
status commit at the top of the next step's work — the build commits
themselves stay one per gated step.

## Red flags — STOP
- Re-scaffolding (Phase 0–2) a project whose `plan.md` / conductor already exist — re-enter via Phase R instead
- Starting to code before `plan.md` has a testable Goal + Required Output
- Building step N+1 because step N's UAT passed — the *human* clears the gate, not the test
- One big commit for "the whole feature" instead of a commit per gated step
- Reaching Phase 4 with `plan.md` / `design.md` / `decisions.json` describing behavior the code no longer has
- Recommending Haiku or Fable for a step — the only execution downshift is Sonnet
