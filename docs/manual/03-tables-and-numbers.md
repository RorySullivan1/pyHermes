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

## How to keep a wide table readable on a phone

Keep it to about five columns. Emails are 680 pixels wide on a desktop and 375 on a phone,
and a wide table is the first thing to overflow a phone screen. Split a wide table into two
side by side in a [`TwoColumn`](02-build-an-email.md#how-to-put-two-or-three-things-side-by-side),
or leave the detail for an attached PDF.
