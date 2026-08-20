---
description: Regenerate .claude/CATALOG.md — the on-demand inventory of this project's skills, agents, commands, and workflows.
argument-hint: (no args)
---

You are regenerating the **capability catalog** for this project.

## 1. Build
Run `python ${CLAUDE_PROJECT_DIR}/.claude/hooks/catalog.py`. This rescans
`.claude/skills/`, `.claude/agents/`, `.claude/commands/`, and `.claude/workflows/` and
rewrites the auto-generated block of `.claude/CATALOG.md` (the preamble above the marker is
preserved).

## 2. Report what changed
Show which assets were **added, removed, or had their description change** since the last
catalog (a `git diff .claude/CATALOG.md` makes this clear). If nothing changed, say so.

## 3. Mind the second tree
`CATALOG.md` is per-tree and is **not** symlinked. In this repo the `example-project/` tree
and the factory root each have their own `.claude/CATALOG.md`. If you regenerated one and the
other tree's assets also changed, regenerate it there too (run the same command with that tree
as the project root).

This catalog is **on-demand** — it is referenced by path from `CLAUDE.md`, not auto-loaded.
Don't paste its contents into the session unless asked; just confirm it's up to date.
