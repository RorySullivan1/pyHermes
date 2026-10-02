---
paths:
  - "pyhermes/brochure/**/*"
  - "pyhermes/builder/templates/brochure/**/*"
  - "pyhermes/builder/templates/document/editorial.html"
  - "qa/fixtures/tri_fold_letter.py"
  - "qa/fixtures/a4_editorial.py"
  - "tests/test_brochure.py"
  - "tests/test_brochure_pdf.py"
  - "tests/test_editorial.py"
---

# The brochure medium — a sheet folded into panels (epic #172)

**The distance to a brochure is a medium; the distance to a factsheet is not.** A factsheet
needed break discipline and document apparatus on the paged medium that already existed
(#169, #171). A brochure changes the skeleton, the unit of layout, the page geometry, the
constraints and the lint rules, while keeping the PDF exporter. That is the profile #157
defined for a medium, so it is `pyhermes/brochure/`, beside `pyhermes/email/` and `pyhermes/document/`.

| Module | Holds |
|---|---|
| `fold.py` | `FoldFormat`, `FoldKind`, the four presets and their width arithmetic |
| `panel.py` | `Panel`, the layout unit, and `PanelBox`, where one sits on the sheet |
| `imposition.py` | One table per fold: reader order to (side, position) |
| `document.py` | `Brochure`: panels in, two sides out, and the proof |
| `checks.py` | The safe area and print resolution, at construction |
| `fit.py` | `overflowing_panels()`, which asks the print engine |
| `medium.py` | `BROCHURE_MEDIUM`: no regions, the `brochure/` then `document/` overlay |

## The prototype question, and its answer (#186)

A side is one `@page`; its panels are layout *inside* the page, never page breaks. So the
question the whole medium turned on was how to keep a panel's copy inside its panel. Three
layouts were measured under WeasyPrint 70, with far too much copy in one panel of a C-fold:

| Layout | What happened |
|---|---|
| Table cells in one row | The row grew and the side ran onto **five more sheets**: imposition broken |
| Absolute boxes, overflow visible | One sheet, and the copy cut off silently at the sheet's edge |
| Absolute boxes, `overflow: hidden` on a fixed-height box | One sheet, copy clipped at the panel's safe line, the neighbour untouched |

**The third, and the clip is made loud.** Each panel ends on an empty sentinel with an `id`.
WeasyPrint's public `page.anchors` records where each landed: below the safe line when copy
overflows on the sheet, and nowhere when it runs off it. `overflowing_panels()` reads both
cases and names the face. It needs `[pdf]`, so it is a function a caller runs and not a
construction check. It sees vertical overflow only. The answer was also posted on #172, as
#186 asked.

## Fold geometry

- **The tuck is a distance, not a weight.** A panel that folds inside another is a few
  millimetres narrower so it closes flat, and the allowance does not grow with the sheet. So
  the fold keeps its own arithmetic. `column_layout()` splits a content width by weights with
  gutters between; widening it with a deficit parameter would give every email a mode no email
  can reach.
- **Pinned widths**: bi-fold 528 + 528; C-fold 344 + 356 + 356 (12px, 1/8in tuck); Z-fold
  352 × 3; A4 gate 277 + 569 + 277 (7.5px, 2mm tuck, chosen so each flap is whole).
- **`panels` is derived from `kind`**, as `Medium.slots` is from its regions.
- **Whole widths are `int`**, because the size layers refuse an integral float (`356.0px`).
- **Side 2 is side 1 mirrored.** A sheet turned on its long edge puts side 1's left panel
  behind side 2's right, and one physical panel has one width. A test checks every
  imposition table against the widths by that backing rule.

## The panel

- **Its sections render against a frame one panel wide, with `pad_x` set to the inset.** Every
  container template already insets its copy by `frame.pad_x`, so the safe distance reaches
  every section and no shared template learned what a panel is. The vertical inset is the
  panel box's own padding.
- **A coloured panel makes its colour the surface its sections sit on**, by rebinding the
  theme's `surface` for the panel. Otherwise the sections' own grounds would paint white
  boxes over it, and the colour would show only in the inset strips.
- **An imaged panel makes its sections' grounds clear**, with a scoped `!important` rule in the
  brochure skeleton, because a picture has no colour to rebind to.
- **It flattens elsewhere**, byte for byte, as `Page` does. It may hold no boundary: nothing
  that holds sections, so no panel, page, slide or appendices (#317). A background image still rides the manifest in an email, unreferenced, so do not give
  one to a panel you only send by email.

## Imposition (#187)

- **Reader order is the only order the API speaks.** No argument takes a printer position.
  The text part is reader order too.
- **The C-fold table is the issue's**: side 1 is the inside flap, the back cover and the front
  cover; side 2 is the inside spread. The PDF test reads each face's position off the sheet
  against positions *written out literally*. The first version compared against `impose()`,
  which reads the table under test, and a perturbed table agreed with itself.
- **The count is the fold's**, checked at construction; the error lists every face in reader
  order. `add_section` is refused.
- **Footnotes are refused.** A note floats to a sheet's foot, which runs under three panels.
- **`proof()` returns a copy** that renders fold guides and reader labels, so
  `render_pdf(brochure.proof())` prints a proof through the unchanged exporter and the
  original can never carry the flag.

## Print preparation (#188)

- **`bleed` and `marks` on `@page`.** The trim box stays the sheet and the media box grows.
  WeasyPrint draws its marks *inside* the declared bleed, under anything painted there, so a
  ground filling the bleed hid them. The declared bleed is therefore the real bleed (12px,
  1/8in) plus a slug (24px) that the grounds never reach, and the marks sit in the slug.
- **A panel's ground is a sibling of its box**, because the box clips. It runs into the bleed
  on every trim edge: top, bottom, and the outer side of the first and last panel on a side.
  It never crosses a fold.
- **The safe area and print resolution are checked at construction, not as `constraints`.**
  #188 named them as constraints on the medium's `Constraint` protocol and also asked for both
  at construction. A `Constraint` sees only composed markup, and neither a panel's inset nor an
  image's pixel count is in it, so the done-when won, and `BROCHURE_MEDIUM.constraints` is
  empty. Resolution follows the 90 KB pattern: below `Config.print_dpi` prints a warning, and
  below half of it raises. A ground image is measured against the ground it fills.
- **CMYK is a non-goal, stated once.** `rgb-only` is an `INFO` finding, a severity that never
  fails a build, on every brochure. `print-marks` is an error when either declaration is
  missing.

## The editorial primitives (#189) — shared kit, a stated email degradation each

| Primitive | On paper | In an email |
|---|---|---|
| `PullQuote` | a tinted band with an accent rule | the same band: it needs no print feature |
| `TextBlock(drop_cap=True)` | the first letter floated, two lines deep | nothing, byte for byte |
| `FlowedColumns` | one passage through `column-count` columns | a `FullWidth`, byte for byte |
| `TextBlock(figure=ImageBlock(wrap=...))` | the image floated, the prose wrapping | the image above the prose, by its `align` |
| `Panel(background_image=...)` | a picture to the bleed | not drawn (a panel flattens) |

- **The drop cap is a real element.** A floated `::first-letter` is laid out after the first
  line in WeasyPrint, so the line ran over the letter, whether the pseudo-element sat on the
  `div` or on its first paragraph. A floated `span` wraps correctly. On paper the builder
  wraps the first visible character, or entity, before the markers are split.
- **A wrapped image is hosted by its text.** A float needs prose beside it in the same block,
  and sections are separate table rows a float cannot leave. So `TextBlock.figure` hosts it
  and `ImageBlock.wrap` names the side. The prose stays in the raw field it already was, and
  the set stays at five. A hosted figure is refused a label and notes: the document numbers
  what it walks, and it walks the text block.
- **One partial for both paged skeletons**, `document/editorial.html`, so the page and the
  brochure set copy alike.
- **`a4_editorial` exists because `a4_portrait`'s sheet counts are claims.** A pull quote put A4
  on six sheets and would have retired "a shorter page needs more sheets", the lesson #171
  recorded. The primitives get a page of their own.
- **Three things only a raster found**: a numbered list's ordinal cells shrink-wrapping on
  paper (a print engine does not map a `td`'s `width` attribute, so the titles staggered), the
  first flowed column sitting a paragraph lower than the rest, and both drop-cap failures.

## Non-goals, as decisions

No CMYK, ICC or PDF/X. No saddle-stitch or perfect-bound imposition. No dielines, die-cut,
spot UV, foil or stock metadata. Fold guides appear on a proof only. A sixth editorial
primitive is a new issue with its own case.
