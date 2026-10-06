# 5. Look and feel

Three settings change how the whole email looks: **colour**, **density** (how much space
everything takes) and **typeface**. Each is one key in the metadata, and each can be a
ready-made preset or your own. You never set a colour or a font size on a single block.
That keeps every email in a series consistent.

To move the spacing of one section or block, add a block of your own, or see which limits
are deliberate, read [Customise the layout](09-customise-the-layout.md).

```python
from pyhermes.builder import EmailBuilder, FullWidth, TextBlock

facts = {
    "email_subject": "Morning Note",
    "firm_name": "Acme Research",
    "campaign_name": "Morning Note",
}
body = FullWidth(TextBlock("<p>Markets opened higher.</p>"), title="Overnight")
```

## How to change the colours

**Steps:** pick a preset with `"theme"`.

```python
email = EmailBuilder().metadata({**facts, "theme": "slate"}).section(body).build()
```

| Preset | Looks like |
|---|---|
| `"classic"` (the default) | Dark slate masthead, warm grey background, teal accents |
| `"slate"` | Cooler blue-grey throughout |

## How to use your firm's colours

**When to use this:** your firm has brand colours the presets do not match.

```python
from pyhermes.builder import DEFAULT_THEME

house = DEFAULT_THEME.derive(palette={"header_bg": "#003366", "accent": "#C8102E"})
email = EmailBuilder().metadata({**facts, "theme": house}).section(body).build()
```

**Result:** the masthead turns navy, and the line beneath it, the footer links and the
contact button turn red. Everything you did
not name keeps the preset's colour.

The colours you can name in `palette`:

| Name | Where it shows |
|---|---|
| `header_bg` | The masthead band |
| `accent` | The line under the masthead, footer links, the contact button, list numbers |
| `wrapper_bg` | The background around the email |
| `surface` | The email's own background |
| `highlight_tint` | A `highlight=True` section |
| `row_alt` | Alternate table rows |
| `rule`, `rule_subtle`, `rule_dark` | Dividing lines, from medium to faint to strong |

Colours are always written `#RRGGBB`, such as `#003366`. Names like `navy` and short forms
like `#036` are refused.

> **Tip:** define `house` once in a shared module and import it into every script, so the
> whole series stays on brand.

## How to add brand tones

**When to use this:** a box, a badge or a figure should be in a brand colour, not in green,
red or grey, which say gain, loss and neither.

```python
from pyhermes.builder import Callout

branded = DEFAULT_THEME.derive(tones={"brand": "#B8860B", "sky": "#0077A8"})
facts_box = FullWidth(Callout(TextBlock("<p>0.03% a year.</p>"), tone="brand", label="Cost"))
email = EmailBuilder().metadata({**facts, "theme": branded}).section(facts_box).build()
```

**Result:** the box takes a light gold tint and a gold frame. A tone name works anywhere a
`tone=` does: a `Callout`, a `Badge`, a card, a table cell, a status column, a bar, a hero
figure, a fact and a chart key. `positive`, `negative` and `neutral` keep their colours.

A name is a lowercase word, and it may not be `positive`, `negative` or `neutral`; to change
those, set `semantic`. A tone the theme does not declare is refused when its section is added,
and the message lists the tones the theme has.

## How to make the email more compact or more spacious

```python
email = EmailBuilder().metadata({**facts, "size_theme": "compact"}).section(body).build()
```

| Preset | Effect |
|---|---|
| `"compact"` | About 17% shorter. Smaller type, tighter spacing |
| `"standard"` (the default) | |
| `"spacious"` | About 23% taller. Larger type, more air |

Everything scales together, including the phone layout.

