---
paths:
  - "svc/math/**"
  - "tests/test_math.py"
  - "tests/test_math_block.py"
  - "tests/test_math_paged.py"
  - "svc/builder/templates/media/math-block.html"
---

# Equations — a MathBlock that survives every medium (#221)

An equation is an **image in every medium**, by decision. Gmail strips MathML and SVG,
Outlook's Word engine renders neither, a web font for math never loads in a mail client, and
WeasyPrint has no MathML. The one thing every client shows is a picture, so the work is making
that picture honest: its source kept, its number computed once, its projection readable.

## The model: the component takes bytes, the extra renders them

| Piece | Where | What it knows |
|---|---|---|
| `MathBlock(image, latex=… \| lines=…)` | `svc/builder/components.py` | An `Exhibit`: the image, the source, caption, label, notes. **Never matplotlib.** |
| `render_math(latex, font_px, color, scale, fontset, lines, align_lines)` | `svc/math/render.py` | mathtext, behind `_backend()`. Returns `RenderedMath(png, width_px, height_px)` |
| `math_block(latex, theme, size_theme, …)` / `image_from_math` | `svc/math/adapter.py` | Joins them: the colour and size from the caller's theme and density |

- **The stub put rendering in the component, and that was corrected.** `MathBlock(latex)`
  rendering at construction would make the builder import a backend.
  `test_no_core_module_imports_an_optional_backend_or_the_adapters` forbids that, lazily or not,
  for the reason `data-layer.md` gives for refusing `DataTable.from_frame`. So the component
  is `ChartBlock`'s half of the `chart_from_figure` pair, and `svc/math` is a third sibling of
  `svc/data` and `svc/pdf` on the same terms. The purity tests cover it both ways.
- **The source is the alt text and the text projection.** The `img` alt is the LaTeX, escaped
  as an attribute, and `text()` prints `$source$` on its own line beneath the numbered caption,
  one line per line of a multi-line display. The raw-HTML set stays closed at five. A screen
  reader that does not know LaTeX reads `\sigma` as a word. It is still the one faithful
  description an equation image has, and a prose reading belongs in `caption`.
- **The component takes bytes, or an `EmailImage` whose alt is the source.** The issue's
  example passed an alt-less `EmailImage.attached(png)`, which `EmailImage` refuses at
  construction. So bytes are the unlabelled form, and the component attaches them with
  `alt=latex`. A supplied image whose alt differs from the source raises, and so does a
  decorative one: an equation is never decorative.
- **It is an `Exhibit` in full.** `label="Equation"` numbers it under its own label, with
  `id="equation-N"`, as a cross-reference target, with `[^n]` in its caption. Nothing in the
  apparatus knows the word "Equation": the label is the caller's, as "Figure" and "Table" are.

## The picture is painted for a theme, once

**The stub wanted the glyph colour from `theme.text.primary` "so a themed email recolours its
equations". A picture's pixels are fixed at construction, and the theme is bound at render,**
so that cannot happen. `math_block` takes `theme=` and `size_theme=` and paints the glyphs in
`theme.text.primary` at `size.type.body`. A document under another theme needs its equations
rendered for it, and the factsheet passes its own facts. There is no colour, size or font
parameter: a per-call hex is what the caller-facing surface refuses everywhere, and a test
holds `math_block` and `image_from_math` to it. Recolouring at render would need the builder
to import the backend.

## The fontset and the scale, and what they cost

- **`DEFAULT_MATH_FONTSET = "cm"`.** Computer Modern is what a reader of research expects of
  an equation. `dejavusans` is matplotlib's default, but the shipped body face is a serif
  (Georgia), so a sans fontset matched it no better. The five fontsets give five byte streams
  and five pixel boxes for one source, so the fontset is part of the contract. A change of
  default is a golden change of every real equation's cid. `custom` is refused: it falls back
  through the caller's rcParams, so the same source would differ per machine.
- **`DEFAULT_MATH_SCALE = 4`.** That is 384 dpi at 96 px to the inch, over `print_dpi` (300),
  so one render serves paper. `SCREEN` caps it at 150 dpi where it is displayed, and a test
  reads both back from the PDF. The display width is the pixel width over the scale.
- **The bytes are deterministic and versionless.** Two renders of one source are equal, the
  `Software` chunk is suppressed, and one source twice in a document is attached once.
- **The email goldens never depend on matplotlib.** Every fixture's equation is `solid_png`
  bytes at a real render's size. The real render runs only in `tests/test_math.py`, in CI's
  `data` and `pdf` jobs, which install `[math]`.

Measured here (matplotlib 3.11.2, Python 3.11), `cm` at 14 px, scale 4. `test_math.py` pins
these within 4 px, so CI shows whether its runners' fonts agree:

| Source | Pixels |
|---|---|
| `\sigma_p^2 = w^\top \Sigma w` | 319 × 87 |
| `\hat{\beta} = (X^\top X)^{-1} X^\top y` | 496 × 85 |
| `\text{VaR}_{99\%} = -q_{0.01}(r)` | 480 × 71 |

