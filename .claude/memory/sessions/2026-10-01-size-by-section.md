# 2026-10-01 · size-by-section

**Goal:** Implement #259: the size report names each body section, and the check reports on an
email over 102 KB.

## What happened
- PRs #289 (#270) and #291 (the superpowers cleanup) merged first; the branch fast-forwarded.
- `Document.rendered_sections()` renders each body section through `render()`'s own engine and
  section list. `size_report(html, sections)` gives each its own region and keeps the sum exact.
- `SizeError.html` carries the refused markup; `pyhermes.check.render_for_check()` returns it.
  `python -m pyhermes.check` always measures; `qa.preview` measures with `--lint` and, without it,
  says to add `--lint`.
- The issue's own case: 149.5 KB, four sections, listed 59.6 / 40.1 / 30.3 / 10.8 KB, exit 1.
- No golden moved.

## Gotchas & dead ends
- `letter_dense`'s first `Page` was not found: `PagedDocument._body_context` dropped its leading
  break, so the standalone render differed. The rule moved to `_body_sections`, shared by both.
- A paged document carries no markers, so its non-section bytes went unattributed until a
  `(rest of document)` region took them.
- A brochure imposes its panels, so no section is found; the report falls back to the markers.
- `test_typography` sliced `document.py` between two strings; moving the binder into
  `_bound_engine()` emptied the slice. The claim (one binder, four axes) still holds.

## Verification
- Three mutations each failed the new tests: dropping `html=` from the `SizeError`, not
  subtracting section bytes, and moving the break rule back into `_body_context`.
- ruff, format, mypy and the prose budget are clean. The suite's only failures are the seven PDF
  tests that need HarfBuzz-Subset, as on `main` in this container.
