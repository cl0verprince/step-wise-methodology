# Step-Wise Methodology

A Claude Code **plugin** for building any new project or major feature the same disciplined way every time: plan first, work in visible **numbered steps**, acceptance-test each step, protect secrets, keep the code readable and in sync with its docs — and **stop for your approval before moving on**.

Language-agnostic. Efficient by design (skills load only when their concern is active).

## Install

```
/plugin marketplace add cl0verprince/step-wise-methodology
/plugin install step-wise-methodology@stepwise
```

> **Recommended companion:** install the [superpowers](https://github.com/obra/superpowers) plugin too. This plugin *composes* its `brainstorming`, `writing-plans`, `test-driven-development`, `dispatching-parallel-agents`, and `subagent-driven-development` skills rather than re-implementing them.

## What's inside

| Skill | Use it when |
|---|---|
| `stepwise-delivery` *(orchestrator)* | starting a new project or major feature — drives the whole phased, gated workflow |
| `adopting-existing-projects` | bringing the methodology to a codebase that wasn't built with it — survey first, then the human picks ride / adopt / rebuild |
| `authoring-the-master-plan` | writing the master `plan.md` (Goal / Required Output / ordered steps) |
| `deterministic-conductors` | building the reproducible run-the-pipeline entry point (any language) |
| `browser-readable-project-docs` | keeping an offline, double-clickable decision log + flow diagram |
| `secret-safe-commits` | committing — never leak `.env`, keys, or credentials |
| `craftsmanship-bar` | holding code to clean, reviewable, no-slop, matches-the-docs standards |
| `agentic-step-execution` | using subagents / parallel workflows to build a step |
| `pipeline-architect` | connecting the repo to GitHub (init → push → branch protection) and deriving the right CI gates from `plan.md` + the pipeline maturity ladder, in approval-gated stages |
| `context-meter` | showing context usage, time-to-red, turns, duration, and cost as a traffic light in the Claude Code status line |
| `session-handoff` | context is running high — write a tight `HANDOFF.md` to resume in a fresh session |

## Project state model

A step-wise project's durable state is four small root files, each owning exactly one concern:

| File | Owns | Maintained via |
|---|---|---|
| `plan.md` | the **contract** — goal, required output, ordered steps (never status) | `authoring-the-master-plan` |
| `workflow.json` | the **canonical step status** — `done` / `in_progress` / `awaiting_approval` / `pending` | every skill that starts, finishes, or adds a step |
| `pipeline.md` | the **delivery posture** — archetype, CI maturity level, active gates | `pipeline-architect` |
| `HANDOFF.md` | the **volatile last-session memory**, pointing at the rest | `session-handoff` |

(`decisions.json` remains the why-log, rendered to HTML by `browser-readable-project-docs`.)

**The re-entry rule:** every skill detects before it creates. If its artifact already exists it reconciles and extends — it never re-scaffolds. Invoked on an existing project, `stepwise-delivery` reads these four files first, reports where the project stands, and resumes at the right phase.

The **`context-meter`** ships a bundled, stdlib-only status-line script
(`skills/context-meter/scripts/context_meter.py`): a 🟢/🟡/🔴 traffic light,
live token count and window size, and a full dashboard line — model, git
branch, current `workflow.json` step, turn count and session duration, cost
and burn rate, and a time-to-red ETA against a red line that adapts to the
compaction point actually observed on this machine — rendered at the bottom
of the Claude Code pane inside PyCharm / VS Code. Setup is agent-led: ask
Claude to enable it and it wires the `settings.json` `statusLine` block for
you; see its `SKILL.md` for details.

## License

MIT
