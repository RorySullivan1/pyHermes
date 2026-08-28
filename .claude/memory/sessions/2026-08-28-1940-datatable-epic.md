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

## State at end

1601 tests with a browser, 4 skipping even then. ruff / `ruff format --check` /
mypy clean. Next: #118 (`Cell`), which carries the colour decision. #120
(caption + `scope="row"`) is independent and could ship first.
