---
name: pipeline-architect
description: Use when connecting a project to GitHub ("connect this to GitHub", git init, add remote, first push), setting up CI/CD or a build/test/release pipeline, enabling branch protection, adding CI gates (unit tests, lint, type check, coverage), or raising a project's pipeline maturity ("make coverage blocking", "add CI"). Derives the right pipeline from plan.md instead of a one-size template; releases/deploys stay behind the human approval gate.
---

# Pipeline Architect

## Overview
The right pipeline for a project depends on **what it ships** — a library, a
service, a UI, or a data/model artifact each want a different delivery path. So
this skill does not hand you one YAML. It **reads the project's declared
contract and derives the fitting pipeline**, connects the repo to GitHub if it
isn't yet, and automates the gates you already enforce by hand.

Two ideas hold everything together:
- The signal is already structured: `plan.md`'s `# Required Output` states the
  **Deliverable** and **Format / interface**. Classify from that — it's a
  contract you wrote, not a guess.
- The gate set is a **ladder you climb, not a fixed list**. A day-old prototype
  and a mature library deserve different CI; the level lives in the project's
  `pipeline.md` and only ratchets up with the human's approval.

**Recommend, don't impose.** Every stage below is *proposed with its rationale*
(tie each choice back to the Required Output); the human approves before
anything is committed or pushed.

## The staged flow (run in order — approval gate between each stage)
Present the stage, do it, report what happened, then **ask the user before
advancing** (`AskUserQuestion`). Only the human advances — same gate as
`stepwise-delivery`. Never run two stages in one breath.

| Stage | Do | Then |
|---|---|---|
| **A — Bootstrap** | Detect repo state; init/connect/push only what's missing | approval |
| **B — Classify & propose** | Archetype + gate set + maturity level (dispatch the read-only role in `templates/pipeline-architect.md`) | approval |
| **C — Commit the pipeline** | Tailor `templates/ci.yml`, write `pipeline.md` from `templates/pipeline.md`, commit (scan first — `secret-safe-commits`), push | approval |
| **D — Branch protection** | Require PR + green `gates` check on `main` | approval |
| **E — First green run** | Watch the run, fix red with the user, mark the level active in `pipeline.md` | final report |

Re-invoked on a project that already has a pipeline? **Read `pipeline.md`
first** — skip the stages that are done and propose the next rung of the ladder
if the project has outgrown its level.

## Stage A — Bootstrap
Check each row; do **only** what's missing. Everything present → say so and go
to Stage B.

