# 2026-09-22 13:51 · format-coverage-audit

**Goal:** Assess how far the codebase is from completely structuring quantitative emails, brochures and factsheets

Read-only audit, no code changed. Verdict: **email complete, factsheet mostly, brochure partial.**
The medium abstraction is already the right shape for all three — a new format is a frozen
`Medium` plus a region set, not a fork — so the distance is content and print mechanics, not
architecture.

## What happened
- Walked `svc/builder` (8 components, 4 containers, 3 axes, 2 projections), `svc/email`,
  `svc/document`, `svc/pdf`, and every template, against the three target formats.
- **Email is finished** for structure. The residual gap is *above* the builder and shared by all
  three formats: there is **no data layer**. Figures arrive as pre-formatted strings, cell colour
  is hand-assigned by the caller, and `ChartBlock` takes a PNG rendered elsewhere. `filters.py`
  carries `percent` (a CSS line-height ratio, not a finance format), hex validation and escaping —
  nothing for currency, bps, sign-aware deltas, or a DataFrame→`DataTable` adapter.
- **Factsheet** is buildable today (`qa/fixtures/a4_portrait.py` is nearly one), short three things:
  break discipline (below), document apparatus (no ToC, footnotes, figure/table numbering,
  cross-references), and page geometry (`PageFormat` is width/height only; horizontal margin is
  deliberately hardcoded 0 in `document/base.html`, vertical comes from `size.frame.outer_pad_y`).
- **Brochure** is the only one needing a new medium: no panel/fold geometry, no imposition
  (`Page` means "break here", never "side 2 of sheet 1"), no bleed/crop marks/CMYK, and no
  editorial primitives (full-bleed outside the cover, text wrap, pull quote, drop cap, flowed
  multi-column text — `TwoColumn`/`ThreeColumn` are fixed-ratio table cells, not a measure).
- Proposed order: pagination hardening → data layer → apparatus → `svc/brochure/`.

## Gotchas & dead ends
- **The paged medium has no break discipline inside an exhibit.** Grepping every template, the
  only break properties in the tree sit on `page.html`, `cover.html` and `back-matter.html`.
  There is no `break-inside: avoid` anywhere, and `analysis/data-table.html:46` emits its header
  row as a bare `<tr>` with **no `<thead>`** — so a holdings table crossing a sheet loses its
  headers and splits wherever the print engine likes. Invisible in the email medium, which is
  why it survived: the markup is shared and email has no sheets. Cheapest high-value fix there is,
  and standing rule 3 already covers proving it (paged fixtures photograph from the PDF).

## State at end
- Nothing edited, nothing pushed. `main` unchanged at `ab193be`; backlog still just #150.

## Open threads
- None opened. The four-step ordering above is a proposal, not filed issues — an epic for
  pagination hardening (`thead` + `break-inside`) is the obvious first sub-issue if it is taken up.

## Filed

[2026-09-22 14:07] The four-step ordering became four epics with seventeen sub-issues, all
labelled `enhancement`, all children attached through the sub-issue API rather than by a bare
reference in the body:

| Epic | Sub-issues | Depends on |
|---|---|---|
| #169 pagination hardening | #173 `thead`/`tbody` · #174 headings and fine print · #175 page margins · #176 fixture, PDF test, lint rule | — |
| #170 data layer | #177 `formats.py` · #178 semantic `tone` · #179 DataFrame adapter `[data]` · #180 Figure adapter `[charts]` | — |
| #171 document apparatus | #181 numbering · #182 footnotes · #183 contents · #184 cross-references · #185 running section header | #181 → #183 → #184 |
| #172 brochure medium | #186 fold geometry (design-first) · #187 imposition · #188 print prep · #189 editorial primitives | #169; #186 first |

Two things re-verified before filing rather than taken from the audit: WeasyPrint 70 does
repeat a `thead` across sheets (120 rows, 3 sheets, header on all three), and
`semantic.positive`/`negative` have no render site in any template. #178 gives them one.

Three decisions the epics carry that the audit did not make: a `tone` is *data* in the sense
`Cell.color` is (a word, not a hex — the theme keeps authority); apparatus numbering is
computed in Python, once, so both projections agree, with the page number the single
print-engine exception; and CMYK is a recorded non-goal of the brochure medium rather than a
silent omission.
