# 2026-10-29 09:00 · reference-reports

**Goal:** Build roadmap v0.3.0, the reference reports and the speed benchmark, through advance-roadmap-step

## What happened
- The owner chose repo stand-ins for all three reference reports (2026-10-28): `daily-note` is
  `examples/daily-investment-note`, `research-report` is `examples/quarterly-review`, and
  `product-brochure` is the `tri_fold_letter` fixture. The v0.3.0 card was revised to match.
- Built `reference/` (a SPEC.md and a build.py each), the `qa/reference.py` registry,
  `python -m qa.benchmark`, the recorded baseline in `reference/README.md`, and
  `tests/test_reference_reports.py`.
- Baseline: 291 / 101 / 159 author lines; every report a second or less of machine time, PDF
  included. The author's code is the cost to cut; the owner's minutes are not yet recorded.
- Review: no must-fix. Its optional notes were taken: one build-timing definition (the script is
  loaded once and `build()` alone is timed), the overlapping columns stated, `-n` validated, a
  missing extra skipped, three spec claims corrected. The audit's note that Gate 1 was undefined is
  answered: Gate N is stage N's milestone, and Gate 1 needs the stand-ins replaced.
- PR #478 opened on the owner's standing go-ahead.

## Gotchas & dead ends
- Debian's system Pillow shadows pip's under python 3.11 here: `python -m pip install
  --ignore-installed pillow` before matplotlib will import.
- With `[pdf]` installed, `test_attachments.py`'s two PDF-equality tests fail here, on main too
  (no HarfBuzz-Subset): the known determinism thread, not a regression.
- argparse rejects a list default with `nargs="*"` and `choices`; validate by hand.
- Committing before delegating kept both checks on one stable diff (the v0.2.0 lesson).

## State at end
- PR #478 open; cursor v0.4.0 (first public release on PyPI).

## Open threads
- On merge: flip v0.3.0 to shipped in the INDEX, its card and `.meta/version`.
- The owner's minutes, data to sent, once real reports replace the stand-ins.
