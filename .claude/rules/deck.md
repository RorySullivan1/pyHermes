---
paths:
  - "pyhermes/deck/**/*"
  - "pyhermes/builder/templates/deck/**/*"
  - "qa/fixtures/pitch_16_9.py"
  - "qa/fixtures/pitch_layouts_16_9.py"
  - "qa/fixtures/slide_16_9.py"
  - "tests/test_deck.py"
  - "tests/test_deck_pdf.py"
  - "tests/test_deck_layouts.py"
---

# The deck medium — one slide to a sheet (epic #218)

A pitchbook or a strategy review is a deck: one idea per slide, a title band and a footer
band on every slide, a slide number, divider slides, and speaker notes nobody prints. Before
#218 a "slide" was only `SLIDE_16_9`, a `PageFormat`, and content flowed from sheet to sheet
like a report. `pyhermes/deck/` is the fourth medium, beside `email`, `document` and `brochure`.

| Module | Holds |
|---|---|
| `medium.py` | `DECK_MEDIUM` and `deck_medium(page)`: two regions, the `deck/` then `document/` overlay |
| `slide.py` | `Slide`, the layout unit; `DividerSlide`, a part's title; `StatementSlide`, one figure; `SlideBox`, the bands' geometry |
| `regions.py` | `TitleSlide` and `ClosingSlide`, each with an `Empty` variant; `DeckFooter` |
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
  A slide's `source=` line is where its source goes instead (#347).
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

## Slide layouts (#366)

`Slide(layout="full" | "split" | "sidebar", side=[...])`: the slide's `sections` fill the main
region and `side` the other. `full` is the default and renders byte-identically.

- **`SlideBox.regions()` computes them like a split, with no px parameter.** The copy between
  the page margins, less one `gutter`, splits by the layout's weights (`LAYOUTS`: 1:1, 2:1), the
  side floored. Each region's frame reaches half a gutter past its copy on both sides, so a band
  in it has an edge to inset from and the main copy sits level with the title; the two frames
  meet at the gutter's middle.
- **Each region renders against its own frame and carries its own sentinel**: `slide-N-end` for
  the main, `slide-N-side-end` for the side. `overflowing_slides` names the slide when either
  lands past the body's foot.
- **Elsewhere it is its sections, main first.** `sections` stays the one list (main then side),
  so an email renders a laid-out slide byte for byte as the same sections in a slide, and a test
  that appends to `slide.sections` still reaches the sheet.
- **#348's image beside copy is `layout="split"` with an image section in `side`**, or it
  generalises this when it starts; that ordering is decided then. `pitch_16_9` gains a sidebar
  slide, *The view in brief*.

## Anchoring a slide's copy (#355)

`Slide(valign="top" | "middle" | "bottom")`, `DividerSlide(valign=)` and `TitleSlide(valign=)`.
`top` is a slide's default and `bottom` the divider's and the title slide's, so every golden
held with it unset. `Deck.add_slide` and `add_divider` pass it on.

- **The probe under WeasyPrint 70, recorded.** Flex auto margins are ignored: copy in a
  `display:flex` column with `margin-top:auto` stayed at the top. The `valign` attribute on a cell
  is ignored too (an unset cell sits middle, the UA default), which is the old divider comment's
  "WeasyPrint left a valign'd cell's copy at the top". CSS `vertical-align` on a cell works, but
  only when the height is on the **cell**, not the table. So an anchored body is one presentation
  table whose cell is the body's height and carries the anchor; `top` writes no such table.
- **The sentinel stays the copy's last element, inside the cell, and is a block there.** An empty
  inline span opens a line box after the copy, so bottom-anchored it landed one line above the
  foot; as a block it lands on the copy's last line, at `body_bottom` exactly. An overfull cell
  grows downward, so the sentinel still lands past the foot and `overflowing_slides` names it.
  Each region of a laid-out slide is anchored with its own sentinel.
- **The divider and the title slide** keep their positioned band for `bottom`. Higher, the band
  spans the sheet under the title band (the title slide: less a title band at each edge) and its
  cell carries the anchor.
