# 2. Build an email

Every email has the same four parts, top to bottom:

| Part | What it is | How you set it |
|---|---|---|
| **Strip** | A thin band of small print above everything else | `header_disclaimer` in the metadata, or `.header(...)` |
| **Masthead** | The title band: firm, campaign, date, logo | `.banner(...)` |
| **Sections** | The body of the email, one band after another | `.section(...)`, once per section |
| **Footer** | Copyright, links and legal copy | `.footer(...)` |

You only have to supply the sections. The other three are built from your metadata.

The examples on this page all start from these facts:

```python
from pyhermes.builder import EmailBuilder, FullWidth, TextBlock

facts = {
    "email_subject": "Rates Weekly: the curve steepens",
    "firm_name": "Acme Research",
    "campaign_name": "Rates Weekly",
}
```

## How to write the facts about your email

**When to use this:** every email, in `.metadata({...})`.

| Key | Required | What it does |
|---|---|---|
| `email_subject` | yes | The subject line when you send it |
| `firm_name` | yes | Who it is from. Shown in the masthead and the copyright line |
| `campaign_name` | yes | The name of the series. Shown under the firm name |
| `department` | | A team name, shown beside the campaign name |
| `date_range` | | For example `"Week ending 25 September"`, shown under the masthead |
| `issue_label` | | For example `"Issue 42"`, shown beside the date |
| `current_year` | | The year in the copyright line |
| `preheader_text` | | The preview line an inbox shows beside the subject |
| `header_disclaimer` | | Small print for the strip at the top (HTML) |
| `unsubscribe_url`, `view_in_browser_url` | | The two links in the footer |
| `theme`, `size_theme`, `font_theme` | | Colours, spacing and typefaces. See [Look and feel](05-look-and-feel.md) |
| `language` | | The language code, `"en"` unless you say otherwise |

```python
email = (
    EmailBuilder()
    .metadata({
        **facts,
        "department": "Rates Strategy",
        "date_range": "Week ending 25 September 2026",
        "issue_label": "Issue 42",
        "current_year": "2026",
        "preheader_text": "Ten-year yields rose six basis points.",
    })
    .section(FullWidth(TextBlock("<p>The curve steepened.</p>"), title="Summary"))
    .build()
)
```

> **Note:** A misspelt key stops the build with `unexpected keyword argument`, naming the
> key. Check it against this table.

## How to add a paragraph of text

**When to use this:** commentary, summaries, anything written.

**Steps:**
1. Write the text as HTML: `<p>` for paragraphs, `<b>` and `<i>` for emphasis,
   `<a href="...">` for links, `<ul>`/`<li>` for bullets.
2. Put it in a `TextBlock`, and the block in a section.

```python
from pyhermes.builder import EmailBuilder, FullWidth, TextBlock

body = TextBlock(
    "<p>Ten-year yields rose <b>six basis points</b> on the week.</p>"
    "<ul><li>Front end repriced</li><li>Long end held</li></ul>"
    '<p>Full note on <a href="https://example.com/rates">our site</a>.</p>',
    subtitle="The week in one paragraph",
)
email = EmailBuilder().metadata(facts).section(FullWidth(body, title="Summary")).build()
```

**Result:** a titled section with a smaller subtitle line, then your text.

> **Warning:** the text is used exactly as written. If any of it comes from somewhere you
> do not control, such as a spreadsheet or a database, pass that part through
> `escape_html` first so a stray `<` cannot break the layout:
>
> ```python
> from pyhermes.builder.filters import escape_html
>
> comment = "Spreads < 100bp & tightening"
> block = TextBlock(f"<p>{escape_html(comment)}</p>")
> ```
>
> Titles, labels and table cells are escaped for you. Pass those as plain text.

## How to show headline figures

**When to use this:** a row of two to four key numbers at the top of the email.

```python
from pyhermes.builder import CardGroup
from pyhermes.builder.models import KpiItem

figures = CardGroup([
    KpiItem("UST 10Y", "4.28%", sublabel="+6 bps", tone="negative"),
    KpiItem("UST 2Y", "3.91%", sublabel="-2 bps", tone="positive"),
    KpiItem("2s10s", "37 bps", sublabel="+8 bps", tone="neutral"),
])
email = (
    EmailBuilder()
    .metadata(facts)
    .section(FullWidth(figures, title="Market snapshot", highlight=True))
    .build()
)
```

**Result:** three figures side by side, each with its label above and its change below.

**Notes:**
- `tone` colours the figure: `"positive"` is green, `"negative"` red, `"neutral"` grey.
  It follows the theme's colours. Use `color="#4A7C59"` for an exact colour instead.
- `highlight=True` gives the whole section a tinted band so it stands out.
- For a list of more than four, stack them: `CardGroup([...], orientation="vertical")`.
- For a card with a sentence instead of a figure, use `Card("Label", body="<p>…</p>")`
  from `pyhermes.builder.models`.

