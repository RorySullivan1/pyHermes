# 9. Customise the layout

[Look and feel](05-look-and-feel.md) changes the whole email at once: its colours, density
and typefaces. This page covers the finer controls: moving the spacing of one section or
block, setting a house density, adding a block of your own, and replacing one of
pyHermes's own templates. It ends with what is fixed on purpose, and what to do instead.

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
colour and line spacing. Inside it:

- **These work in Outlook and Gmail alike:** `<p>`, `<b>` and `<strong>`, `<i>` and `<em>`,
  `<a href>`, `<br>`, and an inline `style=` that sets `color`, `font-weight` or
  `font-style` on a `<span>`.
- **These are not reliable in Outlook:** `padding` or `margin` on a `<div>` or `<p>`,
  borders on a `<div>`, `display:flex`, `position` and `float`. Outlook lays the email out
  with Microsoft Word, which documents only limited support for them. The check reports
  `display:flex`, `position` and `float`; it does not report padding or margins.
- **Use a block instead** for a dividing line (`Divider`, not `<hr>`, which Outlook draws at
  its own weight and colour), a boxed passage (`Callout`), a button (`Button`), or several
  blocks in one column (`Stack`).

```python
note = TextBlock(
    "<p>Spreads <b>tightened</b> for a third week. "
    '<span style="color:#7A2E2E;">High yield lagged.</span> '
    '<a href="https://example.com/credit">The credit note</a> has the detail.</p>'
)
email = EmailBuilder().metadata(facts).section(FullWidth(note, title="Credit")).build()
```

> **Note:** a subheading (`<h3>`), a bulleted list or a quotation inside a `TextBlock` is
> not yet styled from the theme. Each mail program uses its own default size and spacing.
> Styling them is tracked in [#280](https://github.com/RorySullivan1/pyHermes/issues/280).
> Until then, use a section title, or a `NumberedList` for a list.

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
| Align columns to the middle or bottom | Columns align to the top. Middle and bottom alignment has not been checked in mail programs | Keep side-by-side columns a similar length, or stack the shorter one under the longer in one column |
| Round a frame's corners | Outlook ignores rounded corners and draws square ones | Frames and callouts are square in every mail program, so they look the same in all of them |
| Use a web font | Most mail programs ignore web fonts, and the check reports a linked stylesheet | A font theme naming faces your readers have installed ([Look and feel](05-look-and-feel.md#how-to-change-the-typefaces)) |
| Use a dark theme | The email tells mail programs to show it in light mode only, and no dark palette ships | A dark band on one section: `background_color` ([Look and feel](05-look-and-feel.md#how-to-put-a-section-on-a-dark-band)) |

Only the `TextBlock` styling above has an open issue. To ask for one of these to change,
[open an issue](https://github.com/RorySullivan1/pyHermes/issues) saying which mail
programs you send to; that is what any change would have to be checked in.
