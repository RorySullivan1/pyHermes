# MEMORY INDEX  ·  keep ≤ ~80 lines

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes now has a curated `.claude/` asset library sourced from the `claudeBrain` factory (example-project/.claude): 22 skills, 6 agents, 3 commands, 2 workflows, 13 activated hooks. Generators (`build-hooks.py`, `catalog.py`) in sync (`--check` ok). Python 3.13.
- Whole `.claude/` tree is **untracked in git** (branch `main`) — not yet committed.
- Excluded by design: asset-authoring meta-toolkit, `.meta/roadmap` system, all VBA/VSTO/PowerApps assets.
- Two caveats: `github-operator` needs a GitHub MCP server (degraded on `gh` only); `finance-quantitative-developer` + quant skills are speculative (no quant code in repo yet).

## Decisions        (append-only; supersede, never delete)
- [2026-08-19] Installed 3 of 4 claudeBrain tiers (core dev, infra+hooks, financial+design); skipped authoring meta-toolkit — user choice via AskUserQuestion — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Activated all 13 hooks via generated `settings.json`; edit hook *fragments* + rerun `build-hooks.py`, never hand-edit the `hooks` block — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Removed `roadmap_guard` from `git_guards.py` (imports + GUARDS) to prevent a crash from the excluded roadmap system — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Re-scoped `python-developer` + `finance-quantitative-developer` agents from a `tools/` layer to pyHermes' `svc/` package; verification is `python test_builder.py` (no pytest/ruff/mypy) — sessions/2026-08-19-2244-adopt-claudebrain-assets.md

## Threads          (open items; remove when closed)
- Commit the `.claude/` library as its own commit on a new branch (user on `main`) — offered, awaiting decision.
- Pre-existing (unrelated): `dev/TODO.md` container-padding fix is half-applied (content `<td>`s still `2px` top; `highlight.html:14` has invalid comma-shorthand padding); `test_builder.py` has an uncommitted import-reorder.

## Log              (append-only pointers)
- [2026-08-19 22:44] adopt-claudebrain-assets — curated + installed + activated the `.claude/` library — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
