# 4. Images and charts

Every picture in an email, whether a logo, a photograph or a chart, is an `EmailImage`. It
records two things: where the picture comes from, and how it reaches the reader.

```python
from pyhermes.builder import ChartBlock, EmailBuilder, FullWidth, ImageBlock
from pyhermes.builder.images import EmailImage

facts = {
    "email_subject": "Credit Monitor",
    "firm_name": "Acme Research",
    "campaign_name": "Credit Monitor",
}
```

## Choose how the picture travels

| You write | The picture… | In Outlook at work | In Gmail |
|---|---|---|---|
| `EmailImage.attached("chart.png", ...)` | travels inside the email | shows straight away | shows |
| `EmailImage.hosted("https://…/chart.png", ...)` | is fetched from a web server when opened | hidden until the reader clicks **Download pictures** | shows |
| `EmailImage.inline(...)` | is written into the HTML itself | **does not show** | **removed** |

**Use `attached` unless you have a reason not to.** It is the only one that shows up in
Outlook without the reader doing anything, and it does not count towards Gmail's 102 KB limit.
Use `hosted` when your firm serves images from a web server. Avoid `inline` in anything
you send. It exists for quick local previews.

> **Note:** an attached picture only exists inside the finished message. If you open the
> `.html` file from `email.save()` in a browser, attached pictures show as broken. That is
> expected. To see them, open the `.eml` file described in
> [Check and send](06-check-and-send.md), or use `python -m qa.preview … --screenshot`.

## How to add a picture

**Steps:**
1. Save the picture as a PNG, JPEG or GIF. WebP and SVG are refused because Outlook
   cannot show them.
2. Describe it in `alt`. The reader sees this text when pictures are blocked.
3. Give its display width in pixels.

```python
chart = EmailImage.attached("chart.png", alt="Spreads widened 12 bps in September", width=616)
email = (
    EmailBuilder()
    .metadata(facts)
    .section(FullWidth(ImageBlock(chart, caption="Investment-grade spreads"), title="Spreads"))
    .build()
)
```

**Result:** the picture centred across the section, with its caption beneath.

**Notes:**
- A full-width section is **616 pixels** wide inside its margins. Each half of a 50-50
  split is about 280. Save the picture at twice that width so it looks sharp on a
  high-resolution screen, and give the display width in `width=`.
- A picture more than four and a half times wider than its `width=`, such as a phone photo
  shown as a thumbnail, raises a `SizeWarning` that says what width to export it at. It
  still builds, but it adds weight to every message. `Config.oversize_image_ratio` changes
  the limit.
- A picture you pass as `bytes` works the same way as a file path:
  `EmailImage.attached(png_bytes, alt=..., width=...)`.
- For a purely decorative picture, write `decorative=True` instead of an `alt`.
- `ImageBlock` also takes `link_url=` to make the picture a link, and `align="left"` or
  `"right"`.

## How to show a chart with its source

**When to use this:** a chart image, with a source line and small print underneath.

```python
chart = ChartBlock(
    EmailImage.attached("chart.png", alt="Spreads widened 12 bps in September", width=616),
    source="Acme Research, Bloomberg",
    caption="Investment-grade spreads",
    label="Chart",
    disclosure="Option-adjusted spreads. Past performance is not a guide to the future.",
)
email = EmailBuilder().metadata(facts).section(FullWidth(chart, title="Spreads")).build()
```

**Result:** *Chart 1 · Investment-grade spreads*, the image in a thin frame, then the source
and the small print.

## How to use a matplotlib chart directly

**When to use this:** you draw your charts with matplotlib. Needs the `[charts]` extra.

<!-- manual: needs charts -->
```python
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pyhermes.data import chart_from_figure

fig, ax = plt.subplots(figsize=(6, 3))
ax.plot([1, 2, 3, 4], [110, 118, 115, 122])
ax.set_title("IG spreads, bps")

chart = chart_from_figure(fig, alt="IG spreads rose to 122 bps", width=616,
                          source="Acme Research")
email = EmailBuilder().metadata(facts).section(FullWidth(chart, title="Spreads")).build()
plt.close(fig)
```

**Result:** the figure as you drew it, saved at twice its display width and attached to the
email. pyHermes does not restyle your plot.

## How to draw a chart in the email's colours and type

**When to use this:** you want your matplotlib charts to match the email, and to follow it
when the theme changes. Needs the `[charts]` extra.

<!-- manual: needs charts -->
```python
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pyhermes.data import chart_from_figure, chart_style

style = chart_style("classic")             # or chart_style(email.metadata.theme)
with plt.rc_context(style):
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot([1, 2, 3, 4], [110, 118, 115, 122])
    changes = [0.4, -0.2, 0.3]
    ax.bar([5, 6, 7], changes, color=[style.positive if c > 0 else style.negative for c in changes])

chart = chart_from_figure(fig, alt="IG spreads rose to 122 bps", width=616)
plt.close(fig)
```

**Result:** lines and bars in the theme's colours, the first series in its accent, axes and
gridlines in its rule colours, and labels in its small-print typeface where your computer
has it.

**Notes:**
- Nothing changes outside the `with` block, and a colour you set yourself is kept.
- `style.positive` and `style.negative` colour bars by sign. `style.series` lists the series
  colours in order.
- `chart_style("slate", "modern")` takes a font theme too, and `role="body"` uses the body
  typeface instead of the small-print one.

## How to add a logo to the masthead

```python
from pyhermes.builder import Banner

logo = EmailImage.attached("logo.png", alt="Acme Research", width=120)
email = (
    EmailBuilder()
    .metadata(facts)
    .banner(Banner(logo_url=logo))
    .section(FullWidth(ImageBlock(EmailImage.attached("chart.png", alt="Chart", width=616))))
    .build()
)
```

## How to put a photograph behind the masthead

```python
from pyhermes.builder import BannerPalette

banner = Banner(
    title="Q3 Outlook",
    background_image_url=EmailImage.attached("masthead.png", alt="", decorative=True, width=680),
    palette=BannerPalette(title="#FFFFFF", subtitle="#E0E6EB"),
)
email = EmailBuilder().metadata(facts).banner(banner).section(FullWidth(ImageBlock(
    EmailImage.attached("chart.png", alt="Chart", width=616)))).build()
```

**Notes:** the masthead is 680 pixels wide. The `palette` lets you pick text colours that
read well over your photograph. Any colour you leave out keeps the theme's.

## How to reuse a picture

Attach it once and use it as often as you like. The same picture is only carried in the
message once, however many times it appears.
