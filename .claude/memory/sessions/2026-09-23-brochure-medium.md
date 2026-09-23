# 2026-09-23 · brochure-medium

**Goal:** Implement epic #172 — `svc/brochure/`, a sheet folded into panels (#186–#189).

Started from `main` @ `4276727` (PR #192 merged). Eight commits on `claude/gifted-ritchie-7dkp5g`.

| Commit | Issue | What |
|---|---|---|
| `3e75ed4` | — | Numbered-list ordinal width as a CSS property: the first brochure raster found it |
| `d3411d7` | #186, #187 | FoldFormat, Panel, BROCHURE_MEDIUM, imposition, Brochure, proof(), overflowing_panels |
| `3b019fa` | #188 | bleed + slug + marks, grounds into the bleed, safe area, print_dpi, print-marks / rgb-only (INFO) |
| `7045f2a` … `3e4073a` | #189 | PullQuote, drop_cap, FlowedColumns, TextBlock(figure=ImageBlock(wrap=…)), Panel.background_image |

## Decisions and why
- **Panels are absolute boxes with `overflow: hidden`**, measured three ways (table cells ran
  a side onto five more sheets). The clip is made loud by a sentinel `id` read from WeasyPrint's
  public `page.anchors`; `svc.pdf.layout()` was added for it. Posted on #172 as #186 asked.
- **A panel is a frame one panel wide with `pad_x` = inset**, so no shared template changed.
  A coloured panel rebinds the theme's surface; an imaged one clears its sections' grounds.
- **The declared bleed is bleed + slug**: WeasyPrint draws marks inside the declared bleed and
  under anything painted there.
- **Safe area and resolution are construction checks, not `constraints`**: a Constraint sees
  only markup. The done-when won; recorded in `brochure.md`.
- **Wrap is hosted by `TextBlock.figure`**: a float cannot leave its table row.
- **`a4_editorial` is its own paged fixture**: `a4_portrait`'s sheet counts are claims.

## What proved it
- PDF read-back: each face's position against positions written out literally, the media /
  bleed / trim boxes, the cover's picture past the trim, white in the slug, a crop mark, the
  proof's guides and labels, overflow on and off the sheet, and a margin case that fits.
- Every email degradation is a byte-identity test; kitchen_sink's golden did not move for the
  drop cap. Rasters of every primitive on A4 and on the brochure.

## Gotchas & dead ends
- **A test that reads the table it tests agrees with a wrong table.** The first PDF position
  test compared against `impose()`; a swapped C-fold stayed green until the positions were
  written out.
- **`lstrip_blocks` eats indentation before a block tag**, so an inline `{% if %}` around
  `{{ content }}` moved every paged golden; the wrapper went on lines of its own.
- **A floated `::first-letter` does not shorten the first line in WeasyPrint**; a real span does.
- **CI's `pdf` job named only two test modules**; `test_apparatus` (#171) had never run in CI.
  It now names all five PDF-reading modules.
- Run `python -m mypy`: the bare `mypy` on PATH lacks jinja2.

## State at end
- **PR #194 merged** 2026-09-23; one `Closes` per issue, #172 closed with 4/4. CI green on all
  six jobs at first push, the widened `pdf` job included.
- **#193 built out** into an epic with #195–#200, after probing the current PDF: links are live
  (`page.links`), metadata comes from `meta` tags, WeasyPrint 70 writes `pdf/ua-1`. The paged medium already carries the cover,
  contents and portrait/landscape; the gaps are a PDF attachment in `build_message`, a size
  budget, metadata, verified links and tagged PDF.
