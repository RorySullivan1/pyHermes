# ship-version

Label a unit of work as a **version** with its goals, then name and ship the PR from those
goals. The version's intent (in `.meta/version`) becomes the branch name, the commit, and the
PR title/body — so what you set out to do is exactly what the PR says you did.

**Inputs:** a version label (semver, e.g. `v0.4.0`) and its goals/objectives; the work itself.
**Output:** a pushed branch and an open PR whose name and body derive from the version's goals,
with the PR URL recorded back into `.meta/version`.

## Steps

1. **Define the version.** Run **`/version-set`** to write/update `.meta/version` at the project
   root — the label, `status: in-progress`, the start date, a suggested
   `branch: claude/<version>-<slug>`, and the **Goals** / **Objectives**. Settle this *before*
   the work so the goals are a contract, not a post-hoc summary. (If a version is already
   in-progress, extend its goals instead of starting a new one.)

2. **Do the work.** Implement against the goals. The `version_guard` hook stays quiet while you
   work; it only speaks up at push time if `.meta/version` is incomplete.

3. **Ship it.** Run **`/version-ship`**. It reads `.meta/version` and:
   - creates/uses the branch `claude/<version>-<slug>`,
   - commits with a conventional message (subject = `<version>: <theme>`, body = the goals +
     the standard trailers),
   - pushes (retry/backoff per the repo's git convention),
   - opens the PR via `mcp__github__create_pull_request` — **title** `<version>: <theme>`,
     **body** built from the Goals/Objectives,
   - writes the PR URL into `.meta/version` and leaves `status: in-progress`.

4. **On merge.** Set `.meta/version` `status: shipped` (and start the next version with
   `/version-set` when new work begins). Optionally record the shipped version in
   `.claude/memory/` so the trajectory is remembered.

## Control flow / stop conditions

- `.meta/version` missing or has no goals when shipping → **stop and run `/version-set` first**;
  never invent goals to fill a PR.
- PR open with a title/body that match the version's goals → **done**; report the version, the
  branch, and the PR URL.
- A genuine scope question (which goals are in this version, what the bump should be) is the
  caller's → ask, don't guess.

## Invokes
- Commands: `../commands/version-set.md`, `../commands/version-ship.md`.
- Hook: `../hooks/version_guard.py` (PreToolUse·Bash; advisory at push time).
- Tool: `mcp__github__create_pull_request` (PR creation).
