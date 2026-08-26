# 2026-08-26 01:05 · header-region-epic

**Goal:** Complete epic #38: make the header a first-class region (email > header | body)

## What happened
- **All five open sub-issues landed on `claude/review-open-issues-rr8quq`**, one commit each,
  every step leaving the gallery goldens byte-identical (the epic's own acceptance bar).
- **#33 — pure template split.** Both `HEADER` `<tr>` blocks (disclaimer bar + hero, VML
  included) moved verbatim to `svc/builder/templates/regions/header.html`; `base.html` got a
  `{{ header_html }}` hole. The placeholder sits at **column 0**: an indented `{{ }}` prepends
  its indentation to the region's first line only. Byte-identity also needed the *blank line
  after* the old block deleted, so the placeholder line's own `\n` supplies it.
- **#34/#35 — model split + region contract**, in one commit. New `svc/builder/regions.py`
  holds `Header`: `template_path`, `context()`, `render(engine, facts)`, `images()`,
  `assets()`, both resolution chains. `EmailMetadata` keeps the facts and gains a `header`
  field.
- **#36 — `MinimalHeader`**, its own template (`regions/header-minimal.html`), plus a
  **fourth gallery fixture** `minimal_header` so the harness covers it (goldens, lint, shots).
- **#37 — docs.** CLAUDE.md's composition model, ownership rule + field-split table, public
  API, directory map, gallery table, completeness rule, Open work; README's model section;
  `python-developer.md`. Every import/call the docs show was executed to check it runs.
- CI's wheel job now renders a `MinimalHeader` too — a region template that failed to ship
  was otherwise invisible until someone used it. Verified against a real installed wheel.

## Gotchas & dead ends
- **`regions.py`, not `models.py`** as issue #34 sketched: models.py holds data shapes, and a
  `Header` renders and owns a template. Costs one lazy back-edge (`models → regions` inside
  `_default_header()` / `__post_init__`), which mirrors the `models ↔ images` cycle already
  documented here.
- **Back-compat is `InitVar`s.** The four flat masthead kwargs are constructor-only: never
  attributes, absent from `fields()`/`repr`/`==`. That last one matters — a plain attribute
  would have made two emails differing only in masthead compare equal. Passing them *and*
  `header=` raises rather than silently picking one.
- **Two behaviour changes worth remembering**, both accepted deliberately: a bad masthead URL
  now raises at `EmailMetadata` **construction** (the `Header` validates in `__post_init__`)
  rather than at `.validate()`, and the message names `header.logo_url` /
  `header.background_image_url`. Three existing tests were updated for this, not worked around.
- **`Header.context()` layers facts OVER its own keys.** `{**presentation, **facts}`, not the
  other way round — that is what makes "a region cannot contradict a fact" mechanical. A test
  pins the two key sets as disjoint.
- The completeness tests in `tests/test_fixtures.py` had to grow: `EmailMetadata.header` is
  excluded by name (kitchen_sink supplies it the flat way *on purpose*, which is how the
  golden pins the back-compat path), and a new test reads `Header` fields off the **built**
  header so it holds however a fixture chooses to supply them.
- `--update-goldens` after adding the fixture created exactly two files and touched none of
  the existing six. That `git status` is the epic's byte-identity claim, mechanically.
- `minimal_header`'s mobile screenshot is **387px at a 375px viewport** — #76 reproduces on
  the variant too, since it is `base.html`'s `.kpi-cell` CSS, shared by every region.

## State at end
- **PR #80 merged to `main` (`673a6f2`) at 2026-08-26 04:12**, closing #33–#37 and epic #38
  (6/6 sub-issues). All four CI jobs green on the head — including `wheel`, the check this PR
  extended. Branch reset to `main`; PR watch stopped.
- 767 tests pass (714 before this epic); ruff, ruff format, mypy all green; wheel contains both region templates and
  still no `qa/`.
- `base.html` is 277 → 177 lines. Remaining: skeleton, preheader, both footer parts.

## Open threads
- **#76 and #78 were deliberately NOT folded in.** Each changes rendered output, and the
  epic's whole claim was that every step leaves the gallery byte-identical. They are their own
  PR, where the golden diff is the point rather than the problem. One of #78's three findings
  (the `rgba()` scrim) now lives in `templates/regions/header.html`.
- **#55 (footer) should transplant the region mechanism**, not invent a second one: extract to
  `templates/regions/`, give it `template_path` + `context()` + `images()`, layer facts over
  the region's keys, select it with an argument.
