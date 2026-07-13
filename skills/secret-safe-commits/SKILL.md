---
name: secret-safe-commits
description: Use before any git commit or push, when staging files, setting up .gitignore/.env, or reviewing a diff about to enter history — anywhere secrets (API keys, tokens, passwords, private keys, connection strings) could leak into a repo.
---

# Secret-Safe Commits

## Overview
Two layers keep credentials out of git history: **prevent** them from ever staging, and **scan** every commit as a backstop. The scan is **mandatory, not a judgement call** — the model creating the commit may be a fast/cheap one that will not notice a non-obvious secret.

Evidence this is real: strong models refuse both blatant and subtle secrets, but a cheaper execution model committed a hardcoded production password straight into history without flagging it. Since this methodology hands mechanical commits to cheaper models, the gate cannot depend on the committer "noticing."

**Glancing at the diff is not a scan. Skipping the scan because a change "looks like just config" is how the leak happens.**

## Layer 1 — Prevent (at project setup / step 0)
- Add `.gitignore` **before the first commit**, from `templates/gitignore`: covers `.env`, `*.key`, `*.pem`, `id_rsa*`, `*.p12`, `service-account*.json`, credential files.
- A `.gitignore` **already exists? Merge, don't replace** — append the template's secret patterns that are missing; never delete entries that are already there.
- Secrets live only in `.env` (git-ignored). Commit `.env.example` (key names, no values) from `templates/env.example`.
- **Keep `.env.example` current:** every time a new key lands in `.env`, add its name (no value) to `.env.example` in the same change — a stale example file is how the next contributor hardcodes the key instead.

## Layer 2 — Scan the staged diff before EVERY commit
```
git diff --cached
```
STOP and remediate if any appears — **including inside source files**, not only `.env`:
- Private keys: `-----BEGIN ... PRIVATE KEY-----`, `.pem` / `.p12` / `id_rsa` contents
- Provider keys: `sk_live_`, `AKIA…`, `ghp_…`, `xox[baprs]-…`, Google `AIza…`
- **Hardcoded credentials in code:** `password = "…"`, connection strings like `postgres://user:pass@host`
- High-entropy literals assigned to a `token` / `secret` / `key` / `password` field
- Thorough option when available: `gitleaks protect --staged` (or `trufflehog`).

## Already tracked or already committed
`.gitignore` does **not** remove a secret that is already in the repo.
- **Staged only:** `git rm --cached <file>` (keeps it on disk), then ignore it.
- **Already in history:** it stays recoverable forever. **Rotate the credential — assume it is burned.** Scrubbing history (`git filter-repo`) helps only if it never left this machine, and you rotate anyway.

## Red flags — STOP
- Committing with a fast/cheap model and skipping the scan "because it's just config"
- A value that "looks like an ID" assigned to `secret` / `token` / `password`
- Thinking a new commit that deletes a secret fixed it — history still holds it
