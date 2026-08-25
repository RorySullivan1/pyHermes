# 2026-08-24 21:41 · golden-snapshots

**Goal:** Land #58 — golden snapshots over the fixture gallery, resolving #32 onto the same harness

## What happened

- **`qa/goldens.py`** — the harness. Per fixture: `goldens/<name>.html` (byte-for-byte, no
  normalization) and `goldens/<name>.assets.txt` (one tab-separated record per `ImageAsset`
  in manifest order: content-id, MIME type, byte length, filename). Public surface:
  `check_fixture()`, `write_fixture()`, `render_manifest()`, `GoldenMismatch`.
- **`tests/test_goldens.py`** (17 tests) — the gate plus six detection tests.
- **`kitchen_sink` became #32's characterization email**: metadata now exhaustive over
  `EmailMetadata` (hosted logo, header background, the four skeleton-copy strings, explicit
  `logo_alt`/`logo_width`). Two new completeness tests in `test_fixtures.py`.
- 636 tests, all four gates green, wheel re-verified to contain no `qa/` entries.
  Branch @ `32c1b65`, pushed.

## Decisions worth not re-deriving

- **The manifest stores no image bytes.** They live in the fixture that generates them, and a
  Content-ID is `sha256(bytes)[:16]` — different bytes cannot keep the same id, so id + length
  catches everything a second copy would, at none of the repo weight.
- **Manifest order is preserved, not sorted.** The header epic moves image aggregation between
  classes; a dropped, duplicated or reordered asset can happen with the HTML *byte-identical*,
  which is exactly why it is a second artifact rather than a section of the first.
- **`--update-goldens` is the only regeneration path, and a missing golden FAILS.** A golden
  that writes itself on first run pins whatever happened to be true that day and the reviewer
  never sees it. Registered in the **root** `conftest.py` — pytest reads `pytest_addoption`
  only from the rootdir conftest, not from `tests/conftest.py`.
- **Fixture `build()` gained an optional `template_dir`**, threaded to `EmailBuilder`. It is
  what lets the gallery render against a *candidate* template set, which is the question a
  template migration actually asks. Kept out of the `FixtureBuilder` alias so consumers are
  never obliged to pass it.
- **`qa/goldens.py` imports no pytest**, so #61's `preview` CLI can check goldens without a
  test framework.
- **#32 is satisfied here, not separately.** #58 required one harness; #32 had not started.
  Do not add a `tests/test_golden_render.py` — CLAUDE.md says so too.

## Gotchas & dead ends

- **"Delete `</html>` to test the truncation path" does not test it.** `base.html` ends
  `</html>\n`, so removing the tag leaves a `\n` behind and the two strings diverge *mid-file*,
  not as a prefix. The real prefix case is the **manifest** — drop the last asset from
  `kitchen_sink` and the actual text is a strict prefix of the golden, which is what exercises
  `<end of file>` in the report.
- The report was verified by **perturbing a golden by hand** and reading the output, not by
  trusting the tests: fixture, artifact, line 176, byte offset 9407, three lines of context,
  `- expected` / `+ actual`, and the regeneration hint. Same discipline as #57's negative
  control.
- `EmailMetadata` field count is 21; `kitchen_sink` was setting 13. The eight it missed were
  the two image fields, `logo_alt`, `logo_width` and the four skeleton-copy strings — precisely
  the surfaces #38 restructures, so the golden would have been blind where it mattered most.
- The `logo` image's own `alt`/`width` deliberately **differ** from the explicit metadata, so
  the golden records *which* branch of the resolution chain won rather than only that it ran.

## State at end

- **PR #75 merged** at 2026-08-25 04:22 → `main` @ `60b718d`. It carried the README, #57's
  gallery and #58's goldens, and closed **#57, #58 and #32**. CI was green on 3.11/3.13 plus
  the wheel job; 636 tests. The branch was then reset onto the merged `main`, and the PR watch
  stopped.
- Two things verified rather than assumed before it went up: the regeneration path from a
  **clean checkout** (fresh clone + venv → `pytest` green against the committed goldens, then
  `pytest --update-goldens` leaving `git status` empty), and the mismatch report itself, by
  corrupting a golden by hand and reading the output.
- One self-inflicted defect worth remembering: `<name>` inside inline backticks in a **PR body**
  is swallowed as an HTML tag, so the goldens table shipped reading `goldens/.html`. Use a
  brace placeholder (`{fixture}`) in GitHub prose.

## Open threads

- **#32 and #58 are closed** by PR #75. #32 also carries a comment pointing at where the
  harness actually lives, because its own body proposes `tests/test_golden_render.py` +
  `tests/fixtures/golden_email.html` — a #38 reader following the issue would otherwise build
  the second mechanism #58 exists to prevent.
- Epic #54 remainder: **#59 screenshots** is next, then #60 lint, #61 preview CLI, #62 docs.
  #59 inherits the gallery *and* the goldens — a screenshot run that disagrees with a golden
  means the renderer moved, not the design.
- Epic #54's risk note still stands, and #59 has to answer it deliberately: **what rendering
  environment to pin**. This container ships Chromium at `/opt/pw-browsers/chromium` with
  `PLAYWRIGHT_BROWSERS_PATH` preset and `playwright install` disabled — convenient, and exactly
  the thing one pins to by accident. Also curate the Outlook-unsupported-CSS list rather than
  scraping it; a noisy linter gets disabled, which is worse than none.
- The migration epics (#38 / #45 / #46 / #55 / #56) are now unblocked — the gate they all
  waited on is in the suite.
