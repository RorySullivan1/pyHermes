---
name: weasyprint-print-html
description: >
  Authoring HTML and CSS that is rendered to PDF by WeasyPrint — print-first markup,
  paged-media CSS, and the render → rasterize → inspect → fix loop. Use this skill whenever
  writing, editing, reviewing or debugging HTML/CSS whose output is a PDF rather than a
  screen: factsheets, tearsheets, index or fund reports, statements, invoices, certificates,
  any paginated document, or an HTML-to-PDF pipeline. Trigger on WeasyPrint, `@page`, print
  CSS, `break-inside`, running headers and footers, `counter(page)`, `pdftoppm`, `pdffonts`,
  PDF/A, embedded fonts, and on symptoms — "the table splits across pages", "the heading is
  stranded at the bottom", "the PDF looks different on the server", "my chart is missing",
  "this renders blank", "why is the font wrong". Trigger even when the user says only
  "report", "PDF", "factsheet" or "printable" without naming WeasyPrint: if the deliverable
  is a PDF built from HTML, this skill applies. Also use it before converting a dashboard,
  webpage or screen template to print. For the branded factsheet layout, data contract and
  compliance blocks, use `factsheet-template`, which depends on this skill.
---

# WeasyPrint print HTML

Print is not a narrow screen. It has hard page boundaries, no JavaScript, no network, and
no way to scroll — so screen-first habits do not degrade gracefully here, they produce a
plausible-looking PDF that is wrong. **You cannot judge a PDF's layout by reading its HTML.**
The loop below exists because the only thing that answers "does page 2 look right" is a
picture of page 2.

## Workflow

1. **Write** the template against `assets/print-base.css`. Override its custom properties;
   do not restate its rules.
2. **Lint** — `scripts/lint_print_html.py template.html`. Exit 2 means do not bother
   rendering yet.
3. **Render** — `scripts/render.py template.html out.pdf`. **Exit 1 is not success**:
   WeasyPrint degrades silently, so read the warning buckets.
4. **Snapshot** — `scripts/snapshot.py out.pdf` for page PNGs and the font report.
5. **Look at the page images.** Actually view them. Check every page boundary, the running
   footer on each page, and any table that continues.
6. **Fix and repeat — at most 3 times.** Then stop and report what is still wrong, with the
   specific pages and findings. Do not keep iterating; a loop that will not converge in
   three passes is a layout that needs a decision, not another attempt.

## Print-first rules

**No JavaScript.** WeasyPrint never executes it. Charts are **pre-rendered SVG** — matplotlib
is the default, and keep its `svg.fonttype = "path"` default so chart text becomes outlines
and stops depending on installed fonts. A `<script>` tag is lint **E001**.

**No remote assets.** No CDN CSS, no Google Fonts, no hotlinked images. Everything is local
and relative, resolved against `base_url`. A remote URL is lint **E002** — an error, not a
warning, because a failed fetch does not stop the render: you get a PDF with a hole in it.

**Fonts via `@font-face` from bundled files.** Never rely on a system font. A missing family
falls back **silently** and the only evidence is a log line and a different-looking PDF.
Verify after rendering with `pdffonts` (`snapshot.py` does it and flags fallback families by
name).

**Always declare `@page`.** Size, margins, and margin boxes for the running footer and
`counter(page)` / `counter(pages)`. No `@page` is lint **E003**. Repeating content goes in a
margin box, and text travels from the body into it via `string-set` / `string()` — never
`position: fixed`.

**Block flow and tables for anything that may cross a page boundary.** Flex and grid render
correctly but do not *fragment* dependably; use them only inside a `break-inside: avoid` box
that fits on one page. Lint **W005** flags a flex/grid container without it.

**Tables need `<thead>`.** `display: table-header-group` is what repeats a header across
pages, and it has nothing to act on without the element. Set `break-inside: avoid` on `tr`,
never on `table` — a long table should split; its rows should not. Lint **W003**.

**Control breaks explicitly.** `break-after: avoid` on **every** heading level,
`break-inside: avoid` on figures and callout blocks, `break-before: page` for a new section,
and `orphans`/`widows` at 3.