| Check | Command | If missing |
|---|---|---|
| git repo | `git rev-parse --git-dir` | `git init -b main` |
| secret hygiene | `.gitignore` + `.env.example` exist | → `secret-safe-commits` — **before the first commit** |
| first commit | `git log --oneline -1` | commit the scaffold (scan the staged diff first) |
| gh authenticated | `gh auth status` | STOP — the user runs `gh auth login` themselves; never handle or echo tokens |
| remote | `git remote get-url origin` | confirm the repo **name** and **public/private** with the user (private on a free plan can't have branch protection — say so now, not in Stage D), then `gh repo create <name> --private\|--public --source . --push` |
| branch protection | `gh api repos/{owner}/{repo}/branches/main/protection` | defer to Stage D (it needs the check name from Stage C) |

## Stage B — Classify the deliverable → archetype
| Required Output signal | Pipeline archetype |
|---|---|
| CLI / library / plugin / package | **Release-on-tag** — build, publish to the registry, cut a GitHub Release on `vX.Y.Z` |
| Backend / API / service | **Gated deploy** — build image → deploy staging → **human-approved** production |
| Frontend / UI | **Preview + gated prod** — build, preview-deploy per PR, gated production |
| Report / model / dataset (data science) | **Reproduce + track + validate** — run the conductor, log metrics, **threshold gate** (fail if a key metric regresses); *publish* the artifact, not deploy |
| Both / full-stack | **Combined** — the service and frontend archetypes together |

If the Required Output doesn't clearly map to one, the contract is too vague —
fix `plan.md` first (see `authoring-the-master-plan`).

## The gate catalog
Each CI gate is the automated backstop for a manual discipline the methodology
already enforces:

| Gate | Backstops | Runs on |
|---|---|---|
| Secret scan (`gitleaks`) | `secret-safe-commits` | every push/PR |
| Unit tests (fast suite, `tests/unit/`) | TDD red/green (`superpowers:test-driven-development`) | every push/PR |
| Conductor reproduce | `deterministic-conductors` — same inputs + config → same output | every push/PR |
| UAT / SIT (`tests/uat`, `tests/sit`) | the step approval gates | every push/PR |
| Lint + format check | `craftsmanship-bar` | every push/PR |
| Coverage (advisory → blocking floor) | test discipline over time | every push/PR |
| Type check | interface contracts | every push/PR |

## The maturity ladder
Which gates block is a function of the project's **level**, recorded in
`pipeline.md` (start from `templates/pipeline.md`):

| Level | Name | Blocking gates | Advisory |
|---|---|---|---|
| **L0** | Bootstrapped | secret scan, unit tests | — |
| **L1** | Baseline | + conductor reproduce, UAT/SIT | — |
| **L2** | Hygiene | + lint, format check | coverage reported (non-blocking) |
| **L3** | Strict | + type check, coverage floor (`--cov-fail-under`) | — |

Tune the ladder to the project's nature — the levels are the default, the
rubric bends them:

| Project signal | Adjustment |
|---|---|
| Typed language (TypeScript, Go, Rust) | type check from L1 — it's free (`tsc --noEmit`, the compiler) |
| Python without annotations / plain JS | defer type check to L3, once annotations exist |
| Data-science deliverable | conductor + metric-threshold gate are primary; coverage stays advisory longer |
| Library / CLI / plugin | coverage blocking earlier, type check earlier — public surface |
| Frontend | lint + format from L1 (prettier/eslint); coverage advisory |
| Spike / prototype | hold at L0–L1 deliberately; note the intent in `pipeline.md` |

**Ratchet rules:**
- New projects start at **L1** — L0 exists only for the bootstrap window; a
  project driven by `stepwise-delivery` reaches L1 by its first real step.
  Propose L2 once the step loop has produced a few green steps.
- Levels are **named presets, not straitjackets** — the rubric moves individual
  gates between levels, and a single gate can ratchet on its own (e.g. a
  blocking coverage floor at L2 for untyped Python). `pipeline.md`'s Active
  gates table is the authority on what blocks; the level names the posture.
- Levels only go **up**. Lowering a level or the coverage floor is a human
  decision, logged in `pipeline.md`'s Ratchet log with its reason.
- The coverage floor only rises. Set the initial floor **~10 points below
  actual coverage**, and raise it whenever actual clears the floor by ~10
  points again. `ci.yml` holds the enforced number; `pipeline.md` echoes it
  with the why; a ratchet updates both in one commit.
- Every re-invocation of this skill is a chance to propose the next rung.

## Stage C — Commit the pipeline
Commit the workflow the human approved in Stage B — the subagent's draft is
the source of truth; change only what the user asked to change. It starts from
`templates/ci.yml`: gate steps are marked `[L0]`–`[L3]` with L2/L3 shipped
commented-out; uncomment down to the agreed level. Then write `pipeline.md`
(from `templates/pipeline.md`), commit (staged-diff scan first) and push.

**The delivery half, per archetype** (the `gates` job is always kept):
- **Release-on-tag** — keep the template's `release` job as-is.
- **Gated deploy** — swap `release` for build → deploy-staging → deploy-prod,
  with prod bound to a protected GitHub Environment (manual approval).
- **Preview + gated prod** — add a per-PR preview-deploy job; prod as above.
- **Reproduce + track + validate** — swap `release` for a `publish` job that
  attaches the artifact + metrics to a GitHub Release (`gh release create`
  + `gh release upload`) on the human's tag. Implement the **metric threshold
  as an assertion in `tests/sit`** — the gate is then just a test the `gates`
  job already runs, not bespoke YAML.

## Stage D — Branch protection
Make the automated gate mandatory: require a PR and a green `gates` check to
merge into `main`:

```
gh api -X PUT repos/{owner}/{repo}/branches/main/protection \
  -f 'required_status_checks[strict]=true' -f 'required_status_checks[contexts][]=gates' \
  -f 'enforce_admins=false' -f 'required_pull_request_reviews[required_approving_review_count]=0' \
  -F 'restrictions=null'
```

Two known snags — tell the user, don't silently work around:
- The `gates` context can be required **before it has ever run** (the API takes
  the name); the GitHub UI just won't list it yet.
- **Private repo on a free plan → HTTP 403** (protection is a paid feature
  there). Offer: make the repo public, or record "protection unavailable —
  enforced by discipline" in `pipeline.md` and move on.

## Stage E — First green run
Push, then watch: `gh run watch` (or `gh run list --limit 1`). Red? Fix it
*with* the user — a red first run usually means a path or install step needs
tailoring, not that a gate should be deleted. Green? Mark the level active in
`pipeline.md` and give the final report: what's connected, what blocks, what
the next rung would add.

## The human approval gate holds
Automation **prepares**; the human **releases and deploys**.
- **No auto-deploy to production.** Production is a manual-approval environment
  (GitHub Environment protection) or an opt-in, clearly-labelled step — never
  fired automatically on merge.
- **Release is triggered by a human action** — pushing the `vX.Y.Z` tag. CI
  reacts to the tag; it doesn't mint it.
- Branch protection (Stage D) is that same gate, automated: nothing merges
  without the gates going green.
- And this skill's own flow is gated: every stage stops for approval.

## Red flags — STOP
- Dropping in a generic CI/CD YAML without reading `plan.md` — wrong pipeline for the deliverable (e.g. a "deploy" job for a data-science report)
- Auto-deploying to production on merge — that bypasses the approval gate the whole methodology is built on
- CI that skips the secret scan or doesn't run the conductor/UAT — then the gates aren't actually enforced, only decorated
- A "CD" deploy job for a library, or a "release-to-PyPI" job for a service that has nothing to publish — archetype mismatch
- Creating a GitHub repo or pushing without asking public/private and getting approval
- Running `gh repo create` when `git remote -v` already shows an origin — detect, don't duplicate
- Pasting or echoing a token to authenticate `gh` — the user runs `gh auth login` themselves
- Jumping the ladder (proposing L3 for a day-old project) — or silently lowering a level or the coverage floor
- Running all five stages in one breath without the per-stage approval
