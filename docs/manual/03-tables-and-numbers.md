# 3. Tables and numbers

Give pyHermes numbers, not formatted strings, and it writes them the same way everywhere:
in the table, in the figures row, and in the plain-text version of the email.

```python
from pyhermes.builder import DataTable, EmailBuilder, FullWidth
from pyhermes.builder.models import TableRow

facts = {
    "email_subject": "Factor Monitor",
    "firm_name": "Acme Research",
    "campaign_name": "Factor Monitor",
}
```

## How to show a simple table

**When to use this:** a few rows of figures you already have as text.

**Steps:**
1. List the column headings.
2. Make one `TableRow` per row, with one entry per column.
3. Put the `DataTable` in a section.

```python
table = DataTable(
    headers=["Factor", "1M", "YTD"],
    rows=[
        TableRow(["Value", "+1.8%", "+7.4%"]),
        TableRow(["Momentum", "-0.4%", "+3.1%"]),
        TableRow(["Quality", "+0.9%", "+5.2%"]),
    ],
    source="Acme Research",
    as_of="25 September 2026",
)
email = EmailBuilder().metadata(facts).section(FullWidth(table, title="Factor returns")).build()
```

**Result:** a ruled table with its first column on the left and the figures lined up on the
right. Underneath, a small line names the source and says *as of 25 September 2026*.

**Notes:** every row must have exactly as many entries as there are headings. If one does
not, the build stops and names the row.

## How to format numbers

**When to use this:** your figures are Python numbers, such as `0.0142` for 1.42%.

```python
from pyhermes.builder.formats import bps, compact, money, number, pct

pct(0.0142)               # '1.42%'
pct(0.0142, 1, sign=True) # '+1.4%'
bps(0.0006)               # '+6 bps'
money(-1200)              # '-$1,200'
money(2.5e6, currency="£")  # '£2,500,000'
compact(1_240_000_000)    # '1.2bn'
number(1234.5, 1)         # '1,234.5'
pct(None)                 # '--', for a missing figure
```

**Notes:** the second argument is the number of decimal places. Rounding is half up, so
`0.125` becomes `0.13`. For European formatting pass `thousands="."` and `decimal=","`.

## How to build headline figures from numbers

**When to use this:** your figures row comes from data, such as a level and its change.

```python
from functools import partial

from pyhermes.builder import CardGroup
from pyhermes.builder.formats import bps, pct
from pyhermes.builder.models import KpiItem

signed_pct = partial(pct, sign=True)

figures = CardGroup([
    KpiItem.from_number("UST 10Y", 0.0428, pct, change=0.0006, change_fmt=bps, good="down"),
    KpiItem.from_number("S&P 500", 5234.1, change=0.0142, change_fmt=signed_pct),
    KpiItem.from_number("VIX", 14.32, number, change=-2.18, good="down"),
])
email = EmailBuilder().metadata(facts).section(FullWidth(figures, title="Snapshot")).build()
```

**Result:** *4.28%* over *+6 bps* in red, *5,234* over *+1.42%* in green, and *14* over
*-2* in green.

**Notes:**
- The figure is written with the third argument, and the change with `change_fmt`. When you
  give no `change_fmt`, the change uses the figure's format.
- The colour follows the change: up is green and down is red. `good="down"` swaps them, for
  a yield, a spread or the VIX, where a rise is bad news.
- A change that shows as zero, such as `+0.00%`, is not coloured. With no `change`, the
  figure's own sign sets the colour. Pass `tone="neutral"` to choose it yourself.
- `Card.from_number(...)` does the same for a card, and also takes `body=`.

## How to let each column format its own figures

**When to use this:** a table of raw numbers, where every figure in a column is written the
same way.

```python
from functools import partial

from pyhermes.builder import Column

ret = partial(pct, dp=1, sign=True)
table = DataTable(
    headers=[
        "Factor",
        Column("1M", format=ret, tone="auto"),
        Column("YTD", format=ret, tone="auto"),
    ],
    rows=[
        TableRow(["Value", 0.018, 0.074]),
        TableRow(["Momentum", -0.004, 0.031]),
        TableRow(["Quality", 0.0, 0.052]),
    ],
    caption="Style factor returns",
)
```

**Result:** `+1.8%`, `-0.4%`, `0.0%` and so on, with positive figures in green and
negative ones in red. `tone="auto"` colours by sign, and a figure shown as zero is left
uncoloured.

## How to set how wide each column is

**When to use this:** a long label column squeezes the figures beside it, or a short one
leaves them spread out.

```python
table = DataTable(
    headers=[Column("Issue", width=3), "Weight", "Yield"],
    rows=[
        TableRow(["UKT 0.875% 2033", "4.2%", "4.1%"]),
        TableRow(["National Grid 2041", "1.8%", "5.3%"]),
    ],
)
```