> **Note:** there is a fourth preset, `"dense"`, made for printed reports. An email refuses
> it, because it has not been checked in mail programs. See
> [Troubleshooting](08-troubleshooting.md#i-get-has-not-been-rendered-in-an-email-client).

## How to change the typefaces

```python
email = EmailBuilder().metadata({**facts, "font_theme": "modern"}).section(body).build()
```

`"classic"` (the default) sets titles and text in Georgia, labels in Arial and table
figures in Courier New. `"modern"`
switches titles and labels to Tahoma and keeps the body in Georgia.

To use your own faces, derive from a preset. Name only faces your readers will have
installed, and end each list with `serif`, `sans-serif` or `monospace` as the last resort:

```python
from pyhermes.builder import DEFAULT_FONTS, FontStack

house_fonts = DEFAULT_FONTS.derive(
    heading=FontStack("Calibri", "Arial", "sans-serif"),
    body=FontStack("Calibri", "Arial", "sans-serif"),
)
email = EmailBuilder().metadata({**facts, "font_theme": house_fonts}).section(body).build()
```

The four roles are `heading`, `body`, `label` (small print and labels) and `numeric`
(figures in tables). Web fonts are not supported, because most mail programs ignore them.

## How to centre or right-align a section

```python
centred = FullWidth(
    TextBlock("<p>Markets opened higher.</p>"),
    title="Overnight",
    align="center",
)
mixed = FullWidth(
    TextBlock("<p>This paragraph stays on the left.</p>", align="left"),
    title="Centred title",
    align="center",
)
email = EmailBuilder().metadata(facts).section(centred).section(mixed).build()
```

A section's `align` covers its title and its content, and a block inside can override it.
Figures rows and tables keep their own alignment.

## How to tint one section

```python
email = (
    EmailBuilder()
    .metadata(facts)
    .section(FullWidth(TextBlock("<p>Key call.</p>"), title="Our view", highlight=True))
    .section(FullWidth(TextBlock("<p>Detail.</p>"), background_color="#F4F1E8"))
    .build()
)
```

`highlight=True` uses the theme's tint. `background_color` sets an exact colour.

## How to put a section on a dark band

```python
dark = FullWidth(
    TextBlock("<p>Rates rallied into the close.</p>"),
    title="The day in one line",
    background_color="#1B2A38",
)
email = EmailBuilder().metadata(facts).section(dark).build()
```

On a dark `background_color` the title and the text turn light by themselves. To choose the
text colour yourself, add `text_color="#F2E6C9"`; it applies to the title and to every
paragraph, list and caption in the section.

Tables, figures rows and contact cards keep their dark text and are set on a white panel
inside the band, so their figures stay readable.

## How to put a frame around a section

```python
framed = FullWidth(TextBlock("<p>Positioning is stretched.</p>"), title="Risks", border=True)
accent = FullWidth(
    TextBlock("<p>Duration over credit.</p>"),
    title="Our view",
    border=True,
    border_color="#5B8A9A",
)
email = EmailBuilder().metadata(facts).section(framed).section(accent).build()
```

`border=True` draws a 1px frame in the theme's rule colour, and `border_color` changes it.
It works on `FullWidth` and every split, and with `highlight` or `background_color`.
`border_color` without `border=True` is refused. The frame is always 1px and square,
because Outlook ignores rounded corners.

## How to box one passage

```python
from pyhermes.builder import Callout, Stack

box = Stack(
    [
        TextBlock("<p>Breadth narrowed through the week.</p>"),
        Callout(
            TextBlock("<p>Stay long the belly; fade the long end.</p>"),
            tone="positive",
            label="Key takeaway",
        ),
    ]
)
email = EmailBuilder().metadata(facts).section(FullWidth(box, title="Rates")).build()
```

A `Callout` boxes one block, which can be a `Stack` of several. Without a `tone` it uses the
theme's highlight tint and rule. With `tone="positive"`, `"negative"`, `"neutral"` or a
[brand tone](#how-to-add-brand-tones) it takes a light tint and a frame in that colour from the
theme. `border=False` drops the frame. Its
padding is the `callout_pad_y` and `callout_pad_x` spacing tokens.

For a chip such as a ticker in black, fill the box with its tone's full colour:

```python
inked = DEFAULT_THEME.derive(tones={"ink": "#111111"})
chip = Callout(TextBlock("<p>HRMF</p>"), tone="ink", label="Ticker", fill="solid")
email = EmailBuilder().metadata({**facts, "theme": inked}).section(FullWidth(chip)).build()
```

**Result:** a black box with white type. The type inside switches to the theme's `on_dark`
colours on a dark tone and keeps the theme's own type on a light one, as a dark section does,
so you never choose it. A solid box needs a `tone`. Outlook draws the fill as well.

## How to add a button or a dividing line

```python
from pyhermes.builder import Button, Divider

closing = Stack(
    [
        TextBlock("<p>The full note has the charts.</p>"),
        Divider(),
        Button("Read the full note", "https://example.com/note", align="center"),
    ]
)
email = EmailBuilder().metadata(facts).section(FullWidth(closing)).build()
```

`Button` is the same Outlook-safe button `ContactBlock` uses, in the theme's accent. `Divider`
is a thin rule in the theme's rule colour, with `block_gap` space above and below. Both go
anywhere a block goes, including a column. In the plain-text part, a button prints as
`label: url` and a divider as a line of dashes.

## Label and flag items

**When to use this:** to mark a card, a table cell or a section *New*, *Upgrade* or
*Preliminary*; to show a column of statuses as coloured dots; or to list a few topics lightly.

```python
from pyhermes.builder import Badge, CardGroup, Column, DataTable, TagRow
from pyhermes.builder.models import Cell, KpiItem, TableRow

calls = CardGroup(
    [
        KpiItem("10Y gilt", "Overweight", badge=Badge("Upgrade", "positive")),
        KpiItem("Linkers", "Neutral", badge="New"),
    ]
)
statuses = {"On track": "positive", "Watch": "neutral", "Breach": "negative"}
dashboard = DataTable(
    ["Book", Column("Rating", kind="text"), Column("Status", kind="status", statuses=statuses)],
    [
        TableRow(["Gilts", Cell("A", badge=Badge("Upgrade", "positive")), "On track"]),
        TableRow(["Sterling IG", "BBB", "Breach"]),
    ],
)
labelled = (
    EmailBuilder()
    .metadata(facts)
    .section(FullWidth(calls, title="Recommendations", badge="Preliminary"))
    .section(FullWidth(dashboard, title="Risk dashboard"))
    .section(FullWidth(TagRow(["Rates", "Credit", "FX"]), title="Markets covered"))
    .build()
)
print(labelled.text())
```

**Result:** each card's label carries its badge, the gilt's rating has an *Upgrade* badge after
it, every status has a dot in its colour before it, and the last section lists three tags. In
the plain-text part a badge reads `[UPGRADE]` beside what it labels, a status is the word
alone, and the tags read `Tags: Rates, Credit, FX`.

**Notes:**

- A badge takes a tone, `"positive"`, `"negative"` or `"neutral"` (the default), never a
  colour, so it follows the theme. A plain label such as `badge="New"` is a neutral badge.
- A label is at most 24 characters (`Config.badge_max_chars`). A section's badge needs the
  section to have a title, because it sits after it.
- A status column needs `statuses=`, naming every word its cells may hold and each word's tone.
  A word it does not name is refused when the table is built.
- A `TagRow` takes two to twelve tags and wraps onto more lines when it runs out of room.
- Badges and dots are rounded in a browser and in a PDF. Outlook on Windows draws them square.

