---
name: pipeline-architect
description: Use when setting up CI/CD or a build/test/release pipeline for a step-wise project — to derive the RIGHT pipeline from the project's plan.md (library, service, frontend, or data-science) instead of a one-size template, always run the methodology's gates in CI, and keep releases/deploys behind the human approval gate.
---

# Pipeline Architect

## Overview
The right pipeline for a project depends on **what it ships** — a library, a
service, a UI, or a data/model artifact each want a different delivery path. So
this skill does not hand you one YAML. It **reads the project's declared
contract and derives the fitting pipeline**, then automates the gates you
already enforce by hand.

The signal is already structured: `plan.md`'s `# Required Output` states the
**Deliverable** and **Format / interface**. Classify from that — it's a contract
you wrote, not a guess.

**Recommend, don't impose.** The classification and pipeline are *proposed with
their rationale* (tie each choice back to the Required Output); the human
approves before anything is committed. Dispatch the read-only role in
`templates/pipeline-architect.md` when you want a subagent to produce the
proposal.

## 1. Classify the deliverable → archetype
| Required Output signal | Pipeline archetype |
|---|---|
| CLI / library / plugin / package | **Release-on-tag** — build, publish to the registry, cut a GitHub Release on `vX.Y.Z` |
| Backend / API / service | **Gated deploy** — build image → deploy staging → **human-approved** production |
| Frontend / UI | **Preview + gated prod** — build, preview-deploy per PR, gated production |
| Report / model / dataset (data science) | **Reproduce + track + validate** — run the conductor, log metrics, **threshold gate** (fail if a key metric regresses); *publish* the artifact, not deploy |
| Both / full-stack | **Combined** — the service and frontend archetypes together |

If the Required Output doesn't clearly map to one, the contract is too vague —
fix `plan.md` first (see `authoring-the-master-plan`).

## 2. Always run the universal CI baseline
Every archetype includes the same automated backstop for the methodology's
gates, on every push/PR:
- **Secret scan** — `gitleaks` (backstop for `secret-safe-commits`; catches what
  a cheap committer missed).
- **Reproduce** — run the general **conductor** (`deterministic-conductors`):
  same inputs + config → same output, enforced in CI, not just locally.
- **UAT / SIT** — run `tests/uat` and `tests/sit` so "every step is green" is a
  merge requirement.

Start any pipeline from `templates/ci.yml` — a ready GitHub Actions workflow
carrying this baseline plus the release-on-tag archetype. Tailor the delivery
half to the archetype from the rubric; keep the baseline.

## 3. The human approval gate holds
Automation **prepares**; the human **releases and deploys**.
- **No auto-deploy to production.** Production is a manual-approval environment
  (GitHub Environment protection) or an opt-in, clearly-labelled step — never
  fired automatically on merge.
- **Release is triggered by a human action** — pushing the `vX.Y.Z` tag — which
  matches the project's version-tag flow. CI reacts to the tag; it doesn't mint
  it.

## Red flags — STOP
- Dropping in a generic CI/CD YAML without reading `plan.md` — wrong pipeline for the deliverable (e.g. a "deploy" job for a data-science report)
- Auto-deploying to production on merge — that bypasses the approval gate the whole methodology is built on
- CI that skips the secret scan or doesn't run the conductor/UAT — then the gates aren't actually enforced, only decorated
- A "CD" deploy job for a library, or a "release-to-PyPI" job for a service that has nothing to publish — archetype mismatch