- `pitch_16_9`'s title slide and second divider are anchored middle, and *Two positions* sits
  in the middle of its body. Its table slide carries a paragraph capped at the measure over a
  table at 0.6 of the body (#357, #358).

## Layouts (#346)

Epic #346 added six things a pitchbook needs, every one of them off by default and every
deck golden byte-identical with it unset. They live in a second fixture,
`pitch_layouts_16_9`, rather than in `pitch_16_9`, so that fixture's unchanged goldens are
the proof the defaults render byte for byte (#353's own allowance).

- **A source band (#347).** `Slide(source=, as_of=)` is one `micro` line plus `caption_gap`,
  taken from the body only on a sourced slide: `SlideBox.with_source` shrinks `body_height`,
  so `body_bottom`, and every fit check, measures against it. The line is clipped to one line
  and carries a sentinel, so a wrapping source is named `(its source wraps)`, as a title is.
  **The box became per slide**: `Deck.slide_box(slide)` is the deck's box as that slide lays
  it out, and `overflowing_slides` reads each slide's own.
- **A citation in a source resolves through the walk.** `Document._marked()` is the hook: it
  lists every holder of marked copy in reading order, components by default, and `Deck`
  interleaves each slide's source after its components. The walk hands each holder its
  `citing` and `validate` names a dangling key by its holder, `the slide titled ...`. A
  footnote marker in a source is refused at construction.
- **Pictures (#348).** `background_image=` fills the sheet under the bands and needs
  `ground="light" | "dark"`: a photograph has no one colour for `on_ground` to measure, so the
  caller names the tone and the theme is rebound as if the ground were white or black. Every
  section's ground goes clear over it, through one CSS rule the skeleton emits only when a
  slide carries such a picture. `image=` with `image_side=` takes half the sheet, floored,
  edge to edge: `SlideBox.picture` moves the copy, every band and the source into the other
  half at the same inset, and the picture is an `<img>` with `object-fit: cover`, so it keeps
  its alt text. One picture a slide, and none beside a laid-out body. Both are `IMAGE_FIELDS`
  (rule 7). **The floor is a screen's, not a press's**: one source pixel per CSS px
  (`SLIDE_DPI = 96`), below which `validate_image_resolution` warns and below half raises,
  the brochure's check with its `dpi` passed in. In an email the slide flattens and neither
  picture is drawn, as a panel's ground is not.
- **The statement slide (#349)** is a `StatementSlide` holding one `HeroStat`, centred in a
  cell the body's height on `header_bg`, the divider's ground, with the theme rebound so the
  figure reads light. No title band: `Slide.TITLE_BAND` is `False` for it and for a divider,
  so the fit check measures neither's title. Its title is a contents entry and the text part's
  heading; the sheet carries only the anchor, on the cell, so `target-counter` still finds it.
- **The divider's agenda (#350).** `Deck(divider_agenda=True)` lists every divider on every
  divider, in `font.label`, the current one in `on_dark` and the rest `on_dark_muted`, each
  with its own sheet number from `Deck.number`, the footer's count. A part's first sheet is its
  divider. The title then takes a sidebar layout's main region and the list its side, reusing
  `SlideBox.regions`; the list has a sentinel, so a deck with many parts is measured.
- **The footer (#352).** `Deck(footer=DeckFooter(counter="total", label=...))`. A
  presentation choice, so it sits beside the regions rather than in the facts. The counter is
  `str(number)` by default, which is the old `{{ number }}` byte for byte, or `N / total`,
  the total being `Deck.sheet_count()`. **The mark follows the label a gutter on**: centred
  across the band, the first raster put it against the label on a sheet a picture halves. The
  title slide has no bands, so never a mark.
- **The handout (#351)** is `Deck.handout(page)`, markup, and `pyhermes.pdf.render_handout` /
  `save_handout`. Each sheet is the deck's own sheet markup, rendered once at the deck's
  density, inside a frame the page's width between its margins, under `transform: scale()`,
  with its notes beneath in `font.body`, escaped, one paragraph per blank-line block. The
  title slide and the disclosures get a page with no notes. **Scaled markup, not a raster**:
  the issue proposed placing each laid-out sheet as an image, but WeasyPrint has written no
  image since v53, and rasterising needs pypdfium2, which is `[qa]`; the handout would then
  need two extras where the issue says it needs `[pdf]`. A scaled copy of the same markup is
  laid out identically (a test holds that every sheet's markup is in the handout verbatim),
  keeps its text selectable, and costs nothing. A `Contents` on a slide still prints the right
  numbers, because the handout is one page per sheet too. It is a view of the notes
  projection, so #299's decision covers it, and it is not a PowerPoint notes page (#300).
- **The fixture** opens on an agenda, then a divider, a full-bleed slide, an image-left and
  an image-right slide, a second divider anchored middle, a sourced table whose source cites
  the reference the last slide lists, a statement slide carrying the notes sentinel, and the
  bibliography. `tests/test_deck_layouts.py` reads each layout back from the PDF, and CI's
  `pdf` job photographs the deck and its handout one image a sheet.
