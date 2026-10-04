---
paths:
  - "pyhermes/builder/glance.py"
  - "pyhermes/builder/templates/analysis/trend-arrow.html"
  - "pyhermes/builder/templates/analysis/sparkline-bars.html"
  - "pyhermes/builder/templates/analysis/sparkline.html"
  - "pyhermes/builder/templates/analysis/bar-list.html"
  - "pyhermes/builder/templates/analysis/hero-stat.html"
  - "pyhermes/builder/templates/analysis/cell-bar.html"
  - "tests/test_glance.py"
  - "qa/fixtures/_glance.py"
---

# Data at a glance, drawn without images (#318)

A direction, a ranking, a short series and one large figure, each drawn from table cells and
theme tokens. An image would cost three things: Outlook blocks it by default, the plain-text
part cannot read it, and it cannot take the theme's colours. These objects cost none of them.
They are not a chart engine: there are no axes, gridlines or tick labels, and a real chart
stays a `ChartBlock` (`data-layer.md`).

## The trend arrow (#319)

`KpiItem.from_number(..., arrow=True)` draws the change's direction before the sublabel, and
`Column(arrow=True)` draws each raw figure's direction before it. `trend_of(value, fmt)` reads
it on `tone_of`'s rule: up, down, or flat for zero, `None`, NaN and a figure the format writes
as zero.

- **The direction is the number's, never the caller's.** `Card.arrow` is `init=False`, so no
  constructor takes it, and only `from_number` sets it. A tone may still be stated, because a
  rising yield can be bad news: the arrow then points up in the negative tone.
- **A shape, not a glyph, by decision (2026-10-01).** A glyph depends on the faces Outlook falls
  back to. Every client but Outlook draws a zero-size `span`: two transparent side borders and
  a coloured base make the triangle, and a 2px top border is the flat bar. The Word engine draws
  neither a transparent border nor an inline-block's width, so `[if mso]` carries a VML
  `v:shape` (a `v:rect` for flat), the CTA's route. The CSS span sits behind
  `<!--[if !mso]><!-->`, so the lint pass's Outlook rules do not judge it.
- **The probe that settled it.** Both shapes were drawn at three sizes in WeasyPrint 70 and in
  Chromium 141 before any template existed; both drew the CSS triangles and bar cleanly. No
  Outlook client is available here, so the VML half is **unverified** and belongs with #288's
  human check, beside `dir=rtl`.
- **One box token, `trend_arrow`**, the triangle's height; its base is 1.2 times it. It is a box,
  so `Spacing` refuses it.
- **The text part needs nothing.** The signed number already carries the direction (#178's
  reasoning), and a test holds a table's text byte-identical with and without arrows.
- **A table column** refuses an arrow on a text or sparkline column, and a data row with no raw
  figure. A total's raw figure takes an arrow too, since a total's change has a direction; a
  subhead never does.

## The bar list (#320)

`BarList(items, value_format, tone, diverging, title)`: a label, a bar sized to the largest
absolute value, the formatted figure.

- **It reuses the data table's cell bar** (`analysis/cell-bar.html`) and its `table_bar_height`.
  The partial gained two optional keys, `bar_color` and `reverse`; a data table passes them
  empty, so its markup is unchanged by them.
- **A layout table, not a data table.** A ranked list needs no header, rules or semantics, and
  `role="presentation"` keeps `table-role` clean. The outer table carries the `figure` hook, so
  on paper the list stays on one sheet.
- **Diverging** splits the track at a `rule_dark` centre rule. A negative fills the left half
  from the right (`reverse`), a positive the right half from the left. Without `diverging`, a
  negative is refused at construction, because a bar from zero cannot show it.