## How to put two or three things side by side

**When to use this:** a figure beside its commentary, two tables next to each other.

```python
from pyhermes.builder import ThreeColumn, TwoColumn

side_by_side = TwoColumn(
    ratio="30-70",                       # or "50-50", "70-30"
    left=CardGroup([KpiItem("Duration", "6.2y"), KpiItem("Yield", "4.1%")],
                   orientation="vertical"),
    right=TextBlock("<p>We stay long duration into the next meeting.</p>"),
    title="Positioning",
)
three = ThreeColumn(
    ratio="33-33-33",                    # or "50-25-25", "25-50-25", "25-25-50"
    left=TextBlock("<p><b>Rates</b><br>Long duration.</p>"),
    center=TextBlock("<p><b>Credit</b><br>Neutral.</p>"),
    right=TextBlock("<p><b>FX</b><br>Short the dollar.</p>"),
    title="Views",
)
email = EmailBuilder().metadata(facts).section(side_by_side).section(three).build()
```

**Result:** on a desktop the columns sit side by side. On a phone they stack, left first.

**Proportions of your own, and four columns.** A ratio can also be a tuple of weights, one
per column, such as `ratio=(60, 40)` or `ratio=(2, 1, 1)`. `FourColumn` takes a list of four
blocks, with `None` for an empty column:

```python
from pyhermes.builder import FourColumn

email = (
    EmailBuilder()
    .metadata(facts)
    .section(TwoColumn(ratio=(60, 40), left=TextBlock("<p>The argument.</p>"),
                       right=TextBlock("<p>The evidence.</p>"), title="Sixty-forty"))
    .section(FourColumn([TextBlock("<p><b>Rates</b><br>Long.</p>"),
                         TextBlock("<p><b>Credit</b><br>Neutral.</p>"),
                         TextBlock("<p><b>Equities</b><br>Overweight.</p>"),
                         TextBlock("<p><b>FX</b><br>Short USD.</p>")], title="Views"))
    .build()
)
```

A column narrower than 90 pixels is refused, with a message giving the width your weights
produce.

## How to put several blocks in one section

**When to use this:** a paragraph, then the table it introduces, then a note, all under one
section title. Or a column of figures with a comment beneath them.

```python
from pyhermes.builder import DataTable, Stack
from pyhermes.builder.models import TableRow

returns = DataTable(["Factor", "1M"], [TableRow(["Value", "+1.8%"]), TableRow(["Momentum", "-0.4%"])])
email = (
    EmailBuilder()
    .metadata(facts)
    .section(FullWidth(
        Stack([
            TextBlock("<p>Value led again this month.</p>"),
            returns,
            TextBlock("<p>Returns are gross of fees.</p>"),
        ]),
        title="Factor returns",
    ))
    .section(TwoColumn(
        ratio="30-70",
        left=Stack([
            CardGroup([KpiItem("Duration", "6.2y"), KpiItem("Yield", "4.1%")],
                      orientation="vertical"),
            TextBlock("<p>As of Friday's close.</p>"),
        ]),
        right=TextBlock("<p>We stay long duration.</p>"),
        title="Positioning",
    ))
    .build()
)
```

**Result:** each section has one title, with its blocks one above the other. On a phone they
stay in the same order.

**Notes:**
- A `Stack` goes anywhere a single block goes: a full-width section or any column.
- Tables, charts and notes inside a `Stack` are numbered in reading order with the rest of
  the email.
- To tighten or loosen the gap, pass `spacing={"block_gap": 8}`. The same setting also
  spaces the paragraphs inside the stack's text blocks.

## How to put two things side by side inside a column

**When to use this:** a comparison that belongs inside one column of a split, or under the
paragraph that introduces it in a `Stack`.

```python
from pyhermes.builder import Columns

email = (
    EmailBuilder()
    .metadata(facts)
    .section(TwoColumn(
        ratio="30-70",
        left=TextBlock("<p>Our view in one line.</p>"),
        right=Stack([
            TextBlock("<p>Two curves compared.</p>"),
            Columns([
                CardGroup([KpiItem("UST 2Y", "3.91%"), KpiItem("UST 10Y", "4.28%")],
                          orientation="vertical"),
                TextBlock("<p>The front end fell while the long end held.</p>"),
            ], ratio=(1, 2)),
        ]),
        title="Curves",
    ))
    .build()
)
```

**Result:** the wide column holds a paragraph, then a small split sized to fit that column.
On a phone every column stacks, in order.

**Notes:** `Columns` takes two to four blocks (`None` leaves one empty) and optional weights.
It nests one level only: a `Columns` inside another `Columns` is refused.

## How to add a numbered list of ideas

