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
| `authoring-the-master-plan` | writing the master `plan.md` (Goal / Required Output / ordered steps) |
| `deterministic-conductors` | building the reproducible run-the-pipeline entry point (any language) |
| `browser-readable-project-docs` | keeping an offline, double-clickable decision log + flow diagram |
| `secret-safe-commits` | committing — never leak `.env`, keys, or credentials |
| `craftsmanship-bar` | holding code to clean, reviewable, no-slop, matches-the-docs standards |
| `agentic-step-execution` | using subagents / parallel workflows to build a step |

Plus a bundled **`context-meter`** status-line script (🟢/🟡/🔴 context-usage traffic light).

## License

MIT
