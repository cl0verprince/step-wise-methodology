<!-- Copy to the PROJECT's root as pipeline.md. This file is the pipeline's
     memory: which archetype and maturity level the project is at, which gates
     are active, and every ratchet decision. pipeline-architect reads it FIRST
     on every re-invocation. ci.yml holds the enforced numbers; this file holds
     the level and the why. Update both in the same commit when ratcheting. -->

# Pipeline

- **Archetype:** <release-on-tag | gated deploy | preview + gated prod | reproduce + track + validate | combined>
- **Maturity level:** L<0-3> — <Bootstrapped | Baseline | Hygiene | Strict>  (the ladder: pipeline-architect SKILL.md)
- **Coverage floor:** <n>% (<advisory | blocking>) — enforced number lives in `.github/workflows/ci.yml`

## Active gates

| Gate | Status | Since |
|---|---|---|
| secret scan | blocking | L0 |
| unit tests | blocking | L0 |
| conductor reproduce | blocking | L1 |
| UAT / SIT | blocking | L1 |
| lint + format | <not yet | blocking> | L2 |
| coverage | <not yet | advisory | blocking> | L2/L3 |
| type check | <not yet | blocking> | L3 |

## Ratchet log
<!-- One line per level/floor change. Levels only go up; a lowering is a human
     decision and must be logged here with its reason. -->
- <YYYY-MM-DD> — created at L<n> (<archetype>). Approved by user.
