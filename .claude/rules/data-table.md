---
paths:
  - "svc/builder/models.py"
  - "svc/builder/components.py"
  - "svc/builder/templates/analysis/**/*"
---

# The DataTable — columns, cells, row kinds, caption and row headers

### The data table's columns

`DataTable(headers=…)` takes bare strings **or** [Column](../../svc/builder/models.py) objects, mixed
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

**Column widths are deliberately not here.** They interact with the 680px frame arithmetic
`sizing.py` owns and with the mobile collapse, so they are a separate decision with their own
client-testing burden rather than a field to slip in.

### The data table's cells

`TableRow(cells=…)` takes bare strings **or** [Cell](../../svc/builder/models.py) objects, mixed
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
([Tone](../../svc/builder/enums.py)), and the template resolves the word to the **live**
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
([RowKind](../../svc/builder/enums.py)). A total is ruled off above and bold across; a subhead is a
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
  own lead-in counts, `GROUPED_PARAGRAPHS = (8, 9, 11)`, against the one-row `(13, 10, 12)`.
- **Outlook is owed a render.** The tier ships as standard table markup. Neither the
  `outlook-html-specifications` skill nor any rules file records how the Word engine lays
  out a header `colspan`, and no Outlook render exists here (#150's posture). Until one is
  looked at, the claim stays out of this file.

[Card](../../svc/builder/models.py) is the unit: `label` (required), `value`, `color`,
`sublabel`, and an optional `body` for prose. Either `value` or `body` must be present.
`KpiItem` is a `Card` subclass that adds no fields but keeps the stricter rule — a KPI
always has a value. **`Card.body` is an HTML field**, so escaping untrusted text in it is
the caller's job, same as `TextBlock.content`.

[EmailBuilder](../../svc/builder/email.py) is a thin fluent wrapper: `metadata()` initializes the
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
