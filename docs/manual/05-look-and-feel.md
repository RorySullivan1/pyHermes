# 5. Look and feel

Three settings change how the whole email looks: **colour**, **density** (how much space
everything takes) and **typeface**. Each is one key in the metadata, and each can be a
ready-made preset or your own. You never set a colour or a font size on a single block.
That keeps every email in a series consistent.

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