**Size figures in mm against the printable area.** `aspect-ratio` is *dropped* by WeasyPrint,
so ratio-sized figures silently collapse to intrinsic size. A4 with the shipped margins gives
**180mm** usable width and **263mm** usable height. **No `break-inside: avoid` block may be
taller than one page** — it cannot break and will not shrink, so it overflows.

**Know the three CSS outcomes — supported, dropped, inert.** Dropped properties announce
themselves in the log; **inert ones do not**. `animation`, `transition`, `will-change` and
`scroll-behavior` parse without complaint and do nothing (lint **W007**). Meanwhile
`transform`, `border-radius`, gradients, `opacity`, `gap`, grid and `float` **are**
supported — do not avoid them. The measured table is `references/css-support.md`.

**Compress rasters.** `--optimize-images`, plus `--jpeg-quality` / `--dpi` when needed. Lint
**W006** flags an `<img>` over 500 KB. Prefer SVG for anything vector.

**Restrict fetches when content is not yours.** `--strict-fetch` allows only `data:` URIs
and files under the base directory. Two things to know: a refused fetch is a **warning, not a
failure** — add `--fail-on-fetch-error` to make it fatal — and the allowed root is the
**base-url directory**, which also resolves every relative path. So a strict-fetch bundle
must be **self-contained under one directory**; widening `--base-url` to reach a sibling
`assets/` folder breaks the template's own relative paths.

**PDF/A for archival.** `--pdf-variant pdf/a-3b`. The worker validates the name against this
WeasyPrint's own variant table. **Do not claim PDF/UA or accessibility conformance** on the
strength of a variant flag — that needs external validation (veraPDF).

## Scripts

All four are stdlib-only except `render_worker.py`, which is the single file that imports
WeasyPrint. That is deliberate: the renderer stays swappable because replacing the engine
means replacing one worker.

| Script | Command | Exit codes |
|---|---|---|
| `lint_print_html.py` | `… file.html [file.css …] [--json] [--image-threshold-kb 500]` | 0 clean · 1 warnings · 2 errors |
| `render.py` | `… in.html out.pdf [--base-url D] [--python P] [--pdf-variant V] [--optimize-images] [--jpeg-quality N] [--dpi N] [--strict-fetch] [--fail-on-fetch-error] [--json]` | 0 clean · 1 **rendered with warnings** · 2 failed |
| `snapshot.py` | `… out.pdf [--dpi 110] [--out-dir D] [--expected-fonts a,b] [--max-pages N] [--baseline DIR] [--check-tools]` | 0 OK · 1 findings · 2 cannot run |
| `render_worker.py` | invoked by `render.py`; do not call directly | — |

Notes that matter in practice:

- `render.py` finds the WeasyPrint interpreter via `--python`, then `$WEASYPRINT_PYTHON`,
  then itself. On failure it names every candidate it tried.
- `snapshot.py --check-tools` first if unsure: without poppler it exits **2** and says so.
  A missing precondition is never reported as a clean snapshot.
- `--dpi 110` is the snapshot default on purpose — readable at 8pt, cheap enough to view
  several pages. Raise it only to inspect one detail.
- `--baseline DIR` diffs **page PNG hashes**, not PDF bytes: a PDF embeds timestamps, so
  identical input produces different bytes every run.

## Which reference to open

| Problem | Read |
|---|---|
| "Is this CSS supported?" · a style has no effect | `references/css-support.md` |
| A bad page break · table or heading straddling · running footers · sizing | `references/pagination.md` |
| Install · `import weasyprint` fails · wrong font on the server · notebook vs terminal | `references/environment.md` |
| Why the assets are shaped this way | `DECISIONS.md` |

## Verifying a change to this skill

`probes/` carries the controls. `flawed.html` must keep failing lint (7 errors, 8 warnings)
and `clean.html` + `selfcontained/doc.html` must keep passing — a linter change that makes
the flawed fixture clean is a broken linter, and `probes/PROBES.md` records each run.
`probe_css_support.py` re-measures the CSS table against the installed WeasyPrint and reports
drift; run it after any upgrade, because `css-support.md` **is** the linter's rule set.
