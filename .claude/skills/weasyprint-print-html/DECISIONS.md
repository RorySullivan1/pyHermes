# Decisions — weasyprint-print-html

Why the assets are shaped this way. Seeded from the build brief (2026-09-15), then extended
with what the build itself settled. Kept **in the bundle** rather than only in project
memory because these skills are copied into other repositories, and the reasoning has to
travel with them; project memory does not.

## Engine choice

- **WeasyPrint over Playwright/Chromium.** Deterministic, no browser binary to get blocked
  by a corporate network, strong paged-media CSS. Tradeoff accepted: no JavaScript and only
  partial modern CSS.
- **WeasyPrint over ReportLab.** HTML/CSS templates are far faster to style well and keep
  design separate from data.
- **Typst kept as the fallback.** It ships its compiler as Python wheels with no system
  libraries. Revisit if WeasyPrint's layout limits become blocking.

## Architecture

- **Swappable renderer.** The pipeline is data → context dict → template → render, and
  `render_worker.py` is the **only** file that imports WeasyPrint. Changing engines means
  replacing one worker, not unpicking the pipeline.
- **Render via a worker subprocess.** Keeps every orchestration helper stdlib-only while
  still using the Python API — which the CLI cannot do — for a custom `url_fetcher` and for
  programmatic capture of the `weasyprint` logger.
- **Skills before the subagent.** Skills capture the rules at low complexity. `print-qa`
  only pays for itself once the image-heavy QA loop actually crowds the main context; build
  it when that happens, not before.
- **Generic and factsheet skills kept separate.** Reuse across report types, and different
  change cadence — engine rules move with WeasyPrint releases, brand and compliance move
  with the business.
- **Raster hashing for regression.** A PDF embeds creation timestamps, so its bytes differ
  on every run. Page PNGs are the stable comparison target.
- **Fail-closed templates.** A factsheet missing its disclaimer or its as-of date must not
  render at all.

## Settled during the build (2026-09-15)

- **A4 default, Letter by override.** Confirmed with the user. `size` is restated rather
  than variable-driven because WeasyPrint resolves `@page` descriptors before custom
  properties, so `size: var(--page-size)` does not work. The mm variables exist so figure
  sizing stays correct; `size` is the one line you repeat.
- **`fonts/` ships empty with a fallback stack.** Confirmed with the user: no unlicensed
  font file enters the repository. A template still renders, and lint **W004** plus
  `snapshot.py`'s fallback-family check make the substitution loud rather than silent.
- **Lint splits "dropped" from "inert" (W001 vs W007).** Measured, not assumed:
  `box-shadow`, `filter`, `aspect-ratio` and friends are rejected by the CSS parser and
  logged; `animation`, `transition`, `will-change` and `scroll-behavior` parse cleanly and
  do nothing, with **no** warning. One rule covering both would have described the second
  group wrongly. The first draft also listed `transform` as unsupported — it is supported,
  and shipping that would have cost design range for no reason.
- **Lint blanks comment bodies before every check.** The `@page` rule was satisfiable by a
  comment merely *mentioning* `@page`; the negative-control fixture's own header comment
  silenced E003 until this was fixed.
- **`--fail-on-fetch-error` exists because `--strict-fetch` alone is not a gate.** Strict
  mode contains the fetch immediately, but WeasyPrint turns the refusal into a log line and
  finishes, so the default outcome is a PDF missing an asset. For a factsheet that means
  shipping without a logo.
- **`FatalURLFetchingError` subclasses `BaseException`, not `Exception`.** So the worker's
  `except Exception` could not catch the one error the hard gate exists to raise — it died
  with a traceback and an empty stdout, and `render.py` reported "unknown error". The
  handler now names it explicitly. Found by running the gate, not by reading the code.
- **A strict-fetch bundle must be self-contained under one directory.** `base_url` does
  double duty: it resolves every relative URL *and* is the strict-fetch root. Widening it to
  reach a sibling `assets/` directory breaks the template's own relative paths, so the fix
  is to render from a directory that contains everything.
- **`css-support.md` is the linter's rule set, so it is probe-backed and drift-checked.**
  `probes/probe_css_support.py` re-measures every row against the installed WeasyPrint and
  reports DRIFT on an upgrade, because a stale table produces confidently wrong advice.
- **Environment facts are tiered.** `references/environment.md` separates field-settled
  (reported from the target JupyterHub, not re-verified) from probe-settled (measured).
  Neither is ever promoted to the other.

## Known gap

`snapshot.py` is the one script never executed end to end during the build: poppler is not
pip-installable and was unavailable in the build sandbox. Its precondition path, argument
handling and `pdffonts` parser are tested; **rasterisation and the live font report are
not.** Run `snapshot.py --check-tools` and then a real snapshot on the first factsheet, and
record the result in `probes/PROBES.md`.
