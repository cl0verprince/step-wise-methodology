---
name: craftsmanship-bar
description: Use when writing or changing code that has a design doc or plan describing it — to keep code clean, readable, reviewable and slop-free, and to keep the docs in sync with the code before calling any change done.
---

# Craftsmanship Bar

## Overview
Code here is written to be **read and reviewed by a human**, and it must stay **consistent with the docs that describe it**. Neither is automatic. A change is not finished when the code works — it is finished when the code is clean *and* the doc still tells the truth.

Evidence for the sync rule: a strong model updates the design doc alongside the code, but a fast/cheap execution model changes the code and leaves the doc stale — silently making the spec lie. Since this methodology hands mechanical edits to cheaper models, syncing the docs is a **required step**, not a nicety.

## A. Keep code and docs in sync (required)
When you change behavior, **in the same change** update every doc that describes it — the step's `design.md`, the master `plan.md`, and any README/`.md` stating the old behavior.
- Changed a constant, signature, flag, or contract? Grep the docs for the old value and fix each hit.
- **Definition of done:** code and its `.md` agree. If they disagree, the step is not done — resolve it before the approval gate.

## B. Clean, reviewable, slop-free
- **Clean:** clear names, small single-purpose functions, no dead code, no copy-paste duplication, consistent style.
- **Comment WHY, not WHAT.** Docstrings state purpose, inputs, outputs. A competent human should follow the logic without reverse-engineering it.
- **No slop:** no filler comments (`// increment i by 1`), no boilerplate the task doesn't need, no defensive scaffolding for cases that cannot occur, no prose restating the code.

## Red flags — STOP
- Changed code, didn't touch the `design.md` / `plan.md` that documents it → the doc now lies
- "The doc is close enough" → close enough is drift
- Comments narrate *what* the code does instead of *why*
- Guard clauses / try-catch for inputs that are impossible in this context
