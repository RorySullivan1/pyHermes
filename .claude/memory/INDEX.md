# MEMORY INDEX  ·  keep ≤ ~80 lines

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes = the **email builder** only. Delivery (`svc/gmail`, `svc/outlook`) still does not exist.
- `main` @ `44899cb` holds everything through PR #30, incl. PR #27's rework: **`Highlight` is gone** (it is now `highlight=True` on any container) and **`KpiItem` subclasses `Card`**; stacking is `CardGroup(orientation="vertical")`, not a second component.
- **`claude/review-open-issues-rr8quq` @ `dad1c71` is PR #31, open and CI-green — awaiting the user's merge decision.** It carries image embedding (`images.py`, `ImageBlock`, `templates/media/`, `Email.assets()`) plus the parameter pass.
- Parameters with defaults: `logo_alt` / `logo_width` resolve **explicit metadata → the `EmailImage`'s own value → `firm_name` / 90**, and the four skeleton-copy strings (`contact_heading`, `contact_cta_label`, `unsubscribe_label`, `view_in_browser_label`) default to what `base.html` used to hardcode.
- 379 tests pass; ruff / `ruff format --check` / mypy clean; wheel job renders from a clean venv.
- **Three open epics on GitHub**: #38 header region (#32–#37), #45 size themes (#39–#44), #46 color themes (#47–#51). Shared prerequisite for all template migration: golden test #32. All three touch `base.html` + `EmailMetadata` — sequence, don't interleave.
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
- [2026-08-23] **`highlight` is a property of a container, not a container.** `Highlight`'s template was `full-width.html` plus a tint — presentation, not geometry — so it was removed rather than kept as a subclass; `background_color` still beats the tint — sessions/2026-08-23-1731-component-rework-and-parameters.md
- [2026-08-23] **One `CardGroup` with an `orientation`, not two components.** `vertical` is also what `horizontal` collapses to on mobile, so they are one thing viewed two ways; `KpiStrip` stays as a warning alias — sessions/2026-08-23-1731-component-rework-and-parameters.md
- [2026-08-23] **`KpiItem` subclasses `Card` and adds no fields** — it only overrides `validate()` to keep "a KPI always has a value". `Card.body` is an HTML field: escaping it is the caller's job — sessions/2026-08-23-1731-component-rework-and-parameters.md
- [2026-08-23] **Non-formatting values are parameters with defaults that reproduce today's output.** Old hardcoded behaviour becomes the last link in a resolution chain, so nothing existing re-renders differently. Fonts/colours/padding/680px geometry stay fixed — that is the design system — sessions/2026-08-23-1731-component-rework-and-parameters.md
- [2026-08-23] **Audit templates by parsing text nodes, not by grepping.** `grep` matched `Contact Us` inside an HTML section-marker comment and produced a false "not fixed" reading; parsing found exactly the four real strings — sessions/2026-08-23-1731-component-rework-and-parameters.md
- [2026-08-23] **The contact CTA is emitted twice** (VML for Outlook, `<a>` for everyone else). Any change to it must touch both paths, and a test asserts the label appears twice — sessions/2026-08-23-1731-component-rework-and-parameters.md
- [2026-08-23] **Color-theme epic #46: the Theme is the unit of customization, never a single color at a call site.** Unlike size themes (#45, closed presets), users may construct/pass whole `Theme` objects via `EmailMetadata.theme` — coherence held by frozen-complete-validated construction, no per-component color knobs; `KpiItem.color`/`TableRow.colors` stay caller *data* — sessions/2026-08-23-1915-open-color-theme-epic.md
- [2026-08-23] Shadows are stored as **base hex + alpha float, composed to rgba() at render** — never raw rgba strings; the scrim `rgba(20,30,44,0.65)` is `#141E2C` @ 0.65 — sessions/2026-08-23-1915-open-color-theme-epic.md
- [2026-08-23] The dark-mode-forcing block and mobile `@media` block carry their **own hardcoded copies** of palette colors with `!important` — any color/size migration must feed them the same tokens as the inline styles (#41/#49 own this) — sessions/2026-08-23-1915-open-color-theme-epic.md

## Threads          (open items; remove when closed)
- **PR #31 is open and green — the user decides whether to merge.** Do not merge unasked.
- **Epics #38/#45/#46 all start at golden test #32**; the render-context injection mechanism is built once — first of #40 (size) / #48 (theme) to land sets the pattern.
- **Next natural step: `svc/gmail` / `svc/outlook`.** `Email.assets()` is the contract they implement. `ImageAsset.content_id` is bare — the `cid:` prefix (HTML) and `<>` (MIME header) are added by each consumer.
- `claude/card-component-and-highlight-property` merged as PR #27; the remote branch is safe to delete.
- `INLINE_LIMIT_KB = 48` is a judgment call (~half the 102 KB budget), not a spec number.

## Log              (append-only pointers)
- [2026-08-19 22:44] adopt-claudebrain-assets — curated + installed + activated `.claude/`; later committed to `main`, filed issues #1–3, removed `dev/` — sessions/2026-08-19-2244-adopt-claudebrain-assets.md
- [2026-08-20 12:05] review-open-issues — verified all 10 open issues by repro, found unfiled container-title crash, delivered tackle order; no code changed — sessions/2026-08-20-1205-review-open-issues.md
- [2026-08-20 13:20] review-open-issues (cont.) — filed #15, fixed cluster #5/#6/#7/#8/#15 in commit 3625965, opened PR — sessions/2026-08-20-1205-review-open-issues.md
- [2026-08-21 15:49] image-embedding-foundation — designed + shipped the EmailImage/EmbedStrategy/ImageAsset foundation and the Email.assets() manifest seam; ImageBlock + widened ChartBlock; 68 new tests — sessions/2026-08-21-1549-image-embedding-foundation.md
- [2026-08-23 17:31] component-rework-and-parameters — removed `Highlight` into a container property, made `KpiItem` a `Card`, added `CardGroup` orientations; then made logo alt/width and skeleton copy parameters. PR #31 open and green — sessions/2026-08-23-1731-component-rework-and-parameters.md
- [2026-08-23 19:15] open-color-theme-epic — audited all color/shadow usage (18 hexes, ~235 occurrences, 20 files) and filed epic #46 + sub-issues #47–#51 (Theme object: vocabulary → plumbing → migration → custom seam → docs); no code changed — sessions/2026-08-23-1915-open-color-theme-epic.md
