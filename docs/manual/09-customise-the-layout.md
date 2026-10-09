# 9. Customise the layout

[Look and feel](05-look-and-feel.md) changes the whole email at once: its colours, density
and typefaces. This page covers the finer controls: moving the spacing of one section or
block, placing blocks on a phone, on paper and in one medium only, positioning a block in the
room it has, setting a house density,
adding a block of your own, and replacing one of pyHermes's own templates. It ends with what
is fixed on purpose, and what to do instead.

```python
from pyhermes.builder import EmailBuilder, FullWidth, TextBlock

facts = {
    "email_subject": "Morning Note",
    "firm_name": "Acme Research",
    "campaign_name": "Morning Note",
}
```

## How to tighten or loosen one section

**When to use this:** one section needs less (or more) room than the density gives it, and
the rest of the email should stay as it is.

**Steps:** pass `spacing=` to the section or the block, naming the spacing it should move.

```python
from pyhermes.builder import DataTable, Spacing
from pyhermes.builder.models import TableRow

tight = FullWidth(
    TextBlock("<p>Markets opened higher.</p>"),
    title="Overnight",
    spacing={"content_top": 6, "content_bottom": 6},
)
curve = DataTable(
    headers=["Tenor", "Yield"],
    rows=[TableRow(["2Y", "4.10%"]), TableRow(["10Y", "4.28%"])],
    spacing=Spacing(table_cell_pad=3),
)
email = (
    EmailBuilder()
    .metadata(facts)
    .section(tight)
    .section(FullWidth(curve, title="Curve"))
    .build()
)
```

**Result:** the Overnight section sits closer to its neighbours, and the table's cells are
tighter. Every other section and block keeps the density's spacing.

`spacing=` takes a plain mapping or a `Spacing(...)`; the two are the same. Values are
pixels. Each section or block moves only the spacing it reads itself, so to tighten a table
inside a section, give the `spacing=` to the table.

> **Note:** three kinds of name are refused, each with a message saying why: a name the
> object does not use, a width (`width`, `margin` and the others belong to the page), and in
> an email the names the phone layout reads (`pad_x`, `card_pad_x`, `card_pad_y`,
> `mobile_pad_x`, `mobile_pad_y`, `table_cell_pad_mobile`). The phone layout reads the
> whole email's density, so moving one of these for a single section would make it look
> different on a desktop and on a phone. Move them for the whole email with a house density
> instead.

## How to see which spacing a block takes

Each section and block lists the spacing it reads in `SPACING_TOKENS`:

```python
from pyhermes.builder import CardGroup

print(FullWidth.SPACING_TOKENS)
print(DataTable.SPACING_TOKENS)
print(CardGroup.SPACING_TOKENS)
```

```text
('section_title_top', 'section_title_bottom', 'content_top', 'content_bottom', 'pad_x')
('table_cell_pad', 'caption_gap', 'subtitle_gap')
('card_pad_y', 'card_pad_x', 'kpi_pad_y', 'kpi_pad_x', 'card_label_gap', 'card_value_gap', 'caption_gap', 'subtitle_gap')
```

A name outside an object's list is refused when you build it, so a typo cannot quietly do
nothing.

## How to set a house density

**When to use this:** every email in a series should be a little tighter or looser than a
preset, in the same way.

**Steps:**
1. Derive from the nearest preset, naming only what changes. `space` holds the gaps and
   paddings, `type` the type sizes and line spacing, and `component` the sizes particular
   to one kind of block.
2. Render it in the mail programs you send to, and check it on a phone.
3. Allow it with `Config(allow_custom_email_density=True)`. An email refuses a density of
   your own until you do, because nobody has yet checked it in a mail program.

```python
from pyhermes.builder import COMPACT_SIZES, Email
from pyhermes.config import Config

house = COMPACT_SIZES.derive(space={"block_gap": 10, "content_top": 12})
email = Email(
    {**facts, "size_theme": house},
    config=Config(allow_custom_email_density=True),
)
email.add_section(FullWidth(TextBlock("<p>Markets opened higher.</p>"), title="Overnight"))
html = email.render()
```

