# MEMORY INDEX  ·  keep ≤ ~80 lines

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes carries a curated `.claude/` asset library from the `claudeBrain` factory: 22 skills, 6 agents, 3 commands, 2 workflows, 13 activated hooks. Generators (`build-hooks.py`, `catalog.py`) in sync. Python 3.13. **Committed & pushed to `main`.**
- Repo has a `.gitignore` (Python artifacts); `settings.local.json` remains tracked (pre-existing, left alone).
- **Padding issues #1/#2/#3 are CLOSED** — fixed in f8f0d7e, merged as PR #4. `dev/` was deleted.
- Issues #5–#14 opened 2026-08-20, all verified by repro. **The correctness cluster #5/#6/#7/#8 + #15 is FIXED** on `claude/review-open-issues-rr8quq` (commit 3625965) — PR open, closes on merge. #9–#14 (tooling/docs/packaging) remain.
- **#15** = every container crashed when `title` was omitted (`section_title` undefined under `StrictUndefined`); filed and fixed in the same pass.
- `python test_builder.py` passes (35.9 KB) and still only covers the happy path — **#9 (pytest) is the next step**, and the repro suite from the cluster work drops straight into it.
- Excluded by design: asset-authoring meta-toolkit, `.meta/roadmap` system, all VBA/VSTO/PowerApps assets.
- Two caveats: `github-operator` needs a GitHub MCP server (available in remote sessions); `finance-quantitative-developer` + quant skills are speculative (no quant code in repo yet).


## Decisions        (append-only; supersede, never delete)
- [2026-08-19] Installed 3 of 4 claudeBrain tiers (core dev, infra+hooks, financial+design); skipped authoring meta-toolkit — user choice via AskUserQuestion — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Activated all 13 hooks via generated `settings.json`; edit hook *fragments* + rerun `build-hooks.py`, never hand-edit the `hooks` block — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Removed `roadmap_guard` from `git_guards.py` (imports + GUARDS) to prevent a crash from the excluded roadmap system — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Re-scoped `python-developer` + `finance-quantitative-developer` agents from a `tools/` layer to pyHermes' `svc/` package; verification is `python test_builder.py` (no pytest/ruff/mypy) — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Committed `.claude/` + CLAUDE.md rewrite directly to `main` (+push) per explicit user OK; added `.gitignore` and untracked `__pycache__` bytecode — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-19] Migrated `dev/TODO.md` to GitHub issues #1/#2/#3 and deleted `dev/` — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-20] Verify issue claims by *reproducing* them, not by reading the code — this is what surfaced the unfiled container-title crash and showed #6b/#7/#8a fail silently rather than raising — sessions/2026-08-20-1205-review-open-issues.md
- [2026-08-20] Fix the #5/#6/#7/#8 correctness cluster BEFORE writing the #9 pytest suite, so tests are written against the corrected error paths — sessions/2026-08-20-1205-review-open-issues.md
- [2026-08-20] Under `StrictUndefined`, ALWAYS inject a context key with a falsey default rather than `if self.x: ctx["x"] = ...` — an undefined name raises even inside `{% if %}`. This one pattern caused #5 and #15; the same hazard via direct indexing (`row.colors[i]`) caused #6 — sessions/2026-08-20-1205-review-open-issues.md
- [2026-08-20] Prove a no-behavior-change refactor by diffing the rendered `weekly_market_wrap_v2.html` — byte-identical output is the repo's cheapest regression proof absent a test suite — sessions/2026-08-20-1205-review-open-issues.md

## Threads          (open items; remove when closed)
- **Tackle order** (step 1 DONE): ~~(1) correctness cluster #5+#6+#7+#8+#15~~ shipped; next **(2) #9 pytest** — lift the cluster's repro suite into `tests/`; then (3) #11 CI → #10 wheel → #12 escaping → #13 docstring → #14 retire assembler.
- PR for the cluster is open and unmerged — issues #5/#6/#7/#8/#15 close on merge, not before.
- #12 (escaping helper) is low priority only while content is hand-curated — it becomes top priority the moment content comes from an external source.

## Log              (append-only pointers)
- [2026-08-19 22:44] adopt-claudebrain-assets — curated + installed + activated `.claude/`; later committed to `main`, filed issues #1–3, removed `dev/` — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-20 12:05] review-open-issues — verified all 10 open issues by repro, found unfiled container-title crash, delivered tackle order; no code changed — sessions/2026-08-20-1205-review-open-issues.md
- [2026-08-20 13:20] review-open-issues (cont.) — filed #15, fixed cluster #5/#6/#7/#8/#15 in commit 3625965, opened PR — sessions/2026-08-20-1205-review-open-issues.md
