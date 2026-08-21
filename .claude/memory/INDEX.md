# MEMORY INDEX  ·  keep ≤ ~80 lines

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes = the **email builder** only. Delivery (`svc/gmail`, `svc/outlook`) still does not exist.
- `main` @ `44899cb` has absorbed everything through PR #30: `enums.py` (StrEnum vocab), `ThreeColumn`, the `CardGroup`/`highlight` rework, escaping (#12), URL-scheme validation (#24), wheel-packaged templates (#10), pytest suite (#9), CI (#11).
- **`test_builder.py` and the committed `weekly_market_wrap_v2.html` are GONE.** CI is now ruff → format → mypy → pytest, plus a separate wheel job that renders from a clean venv. Output goes to gitignored `output/`.
- **Image handling landed this session** on `claude/review-open-issues-rr8quq` @ `6169dcf` (pushed, **no PR**): `svc/builder/images.py`, `ImageBlock`, `templates/media/`, and `Email.assets()` — the manifest a delivery layer will consume.
- 349 tests pass; ruff/format/mypy clean; wheel verified to ship `templates/media/`.
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

- [2026-08-21] **The builder declares CID embeds; it never performs one.** Attaching a MIME part is a transport act, so `Email.render()` gives HTML and `Email.assets()` gives the parts to attach — for every `src="cid:X"`, one `ImageAsset` for X. This is the seam `svc/gmail`/`svc/outlook` implement — sessions/2026-08-21-1549-image-embedding-foundation.md
- [2026-08-21] Three embed strategies, all three needed: REMOTE (free, Outlook blocks it), CID (renders everywhere, costs *message* not HTML size so it dodges the 102 KB limit), DATA_URI (Gmail strips it, Outlook won't render it, +33% into the budget — supported but guarded and never a default) — sessions/2026-08-21-1549-image-embedding-foundation.md
- [2026-08-21] Image format is sniffed from **magic bytes, not the extension** — PNG/JPEG/GIF only; WebP and SVG are detected specifically so the rejection names the reason — sessions/2026-08-21-1549-image-embedding-foundation.md
- [2026-08-21] Content-IDs are content-addressed (`sha256(bytes)[:16]`): same image used twice is attached once, and the same input always yields the same output — sessions/2026-08-21-1549-image-embedding-foundation.md
- [2026-08-21] **Re-fetch `main` and read the tree before trusting CLAUDE.md's description of it.** CLAUDE.md lagged reality by several merged PRs this session and cost time — sessions/2026-08-21-1549-image-embedding-foundation.md
- [2026-08-21] **Read the tests before refactoring a private helper.** `Email._validate_size` is a `@staticmethod` on purpose (tests drive the size edges directly) and error messages are asserted on by field name — both broke when I changed them for unrelated reasons — sessions/2026-08-21-1549-image-embedding-foundation.md
- [2026-08-21] `models` ↔ `images` must stay a *lazy* cycle: function-local imports plus `TYPE_CHECKING` + quoted annotations. Module-level imports either direction deadlock — sessions/2026-08-21-1549-image-embedding-foundation.md

## Threads          (open items; remove when closed)
- **`claude/review-open-issues-rr8quq` @ `6169dcf` is pushed with no PR** — open one when ready. Branch was restarted from `main` because its old work was already merged.
- **Next natural step: `svc/gmail` / `svc/outlook`.** `Email.assets()` is the contract they implement. `ImageAsset.content_id` is bare — the `cid:` prefix (HTML) and `<>` (MIME header) are added by each consumer.
- Known wart left alone deliberately: `base.html` renders the logo with `alt="{{ firm_name }}"`, so an `EmailImage`'s own `alt` is ignored for the logo. Fixing it changes every existing email's output, so it wants its own decision.
- `claude/card-component-and-highlight-property` is pushed, has no PR, and looks superseded by what landed on `main` — probably deletable.
- `INLINE_LIMIT_KB = 48` is a judgment call (~half the 102 KB budget), not a spec number.

## Log              (append-only pointers)
- [2026-08-19 22:44] adopt-claudebrain-assets — curated + installed + activated `.claude/`; later committed to `main`, filed issues #1–3, removed `dev/` — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-20 12:05] review-open-issues — verified all 10 open issues by repro, found unfiled container-title crash, delivered tackle order; no code changed — sessions/2026-08-20-1205-review-open-issues.md
- [2026-08-20 13:20] review-open-issues (cont.) — filed #15, fixed cluster #5/#6/#7/#8/#15 in commit 3625965, opened PR — sessions/2026-08-20-1205-review-open-issues.md
- [2026-08-21 15:49] image-embedding-foundation — designed + shipped the EmailImage/EmbedStrategy/ImageAsset foundation and the Email.assets() manifest seam; ImageBlock + widened ChartBlock; 68 new tests — sessions/2026-08-21-1549-image-embedding-foundation.md