**Result:** the email is compact, with wider gaps between blocks and above each section's
content.

> **Tip:** if your program loads its settings from the environment with
> `set_config(Config.from_env())`, setting `PYHERMES_ALLOW_CUSTOM_EMAIL_DENSITY=1` allows it
> for every email the program builds.

A printed report takes any density without the switch, because nothing about a page depends
on a mail program. See [Reports and PDFs](07-reports-and-pdfs.md).

## How to add a block pyHermes does not have

**When to use this:** you need a kind of block that pyHermes does not ship, such as an
analyst's rating, and you want it to follow the theme like the built-in blocks.

**Steps:**
1. Write its template in a folder of your own. Read colours from `theme`, sizes from `size`
   and typefaces from `font`, so the block follows the email's settings. Escape every value
   with `| escape_html`.
2. Subclass `Component`. Give it a `template_path` inside that folder, a `context()` that
   returns every value the template reads, and a `text()` for the plain-text part.
3. Pass the folder as `template_overlay=` when you build the email.

```python
from pathlib import Path

from pyhermes.builder import Component

templates = Path("house_templates")
(templates / "house").mkdir(parents=True, exist_ok=True)
(templates / "house" / "rating.html").write_text(
    """<table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:0 0 {{ size.space.block_gap }}px 0; font-family:{{ font.label }};
               font-size:{{ size.type.label }}px; line-height:{{ size.type.secondary_line | percent }};
               color:{{ theme.palette.accent }};">
      {{ call | escape_html }} &middot; {{ ticker | escape_html }}
    </td>
  </tr>
</table>
""",
    encoding="utf-8",
)


class Rating(Component):
    """An analyst's call on one name."""

    template_path = "house/rating.html"

    def __init__(self, ticker: str, call: str):
        self.ticker = ticker
        self.call = call

    def context(self):
        return {"ticker": self.ticker, "call": self.call}

    def text(self):
        return f"{self.call}: {self.ticker}"


email = (
    EmailBuilder(template_overlay=templates)
    .metadata(facts)
    .section(FullWidth(Rating("ACME", "Overweight"), title="Our call"))
    .build()
)
```

**Result:** "Overweight · ACME" in the theme's label face and accent colour, and
`Overweight: ACME` in the plain-text part.

Run the check on any block you write, because it is your markup and not pyHermes's:

```python
from pyhermes.check import check, errors

assert errors(check(email)) == []
```

> **Note:** keep a block's layout in tables, as the template above does. Every table that
> is only there for layout needs `role="presentation"`, and the check reports one without
> it. Inline `style=` on a table cell is what Outlook honours. `display:flex`, `position`
> and `float` are not, and the check reports them.

## How to change one of pyHermes's own templates

**When to use this:** one built-in part needs different markup, such as a footer laid out to
your firm's legal template, and no setting covers it.

**Steps:** copy the packaged template to the same path inside your own folder, edit the
copy, and pass the folder as `template_overlay=`. pyHermes looks in your folder first, so
your copy replaces its own and every other template is unchanged.

```python
from importlib.resources import files

packaged = files("pyhermes.builder") / "templates" / "regions" / "footer.html"
(templates / "regions").mkdir(exist_ok=True)
(templates / "regions" / "footer.html").write_text(
    "<!-- house footer -->\n" + packaged.read_text(encoding="utf-8"),
    encoding="utf-8",
)
email = (
    EmailBuilder(template_overlay=templates)
    .metadata(facts)
    .section(FullWidth(TextBlock("<p>Markets opened higher.</p>")))
    .build()
)
```

**Result:** the email renders your footer. `template_overlay=` also takes a list of folders,
searched in order.

> **Warning:** a replaced template does not change when you upgrade pyHermes. After an
> upgrade, compare your copy with the new packaged one, and render a test email before you
> send.

## What raw HTML in a TextBlock can do

`TextBlock` takes HTML, and the theme styles the paragraph around it: its typeface, size,
colour and line spacing. The same holds for a card's `body` and a numbered item's `body`.
Inside them, these tags take the theme's styles too:

