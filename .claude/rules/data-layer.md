---
paths:
  - "pyhermes/builder/formats.py"
  - "pyhermes/builder/exhibits.py"
  - "pyhermes/builder/templates/analysis/legend.html"
  - "pyhermes/data/**/*"
  - "tests/test_formats.py"
  - "tests/test_frames.py"
  - "tests/test_charts.py"
  - "tests/test_data_layer.py"
---

# The data layer — figures arrive as numbers (epic #170)

Before #170, every figure in the section tree arrived as a pre-formatted string, and every
judgement about it was the caller's: the decimal places, the sign convention, the colour
(a hex kept in the caller's own module), and the chart (a PNG rendered somewhere else). The
gap sat *above* the builder and was shared by every format — email, factsheet, brochure — so
it was filed once rather than per medium.

```
number  →  format (Python, once)  →  string      →  both projections read the string
        →  tone   (sign → word)   →  theme token →  the HTML projection colours it
```

| Piece | Where | Needs |
|---|---|---|
| Formatters (#177) | `pyhermes/builder/formats.py` | stdlib only |
| Semantic tone (#178) | `Cell.tone`, `Card.tone`, `tone_of`, `Cell.from_number` | nothing |
| DataFrame adapter (#179) | `pyhermes.data.table_from_frame` | `[data]` — pandas |
| Figure adapter (#180) | `pyhermes.data.image_from_figure`, `chart_from_figure` | `[charts]` — matplotlib |

The tone's own argument lives in `data-table.md`, beside the colour exception it extends.

### The formatters — rounding, signs and a missing figure

- **`Decimal`, half up, through `repr()`.** Finance rounds `0.125` to `0.13`. Python's
  `round()` gives `0.12` (banker's rounding) and rounds `2.675` to `2.67` (the binary float is
  `2.67499…`). Going through `repr` makes `0.0142` the decimal `0.0142` rather than the
  float's exact expansion. Swapping in `ROUND_HALF_EVEN` fails six named cases.
- **ASCII output, minus sign included.** This is #148's charset reason: a non-ASCII character
  in a plain-text field is a mojibake risk. A typographic minus would be a paged-only option,
  and nothing needs it yet.
- **Zero is never signed, and neither is a value that rounds to zero.** `pct(-0.00001,
  sign=True)` is `0.00%`. `-0.00%` would claim a direction the figure does not show.
- **`None` and NaN render as `MISSING` (`--`), overridable per call.** NaN matters because it
  is how pandas spells a missing figure. The frame adapter checks for it before calling a
  formatter, so a caller's own formatter is never handed one.
- **No `locale`.** Separators are parameters (`thousands=`, `decimal=`). A locale is process
  state, and two documents rendered in one process must not disagree about a comma.
- **`compact()` moves up a unit when rounding reaches 1,000.** `999_950` is `1m`, not
  `1,000k`. It drops trailing zeros (`340m`, not `340.0m`), which is the convention for
  magnitudes and not for returns, so `pct` keeps its zeros.
- **The module imports nothing from `pyhermes`**, and an AST test holds it to `numbers`, `decimal`
  and `typing`. It is the floor of the layer, usable without the render path, and it has no
  reason to move a golden.

### The adapters — a sibling package, and a dependency that runs one way

`pyhermes/data/` is a sibling of `pyhermes/pdf/` on the same terms: it imports the builder, the builder
never imports it, and each backend is imported inside a function, so `import pyhermes.data` works
with neither extra installed. **`pyhermes/math/` (#221) is the third sibling on exactly these
terms**: `MathBlock` takes bytes and the `[math]` extra renders them, so the purity tests cover
it both ways. `math.md` carries its decisions.

- **There is no `DataTable.from_frame` or `ChartBlock.from_figure`.** #179 and #180 asked for
  both classmethods *and* for a purity test that `pyhermes/builder` never imports `pyhermes.data`. The
  two cannot both hold, because a lazy import inside a builder method is still the builder
  importing the adapters. The purity test is what proves the extras optional, so it stayed.
  The entry points are functions in `pyhermes.data`, the shape `pyhermes.pdf.render_pdf(document)`
  already has. Appending the classmethod to `components.py` fails
  `test_no_core_module_imports_an_optional_backend_or_the_adapters[pyhermes/builder]` by name.
- **Two extras, not one.** `[data]` is pandas and `[charts]` is matplotlib. A table author
  should not install a plotting library, and a test asserts neither extra carries the
  other's backend.
- **A missing backend is a `DataError`; a frame of the wrong shape is a `ValidationError`.**
  `pyhermes.data.BackendMissingError` names the install (`pip install "pyhermes[data]"`), as
  `pyhermes.pdf`'s does. A mapping that names a column the frame lacks, `"auto"` on a text column,
  a MultiIndex or an empty frame are data problems, so they raise the builder's own error,
  naming the offending key.
- **mypy lists both spellings of each backend** (`pandas` and `pandas.*`). This is the #157
  lesson: `foo.*` matches submodules only. A test reads `pyproject.toml` and asserts both are
  there.
- **mypy *skips* the backends, not just tolerates their absence.** The first CI run of the
  `data` job failed in mypy, not in a test. matplotlib ships `.pyi` stubs, mypy followed them
  into numpy, and numpy 2.5's stubs use the 3.12 `type` statement, which a project checked at
  `python_version = "3.11"` cannot parse. It could not reproduce here at first, because numpy
  2.5 needs Python 3.12+ and this machine's default is 3.11. A 3.13 venv reproduced it
  exactly. The fix took two keys, not one: `follow_imports = "skip"` **is ignored for `.pyi`
  stubs** unless `follow_imports_for_stubs = true` is also set. numpy is listed because it
  comes in transitively. `pyhermes/data` types every backend as `Any`, so nothing is lost by
  skipping it.

### The frame adapter's inferences

- **Kinds come from dtypes.** Numeric dtypes are `NUMERIC` and everything else is `TEXT`,
  **bool included**, since `True` is not a figure.
- **A default `RangeIndex` is row numbering, not data**, so it is left out. Any other index
  becomes the row-header column. An unnamed one needs `index_label=`, because a column with
  no heading fails `Column`'s own validation.
- **An unformatted numeric column** is whole for an integer dtype and two places for a
  float. Two places is a guess, and `formats=` is how a caller corrects it.
- **The row kinds #119 shipped are reachable.** `total_row=` marks the last row, and
  `subheads=` inserts a band before an index label.
- **It never colours by hex.** Colour arrives only through `tone`, which leaves the theme
  with authority over what the colours are.

### The Figure adapter — exact pixels, and a figure left alone

- **The bytes are exactly `width × scale` pixels wide**, and the `width` attribute is the
  display width, which is the retina rule images already follow. It is pinned across figure
  widths of 6.4, 3.3 and 7.77 inches.
- **`tight=True` is opt-in, against the issue text.** A tight bounding box crops, so the
  pixel width becomes whatever the crop leaves. The issue asked for tight by default *and*
  for exact widths, and the exact width is the guarantee its own done-when pins.
- **The Figure is not modified, and no backend is selected.** `matplotlib.use("Agg")` would
  change process state under the caller. `savefig(format="png")` renders through Agg's print
  path with no display, and the tests build `matplotlib.figure.Figure` directly, with no
  pyplot at all.
- **The PNG's `Software` metadata is dropped.** Content-IDs are `sha256(bytes)[:16]`, so a
  version string in the bytes would change the cid of every chart on every matplotlib
  upgrade.
- **`CID` is the default, and `remote` is refused.** Gmail strips `DATA_URI` and the inline
  cap is 48 KB, which a 2× chart routinely exceeds. The cap's `SizeError` already names
  `attached()` as the fix. A render has no host, so `remote` cannot mean anything.
- **It never styles the plot.** A default style, a palette on the axes or a chart type is
  where a charting library would start, and #170 recorded that as a non-goal. #275 keeps it:
  see *Offered, never applied* below.

### What #170 leaves

- **Two issues asked for things that could not both be true.** Both deviations
  (`from_frame`, `tight`) were resolved in favour of the test in the issue's own done-when,
  and each commit message says so. An issue written before the code will contain such pairs,
  and the tiebreaker is whichever half has a test.
- **The goldens proved the tone rather than asserting it.** Classic's semantic tokens are
  exactly the hexes `kitchen_sink` had been passing by hand. So moving the fixture onto
  tones left every golden byte-identical, and one toned cell in `slate_theme` moved exactly
  one line, to slate's own negative. It was the first time `semantic.negative` had rendered
  anywhere in the gallery.
- **A pipe hid a red suite once.** `pytest | tail -1 && git commit` committed with a failing
  prose-budget test, because `tail` exits 0. The commit was amended before anything was
  pushed. Gate a commit on `set -o pipefail`, or on pytest's own exit code.


## Figures, charts and pictures without hand-work (#273)

**A headline figure takes a number (#274).** `Card.from_number(label, value, fmt, *, change,
change_fmt, tone, good, body)` is `Cell.from_number` for the figures row, and `KpiItem`
inherits it. The tone reads the sign of the *change*, or of the value when there is none,
through `tone_of`, so a change written as zero is never coloured. `good="down"` flips it,
which is the case the README wrote by hand for a yield or the VIX. `change_fmt` falls back to
`fmt`. The tests cover each sign under each `good`, and that the HTML and the text part print
the same strings.

**Offered, never applied (#275).** `pyhermes.data.chart_style(theme, font_theme, *, role)`
returns a `ChartStyle`: a `dict` of matplotlib `rc` settings for `plt.rc_context`, with
`positive`, `negative` and `series` as attributes, because `rc_context` refuses keys it does not
know. The colour settings are listed in `RC_TOKENS`, each with the theme token it reads, and a
test holds that `slate` differs from `classic` exactly where those tokens do. The font list
keeps only the families `font_manager.findfont` resolves without falling back, then the
stack's generic family, so a missing Georgia produces no warning. `chart_from_figure` is
untouched, and nothing changes outside the context.

**The series colours moved to the builder (#337)**, as `theming.SERIES_TOKENS` and
`chart_colors(theme)`, because a `Legend` names them and the builder may not import the
`[charts]` layer; `pyhermes.data.style` re-exports the tokens and builds `series` from the one
function, so the cycle and the key cannot disagree about order.

**The legend never styles the plot (#337).** A chart's key drawn into the picture is lost when
Outlook blocks images, its default, and in the plain-text part. `Legend(entries)` states it
again in markup: a swatch, a shaded inline box the status dot's size, then the label, and
`Key: 10Y gilt, 2Y gilt` in the text. Each `LegendEntry` names its colour one way: a `tone`, a
`series` (an index into `chart_colors`, what `chart_style` cycles), or a `color` hex that must
be one of the theme's chart colours. **The key and the picture agree because both read the
theme, never because the legend reads the chart.** Reading colours out of a matplotlib figure
would make the builder depend on the `[charts]` extra the dependency rule forbids, and would
key whatever the caller happened to draw rather than what the theme says a series is. So the
caller draws inside `chart_style` and names series by number, and the two match by
construction; a caller who styles the plot by hand keeps the job of matching it.

- **A hex is checked against the document's theme in `add_section`**, the precedent the
  email's `valign` refusal set (#356), because only the document knows its theme; the entry
  itself checks the shape at construction. A hex outside the chart colours, or a `series` past
  the end of a cycle whose tokens coincide, is refused there by name. So the palette stays
  closed, and a theme switch that orphans a hex fails loudly rather than keying a colour the
  picture cannot contain. `series` and `tone` recolour with the theme; prefer them.
- **No line-style or marker swatch, and nothing drawn on the image**, by the epic's decision.
- **The Word engine shades the swatch's non-breaking space**, a square, as it does the status
  dot (#326), and drops an inline box's margin, so a space in an mso conditional stands in for
  the gap after the swatch; unverified in a real Outlook here, so it joins #288's check.

**A picture far wider than it is shown warns (#276).** `EmailImage.__post_init__` reads the
pixel width with `pixel_size` and raises a `SizeWarning` through `warn_caller` when it is
over `Config.oversize_image_ratio` times the display `width`. Hosted images and ones with no
`width` are not checked. **The default is 4.5, not the issue's 3, and that was measured:** at 3
the package's own output warned. An equation renders at 4x (`DEFAULT_MATH_SCALE`, so one render
serves paper), and the paged and brochure fixtures' pictures sit at about 3.1x, the 300 dpi
`print_dpi` asks for. The warning names both targets, 2x for a screen and 3.125x for print.
Every gallery renders with no `SizeWarning`, asserted.
