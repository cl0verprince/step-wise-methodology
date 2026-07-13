---
name: adopting-existing-projects
description: Use when applying the step-wise methodology to an existing codebase that was not built with it — a non-empty repo with no plan.md / workflow.json ("adopt this project", "bring structure to this codebase", "continue developing this legacy project", "apply the methodology here"). Also the target of stepwise-delivery's Phase R routing when no state files exist.
---

# Adopting Existing Projects

## Overview
A project that predates this methodology has its own shape — structure,
conventions, history, habits. Dropped in blind, an agent either refuses (no
`plan.md`) or re-scaffolds over living code. This skill does neither: it
**learns the project first, then lets the human choose how deep the
methodology goes**. Mapping beats imposing — the project's existing
structures are given methodology *roles*, not replaced.

## 1. Survey — learn to ride it (read-only, always first)
Before proposing anything, characterize the project. Touch nothing.

| Learn | Look at |
|---|---|
| What it ships (→ archetype) | README, package manifest, entry points, release artifacts |
| How it runs | Makefile / scripts / main / CLI — the existing "conductor", whatever it's called |
| Test reality | test dirs, coverage, CI config — or their absence |
| Conventions & principles | existing `.md`s, `CLAUDE.md`, lint configs, code style, naming |
| History rhythm | `git log` — cadence, contributors, tags/releases |
| Risk surface | secrets handling, `.gitignore` state (→ `secret-safe-commits` lens) |

**Report the survey to the human** — what the project is, how it runs, where
the risks are — before offering any choice. The survey findings are the
skill's whole authority; a mode proposed without one is a guess.

## 2. The mode gate — the human chooses the depth
Present the three modes with your recommendation *for this project* (healthy
and stable → Ride; about to be developed heavily → Adopt; genuinely being
re-engineered → Rebuild). `AskUserQuestion`; the human decides.

| Mode | What happens | Footprint |
|---|---|---|
| **Ride** | Learn it, don't change it | `CLAUDE.md` only |
| **Adopt** | Introduce the state model, mapped onto what exists | `plan.md`, `workflow.json`, `pipeline.md` (`HANDOFF.md` arrives with the first handoff) |
| **Rebuild** | Re-engineer step-wise from a fresh contract | a new project, old code as reference |

**Rebuild requires a second, explicit confirmation** — ask again, plainly:
"this restructures a working project — are you sure?" Only a yes to *that*
question opens Rebuild.

## 3. Ride — remain with the current structure
Distill the survey into the project's **`CLAUDE.md`** (create it, or append a
clearly-marked section — never overwrite existing content): what the project
is, how to run/test it, its conventions and principles, what not to touch.
Human approves the text. No files are moved, nothing is renamed.

New work in a ridden project still gets the discipline — approval before
merging, `secret-safe-commits` before commits, `craftsmanship-bar` on changes
— expressed entirely in the project's own structure.

## 4. Adopt — introduce the state model, mapped onto what exists
Create the four state files (see the README's Project state model), one at a
time, each human-approved:
- **`plan.md`** (`authoring-the-master-plan`) — the as-built contract. Ask how
  to represent pre-existing work: **forward-only baseline** (default: one
  `step0_baseline` marked `done` — a record that the past happened; its
  acceptance is *pinned by the characterization step*, which comes first
  among the new steps when tests are missing), **hybrid milestones** (coarse
  `done` steps from tags/releases), or **full retroactive reconstruction**
  from git history (real effort; offer it, don't push it).
- **`workflow.json`** (`browser-readable-project-docs`) — seeded from the
  chosen history representation.
- **Conductor role, not conductor file** (`deterministic-conductors`) — the
  existing `Makefile` / npm script / entry point *is* the conductor;
  document it as such. Add a new one only if nothing plays that role.
- **`pipeline.md`** (`pipeline-architect`) — its Stage A detection already
  handles "repo connected, CI exists"; classify the existing CI into the gate
  ladder and record the level **as found** (a lint-only CI is what it is).
  Proposing the next rung is `pipeline-architect`'s own job on its next
  invocation — record now, ratchet later.
- **`CLAUDE.md`** — the survey distillation from Ride mode applies here too:
  append a clearly-marked section, never overwrite.

**When the files exist, adoption is over:** hand control back to
`stepwise-delivery` — its Phase R now finds the state files and resumes
normally, and its never-re-scaffold rule protects the structures you mapped.

## 5. Rebuild — re-engineer (double-confirmed only)
Treat it as a new step-wise project: `superpowers:brainstorming` → a fresh
contract (`authoring-the-master-plan`) → `stepwise-delivery` **Phases 2–4**
on the rebuild branch (the survey already served as Phase 0's exploration;
Phase R doesn't re-fire — you are already inside the adoption decision).
The existing code is a **reference implementation**, mined not deleted:
work on a branch, keep the old system runnable until the SIT passes.

## The safety-net rule (any mode)
A project with **no tests** gets a characterization safety net as the first
real step — golden-master tests pinning current behavior — before any
behavior-touching change. You cannot protect what you haven't pinned.

## Red flags — STOP
- Proposing a mode, or touching any file, before the survey is done and reported
- Adding `conductor.py` next to a working `Makefile` — that's imposing, not mapping
- Entering Rebuild off a single yes — it takes the second, explicit confirmation
- Overwriting an existing `CLAUDE.md` instead of appending a marked section
- Retroactive steps that git history doesn't actually evidence — reconstruction is archaeology, not fiction
- Changing behavior in a test-less project before the characterization net exists
- Treating Ride mode as "no discipline" — the gates still apply to new work