```python
from pyhermes.builder import NumberedList
from pyhermes.builder.models import NumberedItem

ideas = NumberedList([
    NumberedItem("1", "Long 10Y Treasuries", "<p>Target 3.9%, stop 4.5%.</p>"),
    NumberedItem("2", "2s10s steepener", "<p>Entry at 30 bps.</p>"),
])
email = EmailBuilder().metadata(facts).section(FullWidth(ideas, title="Trade ideas")).build()
```

The `number` is text, so `"A"`, `"i"` or `"★"` work too. The body is HTML, like a `TextBlock`.

## How to sign the email and add a contact button

```python
from pyhermes.builder import AuthorBlock, ContactBlock

email = (
    EmailBuilder()
    .metadata(facts)
    .section(FullWidth(AuthorBlock("Jane Smith", job_title="Rates Strategist",
                                   email="jane.smith@example.com")))
    .section(FullWidth(ContactBlock(
        heading="Questions?",
        description="The desk is available 8am to 6pm London time.",
        cta_label="Email the desk",
        cta_url="mailto:rates@example.com",
    )))
    .build()
)
```

**Result:** a signature with a clickable address, then a button that opens a new email.

## How to quote someone

```python
from pyhermes.builder import PullQuote

quote = PullQuote("Duration is back.", attribution="Head of Rates")
email = EmailBuilder().metadata(facts).section(FullWidth(quote)).build()
```

## How to add a table of contents

**When to use this:** a long email with many titled sections.

```python
from pyhermes.builder import Contents

email = (
    EmailBuilder()
    .metadata(facts)
    .section(FullWidth(Contents(), title="In this issue"))
    .section(FullWidth(TextBlock("<p>…</p>"), title="Rates"))
    .section(FullWidth(TextBlock("<p>…</p>"), title="Credit"))
    .build()
)
```

**Result:** a linked list of every titled section, filled in for you.

## How to build sections in a loop

**When to use this:** the number of sections depends on your data.

```python
from pyhermes.builder import Email

email = Email(facts)
for region, view in [("US", "Steeper"), ("UK", "Flatter"), ("Japan", "Unchanged")]:
    email.add_section(FullWidth(TextBlock(f"<p>{view}.</p>"), title=region))
```

`Email(facts)` is the same as `EmailBuilder().metadata(facts).build()`. `add_section`
adds one section to the end.

## How to change the masthead

**When to use this:** a different title from your firm name, or a logo.

```python
from pyhermes.builder import Banner, MinimalBanner
from pyhermes.builder.images import EmailImage

logo = EmailImage.attached("logo.png", alt="Acme Research", width=120)

email = (
    EmailBuilder()
    .metadata(facts)
    .banner(Banner(title="Q3 Outlook", subtitle="What the curve is pricing", logo_url=logo))
    .section(FullWidth(TextBlock("<p>…</p>")))
    .build()
)
```

**Notes:**
- `title` defaults to `firm_name` and `subtitle` to `campaign_name`.
- `MinimalBanner(...)` takes the same arguments and draws a plain band with no
  background picture.
- `background_image_url=` puts a photograph behind the masthead. See
  [Images and charts](04-images-and-charts.md) for how to supply one.

## How to change or remove the strip at the top

```python
from pyhermes.builder import EmptyHeader, Header

with_strip = (
    EmailBuilder()
    .metadata({**facts, "header_disclaimer": "For professional investors only."})
    .header(Header(align="left"))
    .section(FullWidth(TextBlock("<p>…</p>")))
    .build()
)
without_strip = (
    EmailBuilder()
    .metadata(facts)
    .header(EmptyHeader())
    .section(FullWidth(TextBlock("<p>…</p>")))
    .build()
)
```

**Notes:** an empty strip still draws a thin band. Use `EmptyHeader()` when you want none.

## How to set the footer

**When to use this:** your legal copy, or links other than the default two.

```python
from pyhermes.builder import Footer
from pyhermes.builder.models import FooterLink, LinkRow

footer = Footer(
    disclaimer="<p>For internal use only. Not investment advice.</p>",
    link_row=LinkRow(
        copyright="2026 Acme Research",
        links=[FooterLink("Research portal", "https://research.example.com")],
    ),
)
email = EmailBuilder().metadata(facts).footer(footer).section(FullWidth(TextBlock("<p>…</p>"))).build()
```

**The two default links.** Without a `link_row`, the footer adds an **Unsubscribe** link
when you set `unsubscribe_url` in the metadata, and a **View in browser** link when you set
`view_in_browser_url`. Leave both unset, as an internal email usually would, and the footer
shows the copyright line alone. A `LinkRow` you pass is used exactly as you wrote it.

```python
email = (
    EmailBuilder()
    .metadata({**facts, "unsubscribe_url": "https://example.com/unsubscribe"})
    .section(FullWidth(TextBlock("<p>…</p>")))
    .build()
)
```

**Notes:** `disclaimer` is HTML, like a `TextBlock`. `Footer` also takes `align`,
`background_color` and `text_color`, the same as `Header`.
