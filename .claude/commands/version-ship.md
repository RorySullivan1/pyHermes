---
description: Name and ship the PR from .meta/version — branch, commit, push, and open the PR with a title/body derived from the version's goals.
argument-hint: [— optional theme/title override]
---

You are shipping the current version: turning `.meta/version` into a named, pushed PR.

## 1. Read the version

Read `${CLAUDE_PROJECT_DIR}/.meta/version`. If it's missing, or has no `version:` or no
**Goals**, **stop** and tell the user to run `/version-set` first — do not invent goals to
fill a PR. Extract: the `version:` label, the `branch:`, the Goals, and the Objectives.

## 2. Derive the names (from the goals, not the diff)

- **Theme** — a short phrase capturing the goals (use `$ARGUMENTS` as an override if given).
- **Branch** — the file's `branch:`, else `claude/<version>-<slug>`.
- **PR title** — `<version>: <theme>` (e.g. `v0.4.0: harden the auth flow`).
- **PR body** — built from the Goals (as the summary) and Objectives (as the acceptance /
  checklist), plus a one-line pointer to `.meta/version`.

## 3. Branch, commit, push

- Create or switch to the branch. Never commit straight to `main`.
- Stage the work and commit with a conventional message: subject `<version>: <theme>`, body =
  the goals, then the repo's standard trailers (`Co-Authored-By:` and `Claude-Session:` per
  `CLAUDE.md`).
- `git push -u origin <branch>` with the retry/backoff convention (2s/4s/8s/16s on network
  failure).

## 4. Open the PR

Call `mcp__github__create_pull_request` with the derived **title** and **body**, base `main`,
head `<branch>`. (This command is the explicit ask, so opening the PR here is intended.)

## 5. Record the result

Write the returned PR URL into `.meta/version`'s `pr:` field. Leave `status: in-progress`
until the PR merges (flip to `shipped` then). Report the version, branch, and PR URL.
