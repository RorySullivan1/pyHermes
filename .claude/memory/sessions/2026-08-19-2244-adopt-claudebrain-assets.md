# 2026-08-19 22:44 · adopt-claudebrain-assets

**Goal:** Curate and install claudeBrain .claude assets into pyHermes

## What happened
- Reviewed github.com/RorySullivan1/claudeBrain (a "factory" repo: root `.claude/` = asset-authoring meta-toolkit; `example-project/.claude/` = the canonical populated consumer with the REAL files — per the repo's single-sourcing convention, operational assets live in example-project and the factory holds symlinks). Cloned it to scratchpad; sourced everything from `example-project/.claude/`.
- User picked 3 of 4 tiers (via AskUserQuestion): **Core dev skills + agents**, **Operational infra + hooks**, **Financial + content-design**. Declined the **asset-authoring meta-toolkit** tier.
- Installed into `.claude/`: 22 skills, 6 agents, 3 commands (`/reindex`, `/version-set`, `/version-ship`), 2 workflows (`ship-version`, `verify-claims`), 7 hook scripts + 13 fragments, `context/python-project-instructions.md`, a fresh `memory/` scaffold, `README.md`, `CATALOG.md`, `settings.json`.
- User then authorized **activating all hooks** → wrote `settings.json` (13 hooks / 6 events) and regenerated it + `CATALOG.md` canonically with the generators (`build-hooks.py`, `catalog.py`); both `--check` report `ok`.

## Gotchas & dead ends
- **`build-hooks.py` design:** `settings.json` is GENERATED from the `*.json` fragments in `hooks/` (merged in filename order). It preserves existing top-level keys (e.g. `permissions`) and only rewrites the `hooks` block. To change hooks, edit fragments then run `build-hooks.py` — never hand-edit the `hooks` block. Same pattern for `CATALOG.md` via `catalog.py` (regen with `/reindex`).
- **Roadmap exclusion required a code fix:** `git_guards.py` did a top-level `import roadmap_guard` (outside try/except) → would crash the whole guard since we didn't copy `roadmap_guard.py`. Removed it from the imports + `GUARDS` tuple. Excluded roadmap entirely (no `session-start-roadmap.json`, no `roadmap-*` commands, no `advance-roadmap-step`/`screen-build`/`control-grounding` workflows).
- **Agent adaptation:** `python-developer` and `finance-quantitative-developer` were written for a `tools/` Python layer + VBA/VSTO lanes that don't exist here. Rewrote them for pyHermes' real shape: package `pyhermes` under `svc/`, root `pyproject.toml`, the CLAUDE.md hard constraints (102 KB / StrictUndefined / hex-color / construction-time validation), and `python test_builder.py` as the verification step (repo has NO pytest/ruff/mypy).
- **Two live caveats:** `github-operator` needs a GitHub **MCP server** (its `tools:` are all `mcp__github__*`); degraded with only `gh` CLI. `finance-quantitative-developer` + the quant skills are **speculative** — pyHermes generates HTML, no quant code yet.
- **Auto-mode classifier** blocked (a) copying the external `settings.json`/hooks as self-modifying config and (b) executing external scripts, until explicit user consent. Split the work into passive-copy first, then activation after confirmation.
- Dropped `change-end-to-end` workflow mid-task — it looked generic but is PowerApps-specific (canvas-app → Studio clipboard air-gap).

## State at end
- `.claude/` fully populated and hook-activated; generators in sync. All of `.claude/` is **untracked in git** (branch `main`). Python 3.13 on PATH; hooks verified importable.
- `SessionStart` hooks fire on the NEXT session (startup/resume/clear/compact); `Pre/PostToolUse` are already live.

## Open threads
- Offered to commit the `.claude/` library as its own commit on a new branch (user on `main`) — awaiting decision; not yet committed.
- **Unrelated pre-existing work still pending** (from start of session): the `dev/TODO.md` container-padding fix is only half-applied (title rows partly done, both content `<td>`s still have `2px` top padding; `highlight.html:14` has invalid comma-shorthand `padding:1px, 1px, 1px, 1px`), and `test_builder.py` has an uncommitted import-reorder.
