---
name: session-handoff
description: Use when the context window is running high (the context-meter shows 🟡/🔴) or the user wants to continue in a fresh session — "write a handoff", "summarize for a new session", "context is getting full, wrap up". Produces a tight HANDOFF.md that lets a new session resume in minutes without re-reading the whole transcript.
---

# Session Handoff

## Overview
A long session's most valuable state is the **volatile working memory** — the
last few turns of decisions and the next concrete move — which lives only in the
transcript, not on disk. When context runs high or you want a clean new session,
this captures that into a one-screen `HANDOFF.md` so a fresh session resumes fast
and correctly.

**On-demand, and honest about it.** An agent cannot read its own token count —
only the human sees the `context-meter` traffic light. So this is **user-invoked**:
the meter is your cue, this skill is the action. It never guesses the context
level or nags.

## What to write
Create `HANDOFF.md` at the project root from `templates/HANDOFF.md`:
- **Goal** — one line, **by reference** to `plan.md` (restate in full only if there
  is no plan.md).
- **Current step / status** — by reference to `workflow.json` (the canonical
  status file); add only what it can't say, the mid-step nuance ("step 3
  in_progress, UAT written but failing on the date parser").
- **Last 4 turns** — *the point of this file.* What changed in the latest
  iterations and the decisions made **with their why**. This is what a fresh
  session most lacks.
- **Next action** — the single concrete next thing to do.
- **Open threads / blockers** — unresolved questions.
- **Pointers** — `plan.md`, the current `stepN/design.md`, `decisions.json`, and
  the key files touched.

## Discipline
- **Reference, don't duplicate.** The Goal lives in `plan.md`, decisions in
  `decisions.json`. The handoff carries the *ephemeral* — last-4-turns state and
  next action — not a second copy of the durable docs.
- **Tighter than the transcript.** It must fit one screen. A handoff longer than
  the conversation it replaces has failed at its one job.
- **Durable record first.** In a stepwise project, bring `decisions.json` **and
  `workflow.json`** current **before** writing the handoff — the handoff is the
  volatile companion, not a replacement for the permanent record (see
  `browser-readable-project-docs`).
- **One HANDOFF.md.** A previous handoff exists? Overwrite it — it described a
  session that is now over, and its history lives in git. Two handoffs means
  the next session guesses which one is true.
- **Resume rule.** A fresh session's first act is: read `HANDOFF.md` → the linked
  docs → resume at *Next action*. **The human approval gate travels with you** —
  a new session does not clear a step's gate just because the handoff said "next"
  (see `stepwise-delivery`).

## Red flags — STOP
- Restating the whole `plan.md` Goal / all of `decisions.json` into HANDOFF.md instead of linking — that's duplication that will drift
- A handoff as long as the transcript — no time saved
- Writing the handoff while `decisions.json` is stale — the permanent record loses the decision, the volatile one keeps it
- A resumed session advancing past a step because HANDOFF.md said "next" — the human still clears the gate
