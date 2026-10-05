---
paths:
  - "pyhermes/builder/models.py"
  - "pyhermes/builder/components.py"
  - "pyhermes/builder/templates/analysis/**/*"
---

# The DataTable — columns, cells, row kinds, caption and row headers

### The data table's columns

`DataTable(headers=…)` takes bare strings **or** [Column](../../pyhermes/builder/models.py) objects, mixed
freely (#117). A string coerces to a `Column` whose presentation resolves from its position —
`coerce_image`'s union-coercion, for `coerce_image`'s reason: a new capability should not cost
every existing call site a rewrite.

- **One convention was doing four jobs.** `loop.first` decided alignment, typeface and weight
  in `data-table.html` *and* the column alignment in `textgen.table()`. It was correct and
  compact; what it could not be was extended, and the tell was that a **fifth reader in
  another module** had to re-derive it so the two projections would agree.
- **The chain is cell → row → column → position**, and it runs through `kind` rather than
  straight to the position: an unset `kind` is `text` for the first column and `numeric` for
  the rest, and an unset `align` follows the *resolved kind*. So `Column("Desk", kind="text")`
  on the third column gets left alignment without saying so, which is the point of naming the
  kind at all. Unset everywhere, this reproduces `loop.first` exactly — every golden was
  byte-identical across the migration.
- **`resolved_columns()` is the single source both projections read.** The template reads the
  resolved `align` and `kind`; `textgen.table()` is *handed* the alignments rather than
  re-deriving them. Computing it twice is precisely how the HTML and the plain-text part would
  come to disagree about which column is the label — the failure epic #53 spent four issues
  preventing. A test asserts both readers against the resolution rather than against each
  other, so it cannot pass by both being wrong the same way.
- **A grep test keeps the convention from creeping back.** Re-introducing `loop.first` would
  render correctly today and quietly make `Column` unreachable, which is the failure mode a
  golden cannot see.

**Superseded (#271): "Column widths are deliberately not here."** They were held back because
they interact with the frame arithmetic `sizing.py` owns and with the mobile collapse. #271
admitted them as a **relative weight**, which touches neither: `Column(width=3)` is a share of
whatever width the table has, so no px enters the API and the frame stays `sizing.py`'s.

- **An unset column weighs 1**, and a table with no weight set emits nothing, so every golden
  but the one fixture that sets a weight stayed byte-identical.
- **The shares are whole percents, rounded by largest remainder**, so they sum to exactly 100.
- **Each share is written twice on the heading cell**, as the `width` attribute and as CSS. The
  Word engine honours the attribute and ignores the CSS. WeasyPrint does the reverse, because
  it reads presentational attributes only with `presentational_hints`, which the exporter does
  not set. The PDF test failed with the attribute alone.
- **The layout stays automatic.** A cell whose content cannot fit its share still widens it:
  a share is a preference, not `table-layout: fixed`, which the issue ruled out.
- `tests/test_table_widths.py` measures the shares in Chromium at 1000px and on a rastered
  sheet, each against an unweighted table that comes out differently.

### The data table's cells

`TableRow(cells=…)` takes bare strings **or** [Cell](../../pyhermes/builder/models.py) objects, mixed
freely (#118) — `text`, `align`, `color`, `background`. The chain completes: **cell → column →
position**, so a cell's `align` overrides what its column resolved and an unset one inherits.

- **Two index-aligned lists became one object.** `cells` and `colors` were held in step by a
  validator, which is the shape an object replaces — `LinkRow`'s reason exactly.
- **`colors` survives as the flat spelling**, as an `InitVar`: constructor-only, absent from
  `fields()`, `repr` and `==`, so the `Cell` is the single owner and the two spellings cannot
  drift. A test asserts they **converge** rather than pinning each separately. Passing both
  `colors` and a `Cell` carrying a `color` raises rather than silently picking one.
- **`Cell.color` and `Cell.background` are the fourth bounded colour exception**, and they are
  admitted as **semantic data**: the caller's claim about a *figure* — *breached its limit*,
  *stale mark*, *estimate* — of the same kind `TableRow.colors` already made. They are **not**
  a styling surface: there is no cell font, size, border or padding, and a test over
  `dataclasses.fields(Cell)` keeps it that way. A colour parameter whose justification
  evaporated would be a `title_color=` with more steps.
- **An explicit colour wins over the column's kind**, in either direction — the caller said
  something about that figure, and the theme is only the fallback behind it.
- **A cell background leaves the row's striping alone.** Marking one figure must not cost the
  caller the alternating tint on every other cell in the row.
- **Marking a cell costs zero bytes.** The template always emitted a `color` and a
  `background-color` declaration; a caller's hex simply replaces the theme's, and both are
  seven characters. The size worry the epic recorded turned out to be free.

### A cell's tone — the same claim, spelled as a word (#178)

`Cell.tone` and `Card.tone` take `positive`, `negative` or `neutral`
([Tone](../../pyhermes/builder/enums.py)), and the template resolves the word to the **live**
theme's `semantic` token at render. Before this, `theme.semantic.positive` and `negative`
rendered nowhere by default: they were tokens with no render site, so the only way a figure
turned green was a caller copying the hex out of the theme and passing it back.

- **It is not a fifth colour exception, and that is the point.** `Cell.color` is admitted
  as the caller's claim about a figure. `tone` makes the same claim with no hex in it, so
  the theme keeps its authority over what *negative* looks like. A tone validates against
  the enum, so passing `#B85450` as a tone raises and names `color` as the field for a hex.
- **The precedence is subhead, then colour, then tone, then the column's kind.** An explicit
  colour wins over a tone for the reason it wins over a kind: the caller said something
  specific about that figure. A subhead outranks both, since a row kind is chrome.
- **It resolves at render, like `Card.color`'s fallback.** A value fixed at construction
  cannot see the theme chosen at render, so a template reads `theme.semantic[tone]`.
  That pattern also makes the default path byte-identical: an untoned card reads
  `theme.semantic['neutral']`, the same value it read before.
- **A sign and a tone are different claims.** `tone_of(value, fmt)` derives one from the sign
  (up is positive), and `Cell.from_number` uses it. But a caller may state one: a rising
  yield is bad for a bond book and a falling VIX is good news, and `kitchen_sink` carries
  both. When `fmt` is given, a figure that renders as zero is neutral whatever its unrounded
  sign, so a `0.00%` is never coloured red.
- **The text projection needs nothing.** The sign already in the formatted string is the
  tone's projection, so a toned table and an untoned one project to identical text.
- **The goldens proved it rather than asserting it.** `kitchen_sink` moved its KPI strip and
  two table rows from hand-picked hexes to tones with **every golden byte-identical**, since
  the classic theme's semantic tokens are those hexes. One toned cell in `slate_theme` then
  moved one line: `#5A6068` became slate's own negative `#A8514E`. That is the first time
  `semantic.negative` has rendered anywhere in the gallery.

### The data table's row kinds

`TableRow(kind=…)` says what a row *is* (#119): `data`, `total` or `subhead`
([RowKind](../../pyhermes/builder/enums.py)). A total is ruled off above and bold across; a subhead is a
tinted label band.

- **A row's kind is chrome; a cell's colour is data.** The two land next to each other and are
  easy to conflate. A kind draws from theme tokens and takes **nothing** from the caller but
  the word, which is why it is not a fifth colour exception. They compose rather than compete:
  the row says *this is a summary*, a cell inside it still says *this figure is down*.
- **Striping counts data rows, not row indices.** A subhead in the middle of a table must not
  invert the tint of everything beneath it — the bug a naive `i % 2` ships, and a test pins the
  row *below* a subhead specifically.
- **A subhead is padded to the table's width.** One cell is the honest way to write a heading;
  making the caller spell out the empties would be ceremony. Between one and the full width is
  still a mistake and still raises. **There is no colspan in a body row** — a merged body cell
  splits badly across sheets and has no honest plain-text projection. *Superseded in part by
  #223, scoped to body rows:* the header tier below is the one place a span is admitted. The
  original line also said Outlook's Word engine handles `colspan` poorly; no render in this
  repo has checked that either way, so it is recorded as unverified rather than as fact.
- **Both kinds project in text**, which is the half most likely to be forgotten: a total gets
  a rule above it matching the header's, and a subhead gets its label alone on its own line,
  unpadded. A total indistinguishable from a data row in the text part is a total only half
  the readers can find.
- **At the default theme a subhead's tint equals `row_alt`**, because `highlight_tint` and
  `row_alt` share a value today. So a subhead reads by its weight and heading colour rather
  than by its band. That is a *theme* affordance, not a template limitation — the two tokens
  are separate precisely so a theme can pull them apart, and a house style that wants a
  stronger band does it there rather than here.

### The data table's accessible name and row headers

`DataTable(caption=…)` renders a `caption` element, and each row's label cell renders as
`th scope="row"` (#120) — finishing what #114 started with `scope="col"`.

- **A caption is the table's *name*, not a standfirst**, which is why it is a field of its own
  rather than the existing `subtitle` reused. A subtitle is copy that happens to sit above the
  table; a caption is attached to it in the markup and is what a screen reader announces on
  reaching it. Rendering the subtitle *as* the caption would have been fewer fields, moved
  every existing golden, and made shipped emails announce a standfirst where a name belongs.
  An email with several tables is where it earns its keep.
- **It is not visually hidden.** `display:none` removes it from screen readers too, defeating
  the point, and the clip-rect idiom is unreliable across email clients. It renders, and a
  caller who wants none sets none.
- **`scope="row"` follows the column's resolved `kind`, not the position.** A table whose
  first column is genuinely numeric — a rank — does not claim to head its row, which is only
  expressible because #117 made the kind a resolved value.
- **The weight had to become explicit**, and this is the one thing that would have turned a
  semantic change into a visual one: `th` is bold by default in browsers *and* in Outlook's
  Word engine, so a label cell that previously emitted no `font-weight` now emits `normal`.
  That is the third thing in #120's golden diff, and it is there to keep the render identical.

### The data table on paper — `thead`, `tbody` and rows that do not split

The header row sits in a `thead` and the rows in a `tbody` (#173), so a print engine repeats
the column headers on every sheet a table crosses. Before this, the header row was a bare `tr`
and a holdings table lost its headers after sheet one. No golden, lint rule or browser
screenshot could see that, because an email has no sheets.

- **The tags shipped alone, and the diff was checked by a script.** 48 added lines across 12
  tables, each one a bare open or close tag, with no removed lines. All 28 email screenshots
  were pixel-identical, because a browser lays out `table-header-group` in place. Two lint
  tests had counted the substring `<th`, which `thead` also starts with. They now match the
  element name.
- **The break rules live in the paged skeleton's `style` block, not in this template.**
  `document/base.html` is to the paged medium what the `@media` block is to mobile. It holds
  rules over class hooks the shared markup carries. The email never loads it, so the rules cost
  an email nothing and nothing had to be forked.
- **The only shared-markup cost is a class on the two non-data row kinds.** `row-total` and
  `row-subhead` carry no style of their own. A data row gets no class, so a table with neither
  kind is byte-identical.
- **Each rule sits on the thing that must not split:** a `tbody` row never splits mid-cell, a
  total never opens a sheet alone, and a subhead never closes one. **Nothing sits on the
  `table`.** `break-inside: avoid` on a table taller than a sheet pushes it whole onto the next
  sheet and leaves a half-empty one behind.
- **There is no `tfoot`.** A total repeated on every sheet would be false on all but the last.

### The header tier — column groups (#223)

`DataTable(groups=[ColumnGroup(label, span), …])` renders a second `thead` row above the
column heads, each group a `th scope="colgroup" colspan="n"`, so 1Y / 3Y / 5Y / 10Y sit under
one "Annualised" head instead of the unit going into the section title.

- **The span lives in the header only.** A group has an honest plain-text projection — its
  label centred over the width of its columns, on a line above the heads — where a merged
  body cell has none. That asymmetry is the whole admission, and `table-header-tier` in
  `qa/lint.py` enforces it in every medium: a `colspan` outside a `thead`, a tier whose spans
  miscount the columns, and a spanning `th` without `scope="colgroup"` each fire.
- **Every column sits under exactly one group,** and a group may cover one column. Spans that
  do not sum to the column count raise at construction; a blank label raises too, so a label
  column is given a group of its own rather than a hole. Nested tiers are out.
- **A label wider than its columns widens the last of them** in the text part, rather than
  overflowing into the neighbouring group.
- **On paper the whole `thead` repeats.** WeasyPrint repeats a table-header-group whole, so
  the tier needed no rule of its own. `a4_long_table.build_grouped()` is the same document
  with a two-row head. Both shapes run through the crossing tests and the stripped-rules
  tests. The extra row moved every engineered boundary, so the grouped variant carries its
  own lead-in counts, `GROUPED_PARAGRAPHS`, against the one-row `(13, 10, 12)`. The variant
  was `(8, 9, 11)` with groups alone. Since #226 it also carries a units row, and it is
  `(7, 8, 11)`.
- **Outlook is owed a render.** The tier ships as standard table markup. Neither the
  `outlook-html-specifications` skill nor any rules file records how the Word engine lays
  out a header `colspan`, and no Outlook render exists here (#150's posture). Until one is
  looked at, the claim stays out of this file.

### A marker in a cell or a column head (#224)

A `[^n]` written in a cell's text or a column's header joins the exhibit's `notes`, is
numbered by the document walk, and renders as the same `sup.note-ref` link a caption's marker
does. On paper its note floats to the sheet foot, and in an email it goes to the endnotes.
Either way it is the same span as a caption's marker. The text part prints `[n]` in the cell.

- **The marker in the text is the one spelling.** The stub proposed a `Cell.note` field. It was
  refused because the marker is already the apparatus's one way to say "a note is called here".
  A second spelling would be exactly the drift `Column` and `textgen` were built to end. It
  also adds no field, so `dataclasses.fields(Cell)` did not grow.
- **The notes copy is the table in reading order**: caption, source, every head, every cell.
  So `check_markers` sees a cell's marker like any other and refuses a marker with no note, a
  note with no marker, and a marker called twice, wherever the extra call sits.
- **The text part measures the spelled marker.** Heads and cells reach `textgen.table()`
  already passed through `text_markers()`, so the column is as wide as `7.2%[3]` and never as
  wide as the raw `7.2%[^2]`.
- **A field with no marker is byte-identical.** The template renders each head and cell
  through `marked()`, whose single unmarked run is `escape_html` of the text. Every golden
  held.
- **A group label carries no marker.** Add one when a real table wants it.

### A column's format is a contract (#225)

`Column(format=…, tone=…)` says once how a column's figures are written and toned. A
`TableRow` may then carry raw `int`, `float` or `Decimal` figures, and the table writes each
one through its column at construction. It calls `Cell.from_number`, the single-cell path
that already existed.

- **One string, made once, read by both projections.** The formatted `Cell.text` is what the
  markup and `text()` both print, so the two cannot format a figure differently. The raw
  figure stays beside it as `Cell.value`, because a heat scale (#227) needs the number rather
  than the string. `Cell.value` is `None` on a hand-written cell. It is `Cell`'s one new field,
  and it is data rather than styling.
- **The contract lives in the builder, and the frame adapter defers to it.**
  `table_from_frame` now puts its `formats` and `tones` mappings onto `Column`s and passes raw
  figures. It no longer formats a cell itself. So a table built by hand and one built from a
  frame take the same path, and the one-way dependency (#170) holds.
- **A string is left as written**, so a "n/a" among figures is legal. A raw figure in a text
  column with no format raises, naming the row, the figure and the column. A bool is not a
  figure.
- **Tone resolves cell, then column.** A cell's own `tone` wins, then the column's (`auto`
  reads the sign through `tone_of` with the column's format, so a `0.0%` stays neutral), then
  none. A cell's `color` and `background` survive formatting.
- **A format makes a column numeric** unless `kind` says otherwise, and `resolved()` keeps the
  format and tone (`dataclasses.replace`), so nothing downstream loses them.
- **The field-completeness test had a hole.** It compared each field with its default, and
  `DataTable` stores `groups=None` as `[]`, so an unused `groups` counted as exercised. An
  empty collection now counts as unset.

### Figures on the point, and the unit said once (#226)

`Column(align_decimal=True)` lines a numeric column up on its decimal point, and
`Column(unit="%")` prints the unit once, in a units row beneath the heads, instead of in every
cell or in the section title.

- **The padding is decided in Python, once.** `textgen.decimal_pads()` counts everything after
  a cell's last `.`, suffix included, so `4.5%` and `12.25%` compare as 2 and 3. It pads each
  cell on the right to the column's widest. `DataTable._pads()` runs it on the spelled text,
  markers as the document's numbers, and hands the counts to both readers. The template emits
  `&nbsp;` and the text part emits spaces, so a test finds one string in both. *One exception,
  found by #228's raster:* a marker in an aligned cell hangs on paper. The markup measures the
  figure with the marker removed, because a superscript is not three characters wide. The text
  part counts the spelled `[n]`. Without it, the factsheet's `11.94¹` pulled `11.93` and `12.03`
  three places left of their points.
- **A figure with no point has one before its suffix.** The issue specified "the maximum plus
  one", which is right for a bare `7` and wrong for `7%`. It would push the `%` one column
  past the point. So the virtual point sits before the trailing non-digits: the `7` stands
  over the units digit and the `%` stands in the point's column. With no suffix this is the
  issue's rule exactly. Chromium measures the glyphs at both viewports and finds them in one
  column.
- **A proportional numeric face keeps the padding**, and a test pins it under a sans `numeric`
  stack. A proportional numeric face is already the caller departing from the table's design,
  and `&nbsp;` padding in it lands *near* the point rather than on it. Dropping the padding
  would lose the alignment in the text part too, where the face does not matter.
- **A text column refuses `align_decimal`** by name. A subhead is not padded, and an empty
  cell pads by nothing.
- **The units row is a third `thead` row, so it repeats on paper.** It holds one `th` per
  column, empty where a column has no unit, set in the label face at normal weight, and not
  upper-cased, because `bps` is not `BPS`. The 2px rule moves under it. The text part prints
  the units on a line under the heads, before the rule. `table-header-tier` already counted
  any number of `thead` rows, so it needed no change.

### A heat scale and a bar, from the number (#227)

`Column(scale=HeatScale(low, high, mid=None))` tints each cell by where its raw figure sits in
the range, and `Column(bar=True)` draws each figure as a bar under it. Both read `Cell.value`
(#225), and neither takes a colour from the caller.

- **A scale is `tone`'s argument for a range.** `Cell.background` is admitted as the caller's
  claim about a figure. A scale makes the same claim from the number, with no hex in it. The
  ends are the live theme's: a figure at `low` takes `palette.surface` and one at `high` takes
  `semantic.positive`. With a `mid`, figures below it run from the surface to
  `semantic.negative`, and figures outside the range clamp to the nearer end.
- **The position is decided in Python and the colour at render.** The theme is bound at
  render, so `DataTable.context()` hands the template a position and a token name. The
  `heat_color` filter interpolates in sRGB, rounds half up and emits uppercase `#RRGGBB`, so
  a position pins one byte-exact colour: halfway from white to classic positive is `#A5BEAC`.
  `slate_theme` carries a scaled column, and its golden moved three background lines, one per
  cell, to slate's own tokens.
- **Text on a tint takes the more legible of two theme tokens.** The first raster of #228's
  fixture showed `-9.0%` in negative red on a negative-red tint, which is illegible. A scaled
  cell's text is now `text.primary` or `text.on_accent`, whichever has the higher WCAG
  contrast with the tint. The `readable_on` filter decides, at render, like the tint. That
  outranks the cell's tone, because the tint already says what the tone would. A caller's
  explicit `color` still wins.
- **Precedence: subhead, then the cell's background, then the scale, then the striping.** A
  total is chrome, so it takes neither a scale nor a bar. A data row's cell in a scaled or
  barred column must carry a raw figure or construction raises, naming the row and the cell.
  A text column refuses both.
- **A bar is a nested presentation table**, the one markup every medium shares. It has a `td`
  whose `width` attribute is the rounded percentage and whose background is
  `palette.accent`, and a remainder `td` that takes the rest. Both carry a width because auto
  layout otherwise shares an unsized row out: the first screenshot drew half a bar for a
  negative figure. A zero bar emits only the remainder. A full bar is the scale's `high`, or
  the column's largest figure when there is no scale, and a negative draws nothing (a
  diverging bar is not in this epic). The thickness is the `table_bar_height` component token,
  a box and not spacing. The mobile `@media` rule pads every `.data-table td` with
  `!important`, so the bar's cells carry `padding: 0 !important` inline, which wins over a
  stylesheet's `!important`. Changing that selector instead would have moved every email
  golden.
- **The bytes, measured on `rich_table`:** 275 for a full bar and 344 for a partial one,
  which adds the remainder cell. A table of twenty barred rows spends about 7 KB of the
  102 KB budget. `table-role` stays clean because the nested table is presentational and
  holds no `th`.
- **Neither projects to text.** The figure is the data, and its sign is already in the string
  (#178's reasoning). A test asserts the text part is byte-identical with and without a scale
  or a bar.
- **Superseded in part (#320): "the `width` attribute" alone.** The print engine reads only
  CSS, so on paper every bar printed at one length; each bar cell now carries its width in both
  spellings. `glance.md` has the measurement.

### An arrow and a sparkline in a column (#319, #321)

`Column(arrow=True)` draws each raw figure's direction before it, and
`Column(kind="sparkline")` draws a list of figures as a row of bars, its text the series'
summary. Both read raw data, as the scale and the bar do, and both are refused on a column
that cannot hold it. `glance.md` has the rest.

### A status column, drawn as dots (#326)

`Column(kind="status", statuses={"On track": "positive", "Watch": "neutral", "Breach":
"negative"})` draws a dot in each word's tone before it, the word as written; the plain text
prints the word alone. The two arguments go together, and a word the mapping does not name is
refused at construction, naming the column and the word. A subhead or an empty cell draws
no dot. The column resolves left and is set like text. Its tones are the three semantic ones;
a fourth colour is a non-goal. The dot is the badge's partial (`design-axes.md`), and a
`Cell.badge` sits after a cell's text on any column (#325).

### The proof: a factor book and the factsheet (#228)

`letter_quant_table` is the paged fixture that carries every word above: Letter portrait,
twenty strategies over two sheets, grouped heads, a units row, decimal-aligned trimmed
figures, a marker on one figure, a diverging heat scale and a bar. `SHEETS = 2` is asserted
from the PDF, the whole three-row head is read back from both sheets, the marked figure's note
is found on its sheet, and each sheet is photographed. The fund factsheet's returns table now
sets "Annualised" over the four periods, a units row of `%`, decimal-aligned raw figures and
one marker on the since-inception figure. The unit left its section title, and the table
still lays out to two sheets.

[Card](../../pyhermes/builder/models.py) is the unit: `label` (required), `value`, `color`,
`sublabel`, and an optional `body` for prose. Either `value` or `body` must be present.
`KpiItem` is a `Card` subclass that adds no fields but keeps the stricter rule — a KPI
always has a value. **`Card.body` is an HTML field**, so escaping untrusted text in it is
the caller's job, same as `TextBlock.content`.

[EmailBuilder](../../pyhermes/builder/email.py) is a thin fluent wrapper: `metadata()` initializes the
underlying `Email`, `section()` appends a container, `build()`/`render()`/`save()` are
terminal. `metadata()` must be called before `section()` or you get a `RuntimeError`. The
non-fluent `Email` class works identically.

- **The DataTable epic (#116) is complete** — #117 columns, #118 cells, #119 row kinds, #120
  the caption and row headers, #121 the fixture and these docs. Four things it leaves:
  - **A convention doing four jobs is a convention waiting to break.** `loop.first` decided
    alignment, typeface and weight in the template *and* the column alignment in
    `textgen.table()`. It was correct and compact; the tell that it could not be extended was
    that a **fifth reader in another module** had to re-derive it so the two projections would
    agree.
  - **An escape hatch survives on its justification, not its shape.** `Cell.color` and
    `Cell.background` are the fourth entry in the closed colour list and a *different kind* of
    entry: the first three name a ground the caller supplies, this one supplies none and is
    admitted as **data**. The same fields justified as "the caller wants control" would
    dissolve the palette exactly as a `title_color=` would — so the argument is written next
    to them, and a test asserts the docstring still carries it.
  - **Component fields had no completeness rule** until this epic needed one, while metadata
    fields, region fields and component *classes* all did. Worth asking, when the next axis
    lands, which of its parts is unwatched.
  - **A tag swap can be a visual change.** #120's diff is three things, not two: `th` is bold
    by default in browsers *and* the Word engine, so every label cell had to start emitting
    `font-weight: normal` or a semantic change would have bolded a column in every shipped
    email.

- **The table-semantics epic (#217) is complete.** #223 added groups, #224 markers, #225 the
  format contract, #226 decimal alignment and units, #227 the scale and the bar, and #228 the
  fixture, the factsheet and these docs. Four things it leaves:
  - **Both defects the pixels found were invisible to every other check.** A red figure on
    a red tint and a column pulled askew by a superscript were both byte-stable. Each passed
    its golden and its lint, and each was right in the text part. Standing rule 3 has now
    paid for itself on two more epics.
  - **Each "one string for both projections" claim needed an exception, and it was
    principled.** A marker is three characters in text and a superscript on paper, so the
    padding counts what each medium actually draws. The single computation holds. It takes a
    flag for the one thing a medium does differently.
  - **A tripwire should fail for the right reason, and one failed for the wrong one.**
    The field-completeness test passed on an unused `groups` because `[]` is not `None`. It
    was exactly the vacuous pass #121 wrote the rule to prevent, one level down.
  - **Every size token must render in `kitchen_sink`**, so a component token forces the
    exhaustive fixture to draw the thing it sizes. That is why `kitchen_sink` carries a bar
    and its A/B siblings moved with it. The rule held, and it was a cost worth paying.
