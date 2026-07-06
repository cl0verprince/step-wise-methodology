---
name: authoring-the-master-plan
description: Use when writing or reviewing a project's master plan.md — to open it with a testable Goal and a concrete Required Output (deliverable, format, acceptance criteria, out-of-scope) before the ordered steps, so "done" is objectively checkable.
---

# Authoring the Master Plan

## Overview
The master `plan.md` is a **contract, not an essay**. It opens with two sections — in this order — before anything else:

1. `# Goal` — the single, specific, **testable** outcome the project exists to achieve, in 1–2 sentences. If you can't state it that briefly, the brainstorming isn't finished.
2. `# Required Output` — what "done" looks like, concrete enough for a test to check.

Only then come the ordered `# Steps`. **Do not write the steps until the Goal and Required Output are nailed down.** Left to default, plans sprawl into overview / architecture / phases and never state a checkable contract — this skill fixes that.

## `# Required Output` must contain
- **Deliverable** — the artifact(s) produced (app, CLI, API, report, model…).
- **Format / interface** — how it is consumed (command, endpoint, file, UI…).
- **Acceptance criteria** — each one **objectively checkable** (a test or command could verify it), not "works well".
- **Out of scope** — what this explicitly does NOT deliver.

Every step's UAT and the final SIT trace back to these. If a step can't be traced to the Required Output, the step or the Required Output is wrong — resolve it before coding.

## Template
Start from `templates/plan.md`. Keep it lean: the contract plus the ordered step list, nothing padded. Each step links to its own `stepN_name/design.md`.