| Tag | Styled as |
|---|---|
| `<h3>` | A subheading: the heading typeface and colour, a little smaller than the section title |
| `<h4>` | A minor heading: the heading typeface, body size, bold |
| `<ul>`, `<ol>`, `<li>` | Lists, indented the same way in every mail program, with a small gap between items |
| `<blockquote>` | A quotation: italic, in the theme's secondary colour, with a rule in the accent colour beside it |
| `<a href>` | A link: the accent colour, underlined. On a dark section band, the band's text colour |
| `<hr>` | A thin line in the theme's rule colour |

A tag you give your own `style=` keeps it, and pyHermes adds nothing to it. Changing the
theme, the density or the typefaces moves all of these with the rest of the email, and
`spacing=` on the block moves the list indent (`prose_indent`), the gap after a heading,
list or quotation (`prose_gap`), and the gap between list items (`prose_item_gap`).

`<h1>` and `<h2>` are refused when the block is built, because the section title is the
heading at that level. Use `<h3>`, or start a new section with its own title.

- **These work in Outlook and Gmail alike:** the tags above, `<p>`, `<b>` and `<strong>`,
  `<i>` and `<em>`, `<br>`, and an inline `style=` that sets `color`, `font-weight` or
  `font-style` on a `<span>`.
- **These are not reliable in Outlook:** `padding` or `margin` on a `<div>` or `<p>`,
  borders on a `<div>`, `display:flex`, `position` and `float`. Outlook lays the email out
  with Microsoft Word, which documents only limited support for them. The check reports
  `display:flex`, `position` and `float`; it does not report padding or margins.
- **Use a block instead** for a dividing line between sections (`Divider`), a boxed passage
  (`Callout`), a button (`Button`), or several blocks in one column (`Stack`). Outlook draws
  an `<hr>` at its own weight, so a `Divider` is the line that looks the same everywhere.

```python
note = TextBlock(
    "<h3>Credit</h3>"
    "<p>Spreads <b>tightened</b> for a third week. "
    '<span style="color:#7A2E2E;">High yield lagged.</span></p>'
    "<ul><li>Investment grade: 4bp tighter</li><li>High yield: 2bp wider</li></ul>"
    '<p><a href="https://example.com/credit">The credit note</a> has the detail.</p>'
)
email = EmailBuilder().metadata(facts).section(FullWidth(note, title="Markets")).build()
```

