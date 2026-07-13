---
name: agentic-step-execution
description: Use when building a step with subagents or parallel workflows — to fan out independent slices, reuse agent roles consistently, keep reusable agent definitions and workflow scripts in standard loadable locations, and preserve the human approval gate.
---

# Agentic Step Execution

## Overview
A step can be built by subagents — several independent slices in parallel, a dedicated reviewer, a scripted workflow. This skill sets **where the agentic pieces live and who approves**, and defers the fan-out mechanics to superpowers.

**REQUIRED SUB-SKILLS:** use `superpowers:dispatching-parallel-agents` (fan-out mechanics) and `superpowers:subagent-driven-development` (agent-built tasks). Agents already recognize when slices are independent — this skill is about consistency and the gate, not re-teaching parallelism.

## Where reusable agentic pieces live
Agents readily invent ad-hoc, non-loadable locations for a role they will reuse (observed: `roles/uat-runner.md`, a bare `uat-runner.md` — never the loadable one). Standardize:
- **Reusable agent roles → `.claude/agents/<name>.md`** — native format (`name` / `description` / `tools` / `model` frontmatter + a system-prompt body). Version-controlled, human-reviewable, and actually loadable as a named subagent. Start from `templates/agent-definition.md`.
- **Reusable workflow scripts → `workflows/`.**
- **The save rule:** save an agent role when it will be used **more than once** (a recurring `uat-runner`, `step-implementer`, `reviewer`). A genuinely single-use dispatch stays **inline** — don't clutter the repo, and don't ask each time; the >1× rule decides.
- **The reuse rule:** before creating a role, check `.claude/agents/` — if it already exists, **load and dispatch it as-is**; edit it only when the step's contract actually changed. Never mint a `uat-runner-2`.

## Discipline
- **Fan out only independent slices.** Anything with a real dependency stays sequential.
- **Subagents report — the human approves.** A subagent may run a step's UAT and report pass/fail, but it never clears the approval gate or advances to the next step. That is the human's call (see `stepwise-delivery`).
- **Keep the conductor deterministic.** The agents' nondeterminism is in *building* the step; the built pipeline must still seed and pin so it reproduces (see `deterministic-conductors`).