**Result:** the first column takes 60% of the table and the other two 20% each. `width`
is a weight, not pixels: a column you leave unset weighs 1, so `3` means three times as
wide as one of those. The shares are the same in Outlook, in a browser and on paper. Leave
every `width` unset and each email client decides the widths from the content, as before.

## How to colour one cell

```python
from pyhermes.builder.models import Cell

row = TableRow([
    "High yield",
    Cell("+2.1%", tone="positive"),
    Cell("stale", color="#8A6D3B", background="#FCF8E3"),
])
table = DataTable(["Sector", "1M", "Status"], [row])
```

`Cell.from_number(-0.004, ret)` formats and colours in one step.

## How to add subtotals, a total and group headings

```python
table = DataTable(
    headers=["Sleeve", "Weight", "1M"],
    rows=[
        TableRow(["Equities"], kind="subhead"),
        TableRow(["US", "40%", "+1.2%"]),
        TableRow(["Europe", "20%", "+0.4%"]),
        TableRow(["Bonds"], kind="subhead"),
        TableRow(["Treasuries", "40%", "-0.3%"]),
        TableRow(["Total", "100%", "+0.5%"], kind="total"),
    ],
)
```

**Result:** *Equities* and *Bonds* become label bands across the table, and the total row
is ruled off and bold. A `subhead` row takes just its label.

To group columns under a shared heading, pass `groups=`:

```python
from pyhermes.builder import ColumnGroup

table = DataTable(
    headers=["Class", "1Y", "3Y", "Weight"],
    groups=[ColumnGroup("Share class"), ColumnGroup("Annualised", 2), ColumnGroup("Book")],
    rows=[TableRow(["Accumulation", "4.5%", "6.1%", "62%"])],
)
```

The number in each `ColumnGroup` is how many columns it spans, and the spans must add up
to the number of columns.

## How to add a note, a caption or small print under a table

```python
table = DataTable(
    headers=["Factor", "1M"],
    rows=[TableRow(["Value", "+1.8%"])],
    label="Exhibit",                                 # numbers it "Exhibit 1"
    caption="Style factor returns[^1]",
    notes=["Equal-weighted across quintiles."],
    source="Acme Research",
    disclosure="Returns are gross of fees. Past performance is not a guide to the future.",
)
```

**Result:** *Exhibit 1 · Style factor returns* above the table, with a note marker. Beneath
the table come the source, then the small print. The note itself is listed under **Notes**
at the end of the email.

**Notes:**
- `[^1]` marks where a note is referenced. Every marker needs a note and every note needs a
  marker, or the build stops and says which is missing.
- Exhibits are numbered for you in reading order. A `label="Chart"` numbers separately
  from a `label="Exhibit"`.
- `disclosure` is plain text. Do not put HTML in it.

## How to frame a table, or rule off its label column

**When to use this:** a comparison table whose labels should stand apart from the figures,
or a verdict table that should read as set aside from the copy around it.

```python
from pyhermes.builder import Column

table = DataTable(
    headers=[Column("Fund", rule_after=True), "Cost", "Verdict"],
    rows=[
        TableRow(["Core", "0.03%", "Buy"]),
        TableRow(["Satellite", "0.12%", "Hold"]),
    ],
    frame="dashed",
)
email = EmailBuilder().metadata(facts).section(FullWidth(table, title="Comparison")).build()
```

**Result:** a dashed frame in the theme's rule colour round the table, a cell's padding inside
it, and a darker vertical rule after the *Fund* column, from the heading to the last row.