**Twenty equations in one email are 280 KB on the wire**, against `attachment_warn_kb`
(15 360). That is about 8.9 KB per image at 4x, more than the issue's 5 KB estimate because the
sources were longer. The HTML part grows by the markup alone, about 1.2 KB per equation,
because the bytes ride the manifest as `cid:` parts. The 102 KB limit is untouched.

## What mathtext renders, and what it refuses

mathtext is a TeX subset and needs no TeX installation, which is why it can be a Python
extra. Measured on 3.11.2:

| Renders | Refused (a `MathSyntaxError` naming the symbol) |
|---|---|
| `\frac`, `\dfrac`, `\sum`, `\int_0^T`, `\left( \right)`, `\hat`, `\mathbb{E}`, `\mathcal{N}`, `\operatorname{Cov}`, `\text{…}`, `\leq`, `\top`, `\mid` | `\begin{aligned}`, `\\`, `\le` (use `\leq`), `\displaystyle`, `\limits`, `\underbrace` |

- **A parse error fails at the call.** matplotlib raises a three-line `ValueError` inside
  `savefig`. `render_math` renders at call time and wraps it as `MathSyntaxError` (a
  `MathError` and a `ValueError`), naming the source and the symbol, with the original
  chained.
- **At a dense 11 px body, `\frac` sets its numerator and denominator in script size**, and
  the factsheet's Sharpe ratio was illegible that way. Use `\dfrac` for a display fraction.

## Several lines, one image, aligned as a block (#232)

`math_block(lines=[…], align_lines="left" | "center" | "right")` renders each line as a
`$…$` run, joined by newlines, in one image. mathtext has no `aligned` environment and exposes
no glyph boxes to align a relation on, so **a line containing `&` is refused** with that reason,
and the lines align as one block. `latex` and `lines` together, or an empty `lines`, raise.

## Proven in each medium

- **On paper the equation is one figure.** `a4_equations` has three labelled equations. One is
  engineered at a sheet's foot, with `LEAD_IN_PARAGRAPHS = 8`. `tests/test_math_paged.py`
  reads each image and its caption back from the same sheet. Stripping `.figure`'s rule splits
  the engineered one. No new break rule was needed, because the caption is inside the figure
  table.
- **Its first raster found every equation stuck at the frame's left edge.** WeasyPrint
  resolves `margin: auto` against `width: 100%` before the `max-width` cap. The image is now
  `inline-block` in a zero-leading line box, placed by `text-align`, which keeps #201's
  cap-on-100% semantics. A test reads each image's centre back from the PDF.
- **`ImageBlock` and an aligned `ChartBlock` had it too, and in the browser as well.**
  Measured after #235: a centred `ImageBlock` sat 189 px left of centre on A4 and 208 px left
  of its cell's centre in Chromium. Its block image had no auto margin, and a block image
  ignores `text-align`, so only Outlook's `td align` ever centred it. Both now use the same
  wrapper. An unaligned chart keeps its block image and its bytes. On paper a decorative
  image is a background `div` of fixed width, so auto margins place it. Sixteen images across
  eight goldens moved, by that markup alone. `tests/test_image_centring.py` pins every
  alignment in both media, and 8 of its 11 cases fail against the old templates.
- **In the email**, `kitchen_sink` carries a labelled single-line equation and a two-line
  display. A real render substituted for the screenshot only (Chromium 141.0.7390.37) showed
  them crisp at 1000 and 375 px. At 320 px both keep their display widths (80 and 137 px)
  without scaling, the caption wraps, and there is no horizontal overflow.
- **A footnote must fit on its marker's sheet.** On the factsheet, a note on the equation's
  caption that did not fit floated to the next sheet, away from its marker, before the sheet
  count moved. The fix was room on the sheet, not a rule. Read the PDF's text per sheet, not
  just the page count.

## Owed, and out

- **An Outlook render is owed.** The equation is a plain attached `img` with a `width`
  attribute, the markup `img-width-attr` and `img-alt` check. How the Word engine shows it, and
  how a transparent PNG with dark glyphs reads under a client's dark mode, are unverified
  here (#150's posture).
- **Out, by decision:** MathML, MathJax, KaTeX and SVG (none renders in a mail client); full
  TeX (not a Python extra; `_backend()` is the seam if mathtext is outgrown); inline math (an
  image on a text baseline no mail client aligns reliably); `&` alignment; a list of
  equations (the apparatus has no list of exhibits of any kind); equations in the brochure's
  editorial primitives.

- **The equations epic (#221) is complete.** #229 added the component, #230 the renderer, #231
  the adapter, #232 the proof and the multi-line shim, and #233 this record and the
  factsheet's Sharpe ratio. Three things it leaves:
  - **The purity rule decided the shape before any code did.** The stub's one-line API was
    one the repository's own test forbade, and following the test gave the design the
    data layer already had.
  - **Both raster findings were layout facts no golden could see:** an image stuck at the
    left edge, and a footnote separated from its marker. Rule 3 again.
  - **A picture cannot follow the theme.** Say so where the caller chooses the theme, rather
    than promise a recolouring the medium cannot do.
