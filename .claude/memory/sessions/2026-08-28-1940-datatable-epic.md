# 2026-08-28 · DataTable epic (#116) — planning + #117

Branch `claude/review-open-issues-rr8quq`, off `main` @ `38a52da` (+#114).

## How the epic got scoped

The user asked to "build out other properties of the DataTable component" and,
asked which, chose all four candidates plus per-cell background and font
colour. That last item collides with a rule the repo closed deliberately, so
the scoping work was mostly finding the honest framing.

**The resolution: per-cell colour ships as *semantic data*, not styling.**
CLAUDE.md already says `TableRow.colors` is "the caller's statement about the
*number* ('this is down'), not a styling choice" — so per-cell **text** colour
was never an exception; it exists. The new surface is the **background**, and
it earns the same justification: a shaded cell says *breached its limit*,
*stale mark*, *estimate* — a claim about the figure.

That framing is what keeps the closed list closed. The same field justified as
"the caller wants control" would dissolve the palette exactly as a
`title_color=` would, and the epic says so in those words.

## Two findings from reading the code before filing

**`loop.first` had five readers, and one was in another module.** It decided
alignment, typeface and weight in `data-table.html` — and `textgen.table()`
re-derived the same rule *on purpose*, its docstring saying "read off the same
rule so the two projections cannot disagree about which column is the label".
A convention doing four jobs is a convention waiting to break; the tell was
that keeping it correct required a second module to copy it.

**Nothing introspects component *fields*.** `TestKitchenSinkCompleteness`
covers every public `Component` subclass and every `EmailMetadata` field, and
there are per-region field tests — but a new field on `DataTable` trips
nothing. The epic could have added seven properties that no fixture exercises
and nothing notices rotting. #121 closes it, and its criterion is that the new
test is **proved to fail** by temporarily adding a field.

## #117, as shipped

`Column(header, align, kind)` + `coerce_column`, `ColumnAlign` / `ColumnKind`,
and `DataTable.resolved_columns()`.

**The chain runs through `kind`, not straight to position.** Unset `kind` is
`text` for column zero and `numeric` after; unset `align` follows the
*resolved kind*. So `Column("Desk", kind="text")` on the third column gets
left alignment without saying so — which is the point of naming the kind at
all. Unset everywhere, it reproduces `loop.first` exactly.

**One source, two readers.** The template reads `column.align` and
`column.kind`; `textgen.table()` takes `aligns=` instead of re-deriving. The
test asserts **both readers against the resolution** rather than against each
other, so it cannot pass by both being wrong the same way.

**Every golden byte-identical**, which is what makes the claim checkable
rather than asserted.

`loop.first` is gone from the template and a grep test keeps it out —
re-introducing it would render correctly today and quietly make `Column`
unreachable, which is the failure mode a golden structurally cannot see.

## #118, as shipped

`Cell(text, align, color, background)` + `coerce_cell`; `TableRow.cells`
coerces; `colors` becomes an `InitVar`.

**The colour decision landed as a fourth entry of a *different kind*.** The
first three exceptions in CLAUDE.md's closed list each name a **ground the
caller supplies** — a section band, a photograph, the two outer boxes. This
one supplies no ground at all: it is admitted as **data**, the caller's claim
about a figure, which is the same clause that always justified
`TableRow.colors`. Writing that distinction into the list is what keeps the
rule a rule; a fourth entry arriving without its argument would turn it into
a list of exceptions, which is how such rules die.

**The size worry was free.** The epic recorded per-cell colour as a size risk
(inline styles, uncompressed gate). Measured: **zero bytes**. The template
always emitted a `color` and a `background-color` declaration — a caller's hex
simply replaces the theme's, and every hex is seven characters. Worth
remembering before pricing an inline-style feature again: the cost is in
*adding declarations*, not in changing their values.

**A dataclass detail worth not rediscovering:** an `InitVar` with a default
leaves that default on the **class**, so `getattr(row, "colors")` answers
`None` rather than raising. `EmailMetadata`'s flat region keywords behave
identically — so the test asserts what the pattern actually guarantees
(absent from `fields()`, `repr` and `==`) rather than what it looks like it
should.

Every golden byte-identical, again.

## #119, as shipped

`RowKind` (`data` / `total` / `subhead`) on `TableRow`.

**The line that keeps the epic coherent: a row's kind is *chrome*, a cell's
colour is *data*.** #118 and #119 land next to each other and are easy to
conflate. A kind draws from theme tokens and takes nothing from the caller
but the word — which is why it is not a fifth colour exception, and why the
two axes compose rather than compete (the row says *this is a summary*, a
cell inside it still says *this figure is down*).

**The bug a naive implementation ships is index-parity striping.** `i % 2`
means a subhead mid-table inverts the tint of every row beneath it. Parity
counts *data* rows, and the test pins the row **below** a subhead
specifically — the assertion that would have caught it.

**A subhead given one cell is padded to the table's width.** One cell is the
honest way to write a heading; making the caller spell out the empties would
be ceremony. Between one and the full width still raises, so a genuine
miscount is still caught.

**Found while building:** at the default theme `highlight_tint` and `row_alt`
are the *same value*, so a subhead's band is indistinguishable from an
alternating row — it reads by weight and heading colour instead. Documented
as a **theme affordance** rather than patched in the template: the two tokens
are separate precisely so a house style can pull them apart, and CLAUDE.md
already noted that distinction had been lost once before.

## State at end

1645 tests with a browser, 4 skipping even then. ruff / `ruff format --check` /
mypy clean. Every golden byte-identical across all three steps so far. Next:
#120 (caption + `scope="row"`), then #121 closes the epic.