To restyle one of these tags for every email you build, copy the packaged
`text/prose-styles.html` into your own folder, edit its line for that tag, and pass the folder
as `template_overlay=` ([above](#how-to-change-one-of-pyhermess-own-templates)). Each tag
must keep its line.

## How to choose the order columns stack in on a phone

**When to use this:** a split puts text on the left and a chart on the right, and on a phone
the reader should meet the chart first.

**Steps:** pass `stack="reverse"` to the split.

```python
from pyhermes.builder import ChartBlock, TwoColumn

chart_first = TwoColumn(
    "30-70",
    left=TextBlock("<p>The long end did the work this quarter.</p>"),
    right=ChartBlock("https://example.com/curve.png", alt_text="Gilt curve"),
    title="The curve",
    stack="reverse",
)
```

**Result:** on a desktop the split looks exactly as before. On a phone the right-hand column
comes first. `TwoColumn`, `ThreeColumn`, `FourColumn` and a `Columns` inside a cell all take
it. Outlook on a desktop never stacks, so it shows the desktop order. On paper and in the
plain-text part the columns keep the order you wrote them in.

## How to keep two small columns side by side on a phone

**When to use this:** two figures, or a label and its value, would each fill a whole row on a
phone although both fit side by side.

**Steps:** pass `stack=False`.

```python
from pyhermes.builder import CardGroup, Columns, Stack
from pyhermes.builder.models import KpiItem

figures = TwoColumn(
    "50-50",
    left=CardGroup([KpiItem("10Y gilt", "4.21%")], orientation="vertical"),
    right=CardGroup([KpiItem("2s10s", "38 bps")], orientation="vertical"),
    stack=False,
)
label_and_value = FullWidth(
    Columns(
        [TextBlock("<p>Modified duration</p>"), TextBlock("<p>6.8 years</p>", align="right")],
        ratio=(3, 2),
        stack=False,
    )
)
```

**Result:** the columns keep their proportions down to a 375px phone screen.

> **Note:** a split too wide to fit is refused when you build it, naming its narrowest
> column's width on a 375px screen. Four equal columns are too narrow; two equal ones fit.
> Give the narrow column more weight, or let it stack.

## How to keep a section on one sheet, or start it on a new one

**When to use this:** in a report, a short section should not break across two sheets, or a
section should open a fresh sheet.

**Steps:** pass `keep_together=True` or `break_before=True` to the section.

```python
from pyhermes.document import PagedDocument

report = PagedDocument({"firm_name": "Acme Research", "campaign_name": "Morning Note"})
report.add_section(FullWidth(TextBlock("<p>Rates rose.</p>"), title="Summary"))
report.add_section(
    FullWidth(TextBlock("<p>The detail.</p>"), title="Detail", keep_together=True)
)
report.add_section(
    FullWidth(TextBlock("<p>What we would do.</p>"), title="Outlook", break_before=True)
)
```

**Result:** *Detail* moves whole to the next sheet if it would otherwise break, and
*Outlook* starts a sheet of its own. Unlike a `Page`, neither wraps anything else.

> **Note:** both are paper's. In an email they add nothing, not even a byte. A brochure panel
> and a slide refuse them, because neither ever breaks. A kept section taller than a sheet
> cannot be kept, so printing it warns, naming the section.

## How to show a block or a section in one medium only

**When to use this:** one set of sections makes both an email and a report, and some content
belongs to one of them: a *Download the PDF* button for the email, a note about the printed
edition for the report.

**Steps:** wrap a block in `Only`, or a list of sections in `OnlySections`, naming the media
it shows in: `"email"`, `"document"`, `"brochure"`, `"deck"` or `"html"`.

```python
from pyhermes.builder import Button, Only, OnlySections

def sections():
    return [
        FullWidth(
            Stack([
                TextBlock("<p>The full note has the tables.</p>"),
                Only(Button("Download the PDF", "https://example.com/note.pdf"), media="email"),
            ]),
            title="Read the full note",
        ),
        OnlySections(
            [FullWidth(TextBlock("<p>This printed edition carries the tables.</p>"),
                       title="About this edition")],
            media="document",
        ),
    ]

email = EmailBuilder().metadata(facts)
for section in sections():
    email.section(section)
email = email.build()
printed = PagedDocument({"firm_name": "Acme Research", "campaign_name": "Morning Note"})
for section in sections():
    printed.add_section(section)
```

**Result:** the email shows the button and not the note; the report the reverse. What is
left out leaves out everything: its markup, its images from the attachments, its text from the
plain-text part and its title from any contents list.

> **Note:** a numbered exhibit, a footnote or a citation inside either wrapper is refused,
> because leaving it out of one medium would number the rest differently there. Keep it
> outside, or drop its label. In a column, a block left out leaves the column empty; to drop
> a whole band, use `OnlySections`.

## Position blocks

**When to use this:** a block has more room than it needs. A short table spans a whole slide,
a cover title should sit low on its panel, a figure should sit level with the middle of the
commentary beside it, or a paragraph runs too wide on a landscape sheet.

**Steps:** each control is a word or a share, never a size in pixels.

- **Anchor copy in a fixed box:** `valign="top"`, `"middle"` or `"bottom"` on a brochure
  `Panel`, a deck `Slide`, `DividerSlide` or `TitleSlide`.
- **Align a split's columns on paper:** `valign=` on `TwoColumn`, `ThreeColumn`, `FourColumn`
  or `Columns`.
- **Make a table, figures, callout or contents list narrower:** `width=` from 0.3 to 1.0, a
  share of its column. The section's `align` places it.
- **Set how long a line of prose may run:** `TextBlock(measure="narrow")`, or `"full"` for no
  limit. Reports, brochures and decks use `"standard"` unless you say otherwise; an email uses
  none.
- **Float a chart or an equation beside prose on paper:** give it `wrap="left"` or
  `"right"` and a width, and pass it as the text's `figure`, as for an image.

```python
from pyhermes.builder import Callout, ChartBlock, TwoColumn
from pyhermes.builder.images import EmailImage

FLOAT_WIDTH = 160  # the floated chart's own width beside the prose, in px

chart = ChartBlock(
    EmailImage.hosted("https://example.com/premium.png", alt="Term premium", width=FLOAT_WIDTH),
    wrap="right",
)
report = PagedDocument({"firm_name": "Acme Research", "campaign_name": "Morning Note"})
report.add_section(
    TwoColumn(
        "30-70",
        left=TextBlock("<p><strong>61 bps</strong></p>"),
        right=TextBlock("<p>The premium explains most of the move at the long end.</p>"),
        valign="middle",
    )
)
report.add_section(
    FullWidth(
        Callout(TextBlock("<p>The premium moved the long end.</p>"), width=0.6),
        align="center",
    )
)
report.add_section(
    FullWidth(TextBlock("<p>Rates rose for a third quarter.</p>", figure=chart, measure="narrow"))
)
```

**Result:** the short figure sits level with the middle of its commentary, the callout takes
60% of its column in the centre, and the prose wraps round the chart, no wider than the
narrow measure.

> **Note:** an email refuses `valign` on a split, naming why: mail programs have not been
> checked aligning columns other than at the top. In an email a floated chart sits above the
> prose, placed by its own alignment, and a measure is written only where a column is wider
> than it, so an email that sets none gains no byte. None of these change the plain-text part.

## What you cannot change, and what to do instead

These limits are deliberate. Each was decided because the alternative breaks in a mail
program, or would let one email drift from the rest of its series.

| You cannot | Because | Instead |
|---|---|---|
| Change the email's width from 680px | Every column width, image width and phone layout is worked out from it, and only this width has been checked in mail programs | For a different width, print the content as a report. Its page size is a setting ([Reports and PDFs](07-reports-and-pdfs.md)) |
| Give one block its own colours | A theme is the email's palette. One-off colours are how a series drifts off brand | Derive a house theme ([Look and feel](05-look-and-feel.md#how-to-use-your-firms-colours)). For one section: `background_color`, `text_color`, `highlight=True` or a `Callout` tone |
| Give one block its own type size or typeface | Sizes come from the density and faces from the font theme, so a heading means the same size everywhere | A house density, or a house font theme ([Look and feel](05-look-and-feel.md#how-to-change-the-typefaces)) |
| Write padding in pixels, such as `"4px 8px"` | Spacing is named, so a density change moves it, and a name the block ignores is caught | `spacing=` with the block's spacing names (above) |
| Put a margin between sections | Outlook drops a margin on a table cell. The space between sections is padding | `spacing={"content_top": ..., "content_bottom": ...}` |
| Align an email's columns to the middle or bottom | Columns align to the top in an email. Middle and bottom alignment has not been checked in mail programs | On paper, `valign=` ([above](#position-blocks)). In an email, keep side-by-side columns a similar length |
| Round a frame's corners | Outlook ignores rounded corners and draws square ones | Frames and callouts are square in every mail program, so they look the same in all of them |
| Use a web font | Most mail programs ignore web fonts, and the check reports a linked stylesheet | A font theme naming faces your readers have installed ([Look and feel](05-look-and-feel.md#how-to-change-the-typefaces)) |
| Use a dark theme | The email tells mail programs to show it in light mode only, and no dark palette ships | A dark band on one section: `background_color` ([Look and feel](05-look-and-feel.md#how-to-put-a-section-on-a-dark-band)) |

To ask for one of these to change,
[open an issue](https://github.com/RorySullivan1/pyHermes/issues) saying which mail
programs you send to; that is what any change would have to be checked in.
