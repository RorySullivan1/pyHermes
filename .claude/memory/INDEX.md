# MEMORY INDEX  ·  keep ≤ ~80 lines

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes carries a curated `.claude/` asset library from the `claudeBrain` factory: 22 skills, 6 agents, 3 commands, 2 workflows, 13 activated hooks. Generators (`build-hooks.py`, `catalog.py`) in sync. Python 3.13. **Committed & pushed to `main`.**
- Repo now has a `.gitignore` (Python artifacts); previously-tracked `svc/**/__pycache__` bytecode was untracked. `settings.local.json` remains tracked (pre-existing, left alone).
- Container-template padding work lives in **GitHub issues #1/#2/#3** (title / content / comma-shorthand); `dev/` was deleted. The fixes are not yet implemented.
- Excluded by design: asset-authoring meta-toolkit, `.meta/roadmap` system, all VBA/VSTO/PowerApps assets.
- Two caveats: `github-operator` needs a GitHub MCP server (degraded on `gh` only); `finance-quantitative-developer` + quant skills are speculative (no quant code in repo yet).

## Decisions        (append-only; supersede, never delete)
- [2026-08-19] Installed 3 of 4 claudeBrain tiers (core dev, infra+hooks, financial+design); skipped authoring meta-toolkit — user choice via AskUserQuestion — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Activated all 13 hooks via generated `settings.json`; edit hook *fragments* + rerun `build-hooks.py`, never hand-edit the `hooks` block — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Removed `roadmap_guard` from `git_guards.py` (imports + GUARDS) to prevent a crash from the excluded roadmap system — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Re-scoped `python-developer` + `finance-quantitative-developer` agents from a `tools/` layer to pyHermes' `svc/` package; verification is `python test_builder.py` (no pytest/ruff/mypy) — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Committed `.claude/` + CLAUDE.md rewrite directly to `main` (+push) per explicit user OK; added `.gitignore` and untracked `__pycache__` bytecode — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Migrated `dev/TODO.md` to GitHub issues #1/#2/#3 and deleted `dev/` — sessions/2026-08-19-2244-adopt-claudebrain-assets.md

## Threads          (open items; remove when closed)
- Padding fixes are unimplemented — tracked in GitHub issues #1 (title padding), #2 (content padding), #3 (invalid comma-shorthand). Not in memory; use the tracker.

## Log              (append-only pointers)
- [2026-08-19 22:44] adopt-claudebrain-assets — curated + installed + activated `.claude/`; later committed to `main`, filed issues #1–3, removed `dev/` — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