**Notes:**
- `frame` is `"solid"` or `"dashed"`; leave it out for no frame. The same word frames a
  [section and a box](05-look-and-feel.md#how-to-put-a-frame-around-a-section).
- `rule_after=True` works on any column, and on more than one.

## How to build a table from a pandas DataFrame

**When to use this:** your figures are already in a DataFrame. Needs the `[data]` extra.

<!-- manual: needs data -->
```python
import pandas as pd

from pyhermes.data import table_from_frame

frame = pd.DataFrame(
    {"1M": [0.018, -0.004, 0.009], "YTD": [0.074, 0.031, 0.052]},
    index=pd.Index(["Value", "Momentum", "Quality"], name="Factor"),
)
ret = lambda v: pct(v, 1, sign=True)
table = table_from_frame(
    frame,
    formats={"1M": ret, "YTD": ret},
    tones={"1M": "auto", "YTD": "auto"},
    source="Acme Research",
)
email = EmailBuilder().metadata(facts).section(FullWidth(table, title="Factor returns")).build()
```

**Notes:** a named index becomes the first column. Pass `total_row=True` to treat the
last row as a total.

## How to show a trend or a ranking without a chart

**When to use this:** you want a direction, a ranking, a short series or one big number to
read at a glance, and you want it to show in Outlook with images blocked.

Each of these is drawn from table cells in your theme's colours, not from a picture, so it
needs no image, and the plain-text version of the email still says what it shows.

```python
from functools import partial

from pyhermes.builder import BarList, Column, HeroStat, Sparkline, Stack
from pyhermes.builder.formats import bps, number, pct

# An arrow on a change, and its last quarters under the figure.
figures = CardGroup([
    KpiItem.from_number(
        "UST 10Y", 0.0428, pct, change=0.0006, change_fmt=bps, good="down",
        arrow=True, trend=[0.0409, 0.0415, 0.0422, 0.0428],
    ),
    KpiItem.from_number("VIX", 14.3, partial(number, dp=1), change=-0.6, good="down", arrow=True),
])

# Top holdings as ranked bars, and contributions either side of zero.
holdings = BarList(
    [("Treasury 2034", 0.081), ("Treasury 2038", 0.074), ("Treasury 2042", 0.066)],
    value_format=partial(pct, dp=1),
    title="Top holdings",
)
contributions = BarList(
    [("Duration", 0.0042), ("Curve", 0.0018), ("Credit", -0.0009)],
    value_format=partial(pct, dp=2, sign=True),
    tone="auto",
    diverging=True,
)

# A series on its own, and one figure set large.
yields = Sparkline([3.62, 3.81, 3.66, 3.88, 3.97, 4.21], tone="auto",
                   value_format=partial(number, dp=2))
lead = HeroStat("38 bps", "2s10s", "steepest since 2022", align="center")

# Arrows and a sparkline in a table's columns.
curve = DataTable(
    headers=[
        "Tenor",
        Column("Change", format=lambda v: f"{v:+d} bps" if v else "0 bps", tone="auto",
               arrow=True),
        Column("Two years", kind="sparkline", format=partial(number, dp=2)),
    ],
    rows=[
        TableRow(["2Y", 0, [3.86, 3.91, 3.84, 3.83]]),
        TableRow(["10Y", 18, [4.00, 4.11, 4.15, 4.21]]),
    ],
)
email = (
    EmailBuilder()
    .metadata(facts)
    .section(FullWidth(Stack([lead, figures]), title="At a glance"))
    .section(FullWidth(Stack([holdings, contributions]), title="The book"))
    .section(FullWidth(Stack([yields, curve]), title="The curve"))
    .build()
)
```

**Result:** a large *38 bps* over its label; *4.28%* with a red up arrow before *+6 bps* and
eight small bars under it; bars for each holding, longest first; green bars right of a centre
line and a red one left of it; a row of bars ending in a toned one; and a table whose change
column has an arrow before each figure and whose last column is a row of bars.

**Notes:**
- The arrow's direction comes from the number's sign, never from you. Its colour is the
  figure's tone, so with `good="down"` a rising yield gets a red up arrow. A change that shows
  as zero gets a flat bar. `arrow=True` needs a `change`.
- In a table, `Column(arrow=True)` reads each cell's raw figure, so the rows must give numbers,
  not text.
- A bar list sizes every bar against its largest value. A negative value needs
  `diverging=True`. Give an item a third entry, such as `("Credit", -0.0009, "negative")`, to
  set its colour; otherwise `tone="auto"` colours each bar by its sign, and with no tone the
  bars take your theme's accent.
- A sparkline draws 2 to 24 values (`Config.sparkline_max`), each scaled to the series' own
  lowest and highest. The last bar takes the series' tone and the rest are grey; pass
  `highlight_last=False` to colour them all. In the plain text it reads
  `min 3.62 · last 4.21 · max 4.21`, written with `value_format`.
- `trend=` on a card and `kind="sparkline"` on a column take the same lists. A card's
  summary uses the figure's format when you use `from_number`.
- `HeroStat` has no box of its own. On a dark section its text turns light by itself. Use
  `HeroStat.from_number(label, value, fmt, context=...)` to write the figure from a number.
- None of these are charts: there are no axes or labels. For a real chart, use a
  [`ChartBlock`](04-images-and-charts.md#how-to-show-a-chart-with-its-source).

## How to keep a wide table readable on a phone

Keep it to about five columns. Emails are 680 pixels wide on a desktop and 375 on a phone,
and a wide table is the first thing to overflow a phone screen. Split a wide table into two
side by side in a [`TwoColumn`](02-build-an-email.md#how-to-put-two-or-three-things-side-by-side),
or leave the detail for an attached PDF.
