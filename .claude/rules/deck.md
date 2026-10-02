---
paths:
  - "pyhermes/deck/**/*"
  - "pyhermes/builder/templates/deck/**/*"
  - "qa/fixtures/pitch_16_9.py"
  - "qa/fixtures/slide_16_9.py"
  - "tests/test_deck.py"
  - "tests/test_deck_pdf.py"
---

# The deck medium — one slide to a sheet (epic #218)

A pitchbook or a strategy review is a deck: one idea per slide, a title band and a footer
band on every slide, a slide number, divider slides, and speaker notes nobody prints. Before
#218 a "slide" was only `SLIDE_16_9`, a `PageFormat`, and content flowed from sheet to sheet
like a report. `pyhermes/deck/` is the fourth medium, beside `email`, `document` and `brochure`.

| Module | Holds |
|---|---|
| `medium.py` | `DECK_MEDIUM` and `deck_medium(page)`: two regions, the `deck/` then `document/` overlay |
| `slide.py` | `Slide`, the layout unit; `DividerSlide`, a part's title; `SlideBox`, the bands' geometry |
| `regions.py` | `TitleSlide` and `ClosingSlide`, each with an `Empty` variant |
| `document.py` | `Deck` and `DeckMetadata`: slides in, sheets numbered, notes out |
| `fit.py` | `overflowing_slides()`, which asks the print engine |

## Why a medium, and the decision it supersedes