- **Tone**: an item's own, then the list's (`auto` reads each figure's sign), then the accent.
- **Spacing**: `bar_list_pad` (new, above and below each row) and `table_cell_pad` (either side
  of the bar).
- **The text part** is two aligned columns, labels left and figures right.

**The defect it found.** The cell bar carried its widths as `td width` attributes only. The
Word engine reads those, but the print engine reads only CSS, so on paper every bar of a list
printed at one length. Each cell now states its width twice, the attribute and the CSS, as
#271's column shares do. The quant fixture's bars and `kitchen_sink`'s moved with it, and
`TestOnPaper.test_a_bar_prints_at_its_share` measures the bars on a rastered sheet.

## The sparkline (#321)

`Sparkline(values, tone, highlight_last, value_format)`, `KpiItem(trend=[...])` and
`Column(kind="sparkline")` all draw a `Series`: a frozen run of figures and the format its
summary is written in.

- **Each bar is scaled to the series' own lowest and highest.** The lowest still fills
  `SERIES_FLOOR` (0.15) of the height so no bar vanishes, and a flat series fills half
  throughout. Python decides the share; the template turns it into pixels at the bound density.
- **The limit is `Config.sparkline_max`, 24.** At the standard `sparkline_bar` of 4px a bar stays
  wider than a hairline; more values are refused, naming the limit and the config field.
- **The last bar takes the series' tone and the rest the theme's rule**, so the eye lands where
  the series ends. `highlight_last=False` tones every bar. `tone="auto"` reads last against first.
- **The markup is a bar per cell, bottom-aligned.** The outer cell carries the height and
  `vertical-align: bottom` (WeasyPrint aligns only a cell with its own height, #355's probe);
  the bar is a nested table whose cell has the filled height. The gap is the next bar's left
  padding, inline and `!important`, so the mobile rule that pads every data-table cell cannot
  move it. About 280 bytes a bar; the first draft spent twice that and took the glance email
  over 90 KB.
- **The summary is the projection**: `min 3.1 · last 4.2 · max 4.2`, in the caller's format, as
  the table's `title`, the standalone line under the bars, and the plain text.
- **Three box tokens**, `sparkline_height`, `sparkline_bar` and `sparkline_gap`.
- **A table cell holds a list** only in a `kind="sparkline"` column, and that column holds only
  lists or text. A scale, a bar, an arrow or a decimal alignment on it is refused.

## The hero figure (#322)

`HeroStat(value, label, context, tone, align)` and `HeroStat.from_number(...)`: one figure for a
statement slide, a brochure's cover or an email's lead.

- **`hero_value` is a type token**, larger than `kpi_value` in every density (a test reads them
  all): 44 standard, 36 compact, 52 spacious, 30 dense, 88 presentation.
- **No border and no ground.** It sits on its section's surface, so a dark section's rebinding
  (#266) turns an untoned figure (`text.heading`) and its label and context light. A tone names
  a semantic token, which a dark ground does not rebind; the glance fixture keeps its dark-band
  figures untoned for that reason.
- **The label is not upper-cased**, unlike a card's: "2s10s" set as "2S10S" reads wrong.
- **Untoned by default in `from_number`**: one figure set alone is a statement, not a move.
- **The text part** reads `38 bps — 2s10s, steepest since 2022`.

## The fixtures (#323)

`glance_layout` (email) and `a4_glance_layout` (paged) build one set of sections
(`qa/fixtures/_glance.py`): KPI changes up, down and flat over trends, a centred hero figure, a
ten-item bar list and a diverging one, a rising, a falling and a flat sparkline, a table with an
arrow column beside a sparkline column, and two hero figures on a dark band. `pitch_16_9`'s KPI
slide draws its changes as arrows and a new last slide sets a hero figure beside a diverging
list; `tri_fold_letter` sets one under its chart. `kitchen_sink` carries a hero, a bar list and
a sparkline in one stack, and an arrow and a trend on its UST card, so every new token renders
there; it stays at 88 KB.

**What the arrow found in the size report.** `size_report` named every short comment with a
letter in it a section marker, so `<!--<![endif]-->`, the close of a downlevel-revealed block,
was one. `cta.html` always emitted it, near the foot; the arrow put one in `kitchen_sink`'s
first section, and the bare report attributed most of the body to `<![endif]`. `_MARKER` now
skips it as it skips `[if`. The sparkline also lost a table `align`: a placement attribute with
no CSS twin fails the alignment audit, and the cell around it already carries the alignment.
