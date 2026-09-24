# Probe kit — weasyprint-print-html

The fixtures and probes that make this skill's checks trustworthy. A check nobody has
watched **fail** is not a check.

| Artifact | Role |
|---|---|
| `flawed.html` | **Negative control** for lint. Every defect is deliberate. If lint calls this clean, lint is broken. |
| `clean.html` + `clean.css` | **Positive control** for lint, exercising `@font-face`, `@page`, `<thead>` and a `break-inside`-guarded flex row. Any finding here is a false positive. |
| `selfcontained/doc.html` + `doc.css` | **Positive control** for `--strict-fetch`: every asset at or below one directory, nothing resolved through `../`. |
| `probe_css_support.py` | Re-measures `references/css-support.md` against the installed WeasyPrint and reports **DRIFT**. Run after every upgrade. |

## Run log — 2026-09-15, WeasyPrint 69.0 (PyPI wheels, Debian container, Python 3.11.15)

**Lint.** Negative control: **7 errors, 8 warnings, exit 2** — E001×2, E002×4, E003, W001×3,
W002, W003, W004, W005, W007. Both positive controls: **clean, exit 0**. The linter
discriminates.

**Render.** `clean.html` rendered 1 page; the missing bundled font surfaced as
``Font-face 'Control Sans' cannot be loaded`` in the **fonts** bucket at exit **1** — which
confirms both the live render path and that the warning categories match WeasyPrint's real
message strings.

**`print-base.css`, verified on a two-page render** (59-row table): `@page` margin boxes
render; `string-set`/`string()` put the running label on **both** pages; `counter(page)` /
`counter(pages)` resolved to "Page 1 of 2" and "Page 2 of 2"; `display: table-header-group`
repeated the `<thead>` on page 2; rows split 27/32 with none broken.

**`--strict-fetch`, with controls.** Control — the same out-of-tree stylesheet loads fine
*without* the flag (so the test is not vacuous). Probe — with the flag it is refused, named
precisely, and categorised as `failed_fetches`. Adding `--fail-on-fetch-error` turned it
into exit **2**. The self-contained fixture passes both flags at exit **0** with no warnings.

**`--pdf-variant`.** `pdf/a-9z` rejected at exit 2 with the full valid list;
`pdf/a-3b` rendered.

**CSS support.** Both controls PASSed (`border-radius` accepted, `box-shadow` dropped), and
all 33 rows matched expectation — **no drift**. Findings worth naming: `aspect-ratio` is
**dropped** (hence mm sizing for figures), `transform` and `border-radius` are **supported**
(the first linter draft wrongly discouraged `transform`), and `animation` / `transition` /
`will-change` / `scroll-behavior` parse **silently** and do nothing.

**`snapshot.py`.** `--check-tools` and the run-without-poppler path both exit **2** with the
precondition named, and `parse_pdffonts` was unit-tested against real-shaped `pdffonts`
output including a subset prefix (`AAAAAA+BrandSans-Bold`) and an `emb: no` row.
**Not verified: rasterisation and the live font report** — poppler is a system binary and was
unavailable. See the Known gap in `../DECISIONS.md`.

## Closing the loop

A CONFIRMED expectation is left alone; a REFUTED one is fixed **at the source**, never
softened to save the claim. This run refuted three things and each was fixed in the code, not
in the wording: the `transform` misclassification, the comment-satisfiable `@page` check, and
the `BaseException` gap that made the hard fetch gate report "unknown error".