**Superseded (#296): "A slide is a *page*, not a medium of its own."** `slide_16_9`'s docstring
said so, and `media.md` called a slide and a sheet of A4 "one medium at two pages". That held
while a slide was only a shape. A deck fails #172's test for a page preset on every count: it
needs its own skeleton (the slide frame) and slot set (title band, body, footer band; notes
outside the render), and its own constraint, because one slide is one sheet and overflow is a
finding, as a brochure panel's is. The section tree is still the content: a `Slide` holds
containers as a `Panel` does. `slide_16_9` stays as what it always was, the paged medium on a
slide-shaped sheet, and its docstring now points here.

**No PowerPoint export (#300, closed with #219 on 2026-10-01).** An exporter that walks the
section tree is a second render path over every public component, and the charts a
pitchbook is made of would still be pictures. A deck is a medium on the one HTML render path,
and it reaches a colleague as a PDF through the unchanged exporter, as a report does.

## The slide against the panel and the page

| | `Page` (paged) | `Panel` (brochure) | `Slide` (deck) |
|---|---|---|---|
| What it is | a break; its sections flow on | a fixed box on a folded side | a fixed sheet with two bands |
| Overflow | a second sheet | clipped, named by `overflowing_panels` | clipped, named by `overflowing_slides` |
| Its title | never rendered | never rendered | the title band, with an anchor |
| Elsewhere | flattens, byte for byte | flattens, byte for byte | flattens, byte for byte |

- **The slide is the layout unit; the sheet is its CSS page.** `@page` has no margin. Each
  sheet is an `overflow: hidden` box the sheet's size, with the title band, the body and the
  footer band positioned inside it, so the title band's ground can reach the edge.
- **`SlideBox` is computed from the page and the density, never passed in.** The title band
  is the page's top margin, one title line and `section_title_bottom`; the footer band is the
  bottom margin. The body is what is left, and `Deck` refuses a page whose bands leave none.
- **The body's sections render against a frame the sheet's width with `pad_x` at the page
  margin**, `_panel_scheme`'s idea: every container already insets its copy by `pad_x`, so the
  copy sits level with the title and no shared template learned what a slide is.
- **A coloured slide makes its colour the surface its sections sit on**, as a panel does, and
  rebinds the theme's ink through `on_ground` (#266), so a dark slide's title band and body
  both read light.
- **The footer band is laid out left to right whatever the slide's `align`.** A centred slide
  lost its number behind the label in the first photograph.
- **A panel refuses a slide (#317)**, by refusing anything that holds sections, as `Page`
  and `Slide` already do. Inside a brochure a slide's anchor was listed and never rendered.
- **A slide claims an anchor only on a deck**, where the title band prints it; `Deck._anchors`
  adds it, so two slides with one title are refused in `add_slide`.

## Numbering, parts and the regions (#298)

- **Every sheet is numbered in Python, the title slide included**, so the footer band, a
  `Contents` on paper and the notes agree on which slide is 4. A contents entry's page comes
  from `target-counter`, as on paper, and it agrees because every slide is exactly one sheet;
  `test_the_agenda_prints_each_entrys_sheet_as_the_footer_counts_it` reads both back.
- **The title slide carries no bands**, as a cover carries no folio. It resolves its headline
  to `campaign_name` and the line under it to `firm_name`, the reverse of the cover's, because
  a deck is titled by its subject. Its `align` defaults to left, not `BoxSurface`'s centre, so
  it sits level with every slide's title.
- **A divider is a `DividerSlide`**: its title set at `kpi_value` on `header_bg`, low on the
  sheet where a slide's body ends. The slides after it carry its title in the footer band
  until the next one. Python follows the part, not `string-set`: the label is in the markup.
- **The closing slide renders `header_disclaimer`**, `BackMatter`'s terms, so the raw-HTML set
  stays at five. It is measured for overflow like any slide.
- **Both regions are handed `deck_box`**, the derived fact the bands need, as a contents
  sheet is handed its entries; the per-region test holds each region's keys disjoint from
  `TITLE_FACTS` and `CLOSING_FACTS`.
- **A `Contents` on a slide lists every titled slide and divider but the one it sits on**,
  the paged rule of skipping its own section. An agenda slide does not list itself.
- **Footnotes are refused**: a note floats to the sheet's foot, which the footer band owns.
- **Positioned, not valign'd.** The first raster put the title slide's and the divider's copy
  at the top of the sheet, a `valign="bottom"` cell ignored, so both are absolute boxes.

## Overflow (#297)

`overflowing_slides(deck)` lays the deck out and reads each slide's closing sentinel,
`slide-N-end`, against `SlideBox.body_bottom`. **A title is measured too (#316).** The band
holds one line: the `h2` is clipped to `SlideBox.title_line`, and a sentinel ending its text,
`slide-N-title-end`, lands a line lower when it wraps, so past half a line below the first it
is named `slide N: Title (its title wraps)`. Before the fix a second line painted over the
body and the check said nothing. The brochure's measuring moved into
`pyhermes.pdf.anchor_tops`, which both fit checks share. A sentinel below the body, or on no
sheet at all, names the slide as `slide N: Title`.

The `slide-overflow` lint rule applies to the deck alone. It needs a layout, so it is not a
markup rule: `layout_findings(document)` runs it, and `lint_document`, `python -m
pyhermes.check` and `qa.preview --lint` all call it. Without `[pdf]` it is one warning saying
the deck was not measured, never a silent pass; an overflowing slide is an error, so the
check exits 1. **A deck the exporter refuses**, such as one with a hosted image, is one error
naming the exporter's reason (#315); it used to escape as a traceback from the check and from
`preview --lint`, which now reaches its own "pdf skipped" step. A deck takes the paged rules and the neutral five, and neither print rule: it
is projected or sent, never pressed.

## Notes are a third projection (#299)

`Slide(notes=...)` is plain text, never rendered. `Deck.notes()` returns one block per slide
that has notes, headed `Slide N: Title` with the sheet's number. **Notes are not part of the
text part**, because the text part is the deck as a reader reads it, and the notes are what
the presenter says over it. `artifacts()` pins them as a fourth golden for a deck,
`goldens/deck/NAME.notes.txt`, and a sentinel in the fixture's notes is asserted absent from
the HTML, the text part and the PDF's text.

## The density: `presentation`, measured (#301)

The decision #218 left open was between a new preset and `spacious`. It was made from the
fixture's PDF, read back through pypdfium2. A 1280px slide is a 960pt sheet, PowerPoint's
own 13.33in, so a size printed there compares directly with a slide's:

| Measured on the sheet | `spacious` | `presentation` |
|---|---|---|
| Body copy | 11.25pt | 15pt |
| Slide title | 24pt | 30pt |
| KPI value, divider and title-slide headline | 18pt | 33pt |
| Footer band | 7.9pt | 9.75pt |

`spacious` sets a printed report's sizes on a sheet read from a screen or across a room, so a
preset it is. `PRESENTATION_SIZES` derives from `SPACIOUS_SIZES`, raises every reader-facing
type token (a test holds each above spacious), and tightens leading because a slide is read
in lines and its height is fixed. **It is the first density one medium alone may take**:
`MEDIUM_DENSITIES` maps it to `deck`, and `check_density` refuses it on any other medium with
no switch, unlike `allow_custom_email_density`. It is also in `PRINT_DENSITIES`, so the email
gallery tests that iterate the presets pass it by. `DeckMetadata` makes it a deck's default;
any other preset is still accepted.

## The fixture

`pitch_16_9` is the gallery (`all_deck_fixtures()`, a fourth registry for
`all_brochure_fixtures()`' reason): a title slide, an agenda, two dividers, a KPI slide, a
table slide, a chart slide with notes, a two-column slide and the disclosures, every
`Slide`, `DividerSlide`, `TitleSlide` and `ClosingSlide` field away from its default. It is
photographed one image a sheet in CI's `pdf` job. `TestTheFixtureIsEngineeredRatherThanLucky`
holds that every slide fits and that a table appended to one slide is named.

## Non-goals, as decisions

No PowerPoint export, master or native chart. No animation, builds or transitions: a deck
here is a printed or sent artefact. No auto-fit or splitting of an overfull slide; the author
trims, as for a panel. No rich notes or timings.
