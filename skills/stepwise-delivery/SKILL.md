---
name: stepwise-delivery
description: Use when starting any new project or building a major new feature, component, or subsystem from scratch — greenfield "let's build X" work worth doing in deliberate, planned, acceptance-tested, approval-gated numbered steps. Drives the whole phased workflow and calls the other step-wise skills in order.
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
`workflow.json`).

**Phase 3 — The step loop.** For each numbered step, in order:
1. Write the step's `stepN_name/design.md` (traces to the Required Output).
2. Build the slice — solo, or via `agentic-step-execution` when independent
   slices fan out. Implement test-first (`superpowers:test-driven-development`).
3. Hold the bar (`craftsmanship-bar`): clean code **and** docs updated in the
   same change — including `plan.md`, the `design.md`, `decisions.json`,
   `workflow.json`.
4. Run the step's **UAT** against its acceptance criteria (a subagent may run
   and report; see `agentic-step-execution`).
5. Commit (`secret-safe-commits`: scan the staged diff — mandatory, not a glance).
6. **STOP at the approval gate** (below).

**Phase 4 — SIT & close.** Run the whole general conductor end-to-end and check
the full `# Required Output` (System Integration Test). Regenerate the browser
docs. Then `superpowers:finishing-a-development-branch`.

## The approval gate (non-negotiable)
After each step's UAT, **stop and report to the human** — what was built, UAT
result per criterion, what the next step is. **Only the human advances to the
next step.** A subagent, a passing UAT, or your own confidence never clears the
gate. This is the single invariant every other skill defers to.

## Red flags — STOP
- Starting to code before `plan.md` has a testable Goal + Required Output
- Building step N+1 because step N's UAT passed — the *human* clears the gate, not the test
- One big commit for "the whole feature" instead of a commit per gated step
- Reaching Phase 4 with `plan.md` / `design.md` / `decisions.json` describing behavior the code no longer has
