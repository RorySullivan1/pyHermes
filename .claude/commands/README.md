# commands/

**Single-shot prompt templates.** Saved prompts you'd otherwise retype —
stateless, instant, one invocation. Invoked as `/<name>`.

## Format

- One markdown file per command: `<name>.md`. The filename is the command name.
- The body is the prompt. Use `$ARGUMENTS` (or `$1`, `$2`, …) for parameters and
  `!`-prefixed lines for shell context if your harness supports it.
- Keep each command focused on one repeatable action.

## Typical uses

- `/review-pr` — review an open PR against project conventions.
- `/new-thing` — scaffold a new component/spec with standard fields.
- `/status` — pull and format a standup/status digest.

## Status

**Defined:**
- `/reindex` — regenerate `.claude/CATALOG.md` (runs `.claude/hooks/catalog.py`).
- `/version-set`, `/version-ship` — the version-labeling flow (see `.meta/version`).
- `/prose-review` — audit comments/docstrings against the prose scope discipline via the
  `prose-auditor` agent (findings only; `--apply` to also fix, route-then-trim).
- `/epic` — plan a body of work (no code) and file it on the remote as an epic with ordered,
  templated sub-issues; offers the `epic-autoclose` Actions workflow. Standard: `github-issues`.
- `/issue` — file one templated issue (task/bug/feature), optionally `--parent #N` under an
  epic, with a ready-to-paste `Closes #n` line.

Drop a `<name>.md` here to add another.
