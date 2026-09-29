---
paths:
  - "pyhermes/builder/theming.py"
  - "pyhermes/builder/sizing.py"
  - "pyhermes/builder/typography.py"
  - "pyhermes/builder/enums.py"
  - "pyhermes/builder/containers.py"
  - "pyhermes/builder/templates/**/*"
---

# The four design axes — colour, size, typeface, alignment

### Theming — colour is one validated object

**One thing the theme cannot reach: a rendered picture.** An equation's glyphs (#231) are
painted at construction for the theme the caller passes to `math_block`, because the theme is
bound only at render. A document under another theme needs its equations rendered for it
(`math.md`).

Colour was 18 hex values in 245 occurrences across all 20 template files, three `rgba()`
literals and three Python fallbacks, described by a palette *comment* in `base.html` that
nothing could read — and that had already drifted, naming a row-alt colour the data table
never used. Epic #46 replaced it with [pyhermes/builder/theming.py](../../pyhermes/builder/theming.py).

```python
from pyhermes.builder import DEFAULT_THEME, Palette, Theme

EmailBuilder().metadata({..., "theme": "slate"})              # a curated preset
EmailBuilder().metadata({..., "theme": DEFAULT_THEME.derive(  # or your own
    palette={"header_bg": "#1B3A5C", "accent": "#7FA8B8"})})
```

`EmailMetadata.theme` → resolved **once** in `Email.render()` → four frozen layers
(`palette`, `text`, `semantic`, `shadow`) → templates read `{{ theme.palette.surface }}`.

- **The `Theme` is the unit of customisation, never a single colour at a call site.** That
  is what keeps a palette coherent while still being open: the layers are frozen, no token
  field is optional, and every value is validated at construction — so a `Theme` that exists
  is a `Theme` that renders, and `StrictUndefined` cannot be tripped by a half-built one.
  **There is deliberately no per-component colour parameter**; a `title_color=` anywhere
  would dissolve the palette one call site at a time.
- **The exceptions are a closed list of three, and one sentence explains all of them: the
  caller supplies the ground.** A theme can curate type against a surface it owns; it cannot
  curate type against a surface it has never been handed. Where a caller chooses the ground,
  and *only* there, they get a bounded say over what sits on it:

  | Exception | Since | The ground the caller supplies |
  |---|---|---|
  | `Container.background_color` | pre-existing | a section band — the original escape hatch, neither removed nor extended |
  | `Banner.palette` (`BannerPalette`) | #93 | a **photograph**: `background_image_url` is an image the palette has never seen, so white-on-navy tokens over a pale one are a guess |
  | `Header` / `Footer` `background_color` + `text_color` (`BoxSurface`) | #95, #99 | the two outer **boxes**, the same reason at the size those boxes need |
  | `Cell.color` + `Cell.background` | #118 | **not a ground at all — the other kind of exception.** Admitted as *semantic data*: the caller's claim about a **figure**, which is why `TableRow.colors` was never a breach either. See `data-table.md` |

  Everything else renders on surfaces the theme owns and gets nothing — every component, and
  every region's structural chrome. What the rule protects survives in all three, which is why
  these are exceptions rather than breaches: a caller picks a validated, coherent **atom**
  (a whole `BannerPalette`, or a background *with* the type that has to be legible on it),
  never a lone colour at a call site.

  **The fourth entry is a different kind of exception, and saying so is what keeps the rule
  alive.** `Cell.color` and `Cell.background` supply no ground — they are *data*. The clause
  that admits them is the one immediately below: `KpiItem.color` and `TableRow.colors` were
  always the caller's statement about the number, not a styling choice, so a cell background
  saying *breached its limit* or *stale mark* is the same claim in another channel. Read as
  "the caller controls cell appearance" it would be a `title_color=` with more steps; read as
  what it is, it never touches the palette's authority over surfaces the *theme* owns.

  **The list being closed is the point.** "Now every region gets a palette" is the failure
  mode, not the roadmap; a fifth exception has to name a ground the caller supplies, or be
  data in the sense the fourth is. The
  scoping is enforced rather than described: `BannerPalette` covers the *banner slot* only, so
  the strip in the same region keeps the theme's tokens even though the two share a class, and
  a test asserts it. **And the colour pair never ships alone** — a background without the text
  colour on it is half a decision, since the theme's type is a guess the moment the ground
  moves.
- **Tokens are named by role, not by value.** The same `#FFFFFF` is `palette.surface` behind
  a table and `text.on_dark` over the navy; the same `#2C3E50` is `palette.header_bg` as a
  band, `text.heading` as type and `palette.rule_dark` as an underline. Several tokens share
  a value today and are separate on purpose — type is not a surface, even when it borrows a
  surface's colour, and `row_alt` vs `highlight_tint` is a distinction the old comment drew
  before the templates lost it.
- **Shadows are stored as hex + alpha, never as an `rgba()` string** — otherwise a theme
  author is hand-writing CSS instead of picking a colour. `Rgba.css` composes the CSS form
  and `Rgba.opacity_percent` the VML one, on a **byte-exact contract**: no spaces after
  commas, no trailing zeros. The masthead scrim exists twice (CSS for everyone, VML
  attributes for Outlook) and both read one object, which is the only reason they cannot
  drift.
- **Semantic data stays data.** `KpiItem.color` and `TableRow.colors` are the caller's
  statement about the *number* ("this is down"), not a styling choice. The theme supplies
  only the fallback behind them. `Card.color` is **unset by default** and resolved at render
  to `theme.semantic.neutral` — a construction-time default cannot see a render-time theme —
  while an explicit value is still validated at construction exactly as before.
- **The engine guarantees a theme; the email chooses which.** `TemplateEngine.render()`
  layers `DEFAULT_THEME` *under* the caller's context, so rendering a component on its own
  stays a one-liner. `Email.render()` binds the resolved theme on top, and that always wins.

**A region resolves against the theme through `Region.theme_context()`.** The hook a region
overrides when one of its presentation fields means *"the theme's token, unless I say
otherwise"* — the banner's `BannerPalette`, the header's colour pair, and #98's footer box for
the same two tokens. It exists because the theme is neither a fact nor a field: it reaches the
templates through the bound engine, so a region only has it at render time and `context()`,
which has no engine, cannot resolve there. What it returns is layered **with the facts**, over
the region's own keys, so a resolved value cannot be shadowed by the raw field it came from —
and that is why **a resolved key takes a different name than the field it resolves**:
`Header.background_color` is what the caller set (possibly nothing), `header_background` is
what renders, and the template reads only the second. Generalised in #95 rather than
duplicated: the banner had grown its own `render_slots()` override, and the second region
needing one is what turned a special case into the mechanism. Two tests ride on it — the
"every template reads the theme namespace" check reads its accepted names off
`theme_context()` itself, so a region that grows one is covered without anyone widening the
test.

**How a `BannerPalette` reaches the markup.** Eight roles, one per colour the banner slot
draws — `band`, `title`, `subtitle`, `meta`, `accent`, `scrim`, `title_shadow`,
`subtitle_shadow` — each defaulting to `None`, meaning *the theme's token*. `FALLBACKS` is the
single place the role→token correspondence is written down. `Banner.render_slots()` calls
`palette.resolved(engine.theme)` and puts a **total** palette in the context under
`banner_palette`, so the template reads one object per colour with no `{% if %}` and nothing
for `StrictUndefined` to trip on — and an override reaches the markup by the same path an
inherited token does, which is what makes "unset renders byte-identically" a property of the
mechanism rather than a claim to re-test per role. `Renderer` grew a `theme` property for
this: the banner needs the theme as an *object*, and reading it off the engine is what kept
`render_slots()` the signature every region shares. **The scrim stays one `Rgba`** because the
masthead emits it twice (CSS `rgba()` for everyone, `v:fill` colour + opacity for Outlook), and
two sources is the drift this module exists to end.

**The two halves share the colour and must also share their guards — #150 is where they did
not.** #78 gated the CSS `background-image` on the value, because `url('')` is not inert, and
missed the `v:fill src` two lines above it; eight gallery fixtures shipped `src=""` to Outlook
for the life of the package. The gate is now on both — and on `type` as well as `src`, which
is the part that had to be *rendered* to be learned.

**VERIFIED, and the first attempt was wrong.** The staged fix gated `src` alone and kept
`type="frame"`, on the argument that only the attribute should move. Put in front of the Word
engine — the engine Outlook Classic uses for HTML mail — that markup does not draw the band at
all: `type="frame"` is a claim that the fill *is* an image, so with no source the engine paints
a **broken-image placeholder** across the masthead instead of falling back to `color`/`opacity`.
No band, no scrim, dark title text on white. That is worse than the empty `src` it replaced,
and identical to what the empty `src` already did — which is why "the render is unchanged" was
true and still not good enough.

The remedy is the one this file predicted: **gate `type` alongside `src`**, never the whole
`v:rect`, which would take the scrim with it. Without a `src` the fill is solid, and solid is
what VML honours `color` and `opacity` for — so the scrim reaches every banner, backdrop or
not. All four cases were rendered: backdrop present is byte-identical either way and draws the
photograph under the scrim; backdrop absent draws the flat band *with* its scrim only once
`type` is gated too. `TestTheVmlFillSrcIsGated` pins what is emitted in every case, and
`vml-fill-frame-without-src` now fails the lint pass on the shape that was staged — so this
particular wrong answer cannot come back quietly. Three tests hold the wiring: the templates
may not read `theme.` at all, they may not name a role `FALLBACKS` does not declare, and every
declared role must actually be drawn.

**How the theme reaches every template — the mechanism epic #45 rode.** A value owned by
the email must reach component templates several layers down. `TemplateEngine.bound(**shared)`
returns a `BoundEngine`: a **per-render** view that merges shared values into every context
and delegates the rest. Containers, components and regions keep taking one argument and
calling `engine.render(path, ctx)` unchanged — they are simply handed the view, and a test
asserts those signatures never grew a parameter. Threading an argument would have changed
every call site; an environment global would have made the engine stateful, so two emails
with different themes sharing an engine could interleave. Shared values layer **over** the
caller's context, the same way `Region.context()` layers facts over presentation: what the
email owns cannot be shadowed from below. **#40 rode it rather than building a second one**:
a size scheme is another shared value on the same binder, and nothing in the section tree
changed signature to accept it.

**Adding a preset**: curated values, not a hue rotation — every colour is a design decision,
exactly as the default's are. Add it to `THEMES`, and **land it with a gallery fixture**, as
`slate_theme` does. The registry is repo-owned and never mutated at runtime; a user's theme
is passed as an object, not registered by name.

**Contrast is a recommendation, not a rule.** Validation checks *shape* — valid hex, alpha in
range, completeness — never aesthetics. Aim for at least 4.5:1 between `text.primary` and
`palette.surface`, and between `text.on_dark` and `palette.header_bg`; a theme that fails
that is legal and will render, and no `ValidationError` will tell you. Judge it with
`python -m qa.preview <fixture> --screenshot`, remembering that Chromium's colour handling
is not Outlook's.

**Non-goals, as decisions**: no dark theme — the skeleton still forces light rendering and the migration tokenised that block without
changing what it does; no contrast or taste policing; **one theme per email** — a palette is
an email-level voice, so there is no per-section mixing.

### Sizing — density is one selected preset

Sizes were 57 `font-size` declarations, ~50 line-heights and ~90 padding literals across 20
templates, plus the 680px frame arithmetic written out **twice per column in eight container
files**. An implied scale existed (28 / 22 / 21 / 17 / 14 / 13 / 11 / 10 / 9.5 px); nothing
named it, owned it, or could vary it. Epic #45 replaced it with
[pyhermes/builder/sizing.py](../../pyhermes/builder/sizing.py).

```python
EmailBuilder().metadata({..., "size_theme": "compact"})     # or "standard" / "spacious"
```

`EmailMetadata.size_theme` → resolved **once** in `Email.render()` → four frozen layers
(`type`, `space`, `component`, `frame`) → templates read `{{ size.type.body }}`.

- **Superseded (#212): "`size_theme` accepts a `SizeTheme` member or its bare string and
  nothing else."** It was stricter than colour on purpose: density interacts with the 102 KB
  clipping limit, Outlook's Word engine and the mobile collapse all at once, so a scheme nobody
  has rendered in a real client is a compatibility claim nobody has tested. It also said
  widening later is additive, and #209 is that widening. `size_theme` now takes a
  `SizeScheme` as `theme` takes a `Theme`, and the reason survives as a **gate on the email
  medium**: an `Email` refuses a custom scheme, and the print density `dense`, unless
  `Config.allow_custom_email_density` says the caller has rendered it. A paged document and
  a brochure take any scheme, because nothing clips a PDF and no Word engine reads one.
  `Document.__init__` runs the gate, so it fails at construction. Callers still never pass a px.
- **Tokens are named by role, not by number**, for the reason the colour epic learned the
  expensive way: a value-keyed vocabulary is byte-identical and useless, because changing the
  masthead would silently change every body heading that happened to share its size.
- **Validation rejects an integral float.** A scheme holding `14.0` renders
  `font-size:14.0px` — legal CSS, and a byte-identity failure. The rule cannot simply be
  "ints only": `micro` is genuinely 9.5.
- **`frame.inner` is a property, never a field.** A stored inner width could disagree with
  `width - 2 * pad_x`, and the eight container templates are what that disagreement looked
  like in practice.
- **The engine guarantees a scheme; the email chooses which** — the same floor as the theme.
  `TemplateEngine.render()` layers `STANDARD_SIZES` *under* the caller's context, so
  rendering a component on its own stays a one-liner, and `Email.render()`'s binding wins.

**`dense` is the fourth preset, and the first tuned for paper (#211).** A printed factsheet
spends 14 to 16px on a table row, and `compact` spent about 37. `DENSE_SIZES` is a derive of
`COMPACT_SIZES`, so what it decides beyond compact is the literal content of its definition,
and a test holds that no token it sets is roomier than compact's. Three rules shape it, in the
shape of compact's four:

- **The readability floor moves, and stops at 8px.** Compact held `label` and `micro`; on paper
  `label` 9 is 6.75pt and `micro` 8.5 is 6.4pt, both above the 6pt below which fine print is not
  read. A test pins the floor.
- **Leading tightens less than type.** Body type gives up 2px of 13 and `body_line` 0.2 of 1.6,
  the smaller share. The KPI value gives up the least of all, 17 against 19, for compact's reason.
- **Most of the density is spacing, and a table row is where it is spent.** `table_cell_pad` 4
  against 8, section rhythm about half, and a frame `pad_x` of 12, since a sheet already has a
  printed margin and an email's padding is its only one.

The probe in #209 (11px body, 3px cells) filled 60% and 63% of the factsheet's sheets. `dense`
is tuned up from it and filled 65% and 68% before the factsheet spent the room.

**Column geometry is arithmetic the builder owns.** A ratio's own *name* is its weights —
`"25-25-50"` is `[25, 25, 50]` — and `column_layout()` splits the active scheme's content
width by them. No lookup table: a table would be a second place for the split to be written
down, and therefore a second place to be wrong. Weights normalise by their own sum, which is
what makes `"33-33-33"` exact thirds rather than 99% of the frame with a 6px hole in it. Two
rules the arithmetic had to *recover* rather than invent:

- **The remainder goes outside-in.** 584px does not divide by three, and which two columns
  gain a pixel was already decided by hand as 195 / 194 / 195. `_remainder_order()`
  reproduces it — and it is the right rule independently, because a reader notices an
  asymmetric left/right pair, not a centre column one pixel narrower than its neighbours.
- **Column padding steps down below `frame.narrow_column`.** The 20px / 16px split was never
  a rule, only a per-file choice: 300 and 420 had 20, 292 and smaller had 16. That threshold
  is the rule made explicit — and it is the one token that moves *down* in `spacious`, where
  a 24px gutter puts a two-up split at 288px and holding it at 300 would have handed the
  airiest theme the tightest column padding.
- **A column's *outer* edge takes no padding at all** (#85). The band is inset by
  `frame.pad_x`, so padding the two edges that face the frame would indent that text past the
  section heading above it — which is exactly what it did, for as long as the eight per-ratio
  templates existed. Only gutter-facing sides pad, so the gap *between* columns is unchanged.

**One left margin, and it is checkable.** Every section heading and every container content
box starts at `frame.pad_x` from the frame edge — full-width and multi-column alike, at every
density. Two things make that hold and are easy to undo by accident: the band's inset cell
zeroes `font-size`/`line-height`, because the columns are inline-blocks and the newline
between two of them would otherwise render as a space that no longer fits; and a highlighted
band gives its 1px hairline back to every horizontal inset (`edge_pad`), or the last column
wraps. A browser test asserts the invariant per fixture — the goldens cannot, because this
was correct markup laid out wrongly.

**The eight per-ratio templates are one template.** They were byte-identical apart from a
Jinja comment and the numbers, so they were never carrying a per-ratio *decision* — they were
carrying arithmetic nobody had done in Python. `TwoColumn` and `ThreeColumn` share
`_SplitContainer` and one `template_path`; the ratio selects numbers, not a file, and a test
fails if a `col-*.html` ever comes back. The attribute width and the CSS width come from one
computed value, asserted per column at frames the email has never shipped at.

**A data table tightens its cells at the breakpoint, and cannot do more (#132).**
`table_cell_pad_mobile` is the only lever a narrow viewport has on a table: a `CardGroup`
collapses because a KPI strip *becomes* the vertical card layout, but stacking a table's
columns would destroy the alignment that is the only reason to render one — the same
reasoning that refuses `colspan`. Tightening the cells buys a measured 24px on a
five-column table, which is enough for the 375px viewport the harness asserts and not
enough for 320. **It is a mitigation with a measured headroom, not a guarantee**: a wide
enough table still overflows, and that limit is the caller's to design around. The rule
selects on the table rather than on every cell — one class per table against ~19 bytes per
cell, which the clipping budget notices.

**`.kpi-cell` reads `card_pad_*` on purpose.** On a phone a horizontal KPI strip *becomes*
the vertical card layout, so it is padded like one rather than from a second pair of tokens.
That is what stops a compact email rendering airier on a phone than on a desktop, and a test
asserts it per theme.

**Adding a theme**: add the `SizeTheme` member, populate a full `SizeScheme` — the
completeness test enforces "full", and a member without a scheme raises a message saying so —
and **land it with a gallery fixture**. Write it as `STANDARD_SIZES.derive(...)` so what the
preset *decides* is the literal content of its definition and everything else is visibly
inherited; `derive()` re-runs each layer's validation, so a derived scheme is checked exactly
as a hand-built one. Curate, do not multiply: a multiplier would shrink fine print below
legibility, scale leading linearly with type when leading should move the other way, and
treat a KPI number as ordinary body copy. Tests assert all three.

**Non-goals, as decisions**: no free-form size parameters (`size_theme` and a named-token
`spacing` are the whole surface, below);
**no narrow-frame theme** — all three keep the 680px frame, and #42 made width *derivable* so
that shipping a different one becomes a deliberate act with its own client-testing burden and
its own interplay with image `width=` attributes, rather than a side effect. **#159 made that
deliberate act a named one**: the page is a `PageFormat` the *medium* owns, layered over the
density's frame at render time, so a density still cannot reach a width and choosing a
different one now means choosing where the document is read. The non-goal stands; what changed
is that a frame width has an owner rather than a convention; one theme per
email, since density is an email-level voice; and no font theming — which stopped being a
non-goal when #56 landed, and is the axis below.

### Spacing per object — a derive of the bound scheme, never a px (#209)

**Two levels, and the second speaks the first's vocabulary.** The preset stays the general
control: a document picks a density, or passes a scheme derived from one. An object carrying
`spacing=` renders itself and its subtree through `engine.bound(size=...)` with the bound
scheme derived again, which is the move a brochure `Panel` already made for its surface colour.
Every template keeps reading `size.*`, so `TestNoScaleLiteralSurvives` never moved, and an
override can only move a token the object already reads.

```python
DataTable(headers, rows, spacing=Spacing(table_cell_pad=3))
FullWidth(content=table, spacing={"content_top": 6})
Page(sections, spacing={"table_cell_pad": 3})       # every section on the sheet
```

- **A caller names a token, flat, and `Spacing` finds its layer.** `by_layer()` is the shape
  `derive` takes. A name in two layers would be refused rather than guessed; none is today, and
  a test holds both.
- **Four kinds of name are refused whatever the object.** The width (`width`, `height`,
  `margin`, `mobile_breakpoint`, `narrow_column`) is the medium's. The type layer and the
  component leadings and `kpi_value` are the document's voice. `cta_width`, `cta_height` and
  `list_ordinal_width` size a box rather than space it. And a bad value fails with the message
  a bad preset would, because `Spacing` validates by applying itself to `STANDARD_SIZES`.
- **`SPACING_TOKENS` is per class, and a test derives it from the template.** It renders each
  container and component with each declared token set to a sentinel and finds the sentinel.
  Then it perturbs every other eligible token at document level and asserts the markup does not
  move. The second half is what caught the CTA and ordinal sizes, and a deliberately wrong
  declaration fails both halves. A container declares only its own template's tokens. A `Page`
  declares every token a section or component reads, because it reaches them all.
- **The email refuses what its `@media` block reads.** That block reads the document's scheme,
  never a subtree's, so a section moving `card_pad_*` or `mobile_*` would render one way wide
  and another collapsed. `pad_x` joins them because the masthead, the footer and every section
  share it on an email. `Document.add_section` refuses them on any medium that is not paged,
  and the render refuses them again for a component rendered on its own. A test reads the
  `@media` block and fails if it ever reads a token outside the named set.
- **No override, no rebind.** `respaced()` returns the engine itself for `None`. A test renders
  every fixture in all three galleries with the rebind patched to raise, and the goldens of
  every fixture without an override were byte-identical through the whole epic.
- **An override has no plain-text projection.** Spacing is a markup concern, as the three axes
  are, and a test holds `text()` byte-identical with and without one.

**Non-goals, as decisions**: no free pixel parameter on any template or constructor, and no
`padding="4px 8px"` string anywhere; no per-object type scale, since a pull quote or KPI that
needs a different size already has a component token; no CSS margin on sections, which Outlook
drops on a `td` and a `tr`, so the section rhythm stays padding on cells; and no layout engine.
Nothing computes a fit: the print engine breaks sheets, and the author trims content.

**What the epic left.**

- **A scheme on the metadata, a spacing on the tree, and one gate between them and the email.**
  Every refusal names the switch or the medium, so a caller hitting one learns what to change.
- **The reverse sentinel is the half worth copying.** Proving a declared token is read is the
  obvious test. Proving every *undeclared* token is not read is what found two tokens the first
  declarations missed, and it is the check a future template edit will trip.
- **A local override hides a document-level token from a document-level test.** Once
  `kitchen_sink` tightened its only table and its only KPI strip, `TestTheTokensAreLive` could
  no longer see `table_cell_pad` or `kpi_pad_y` arrive. The fix was to strip the overrides in
  that test, whose subject is the document's scheme, rather than to weaken it.
- **The factsheet is the proof.** At `dense`, with its returns tables at `table_cell_pad` 3, it
  carries a risk-statistics table, a trading table and a second row of characteristics, and
  still fills 90% of each of its two sheets.

### Alignment — geometry, not a fourth design axis

Colour, density and typeface each became an email-level *theme*. Alignment did not, and
saying why is the first thing to keep: it is **layout geometry**, the same category as
`TwoColumn(ratio=…)` and `CardGroup(orientation=…)`, which have always been per-call-site
parameters. A section's alignment varies *per section* — that is the point of it — so it can
never be an email-level voice. There is no `align_theme`, no fourth shared value on the
binder, no entry in the closed colour list, and nothing to widen in the no-per-call-site-
parameter test. Two tests pin exactly that, including one forbidding any alignment field on
`EmailMetadata`.

```python
FullWidth(title="Q3 Outlook", align="center", content=TextBlock("…"))
FullWidth(align="center", content=TextBlock("…", align="left"))   # the block opts out
```

`Container.align` (#126) and `Component.align` (#127) both take a `TextAlign` member or its
bare string, default to unset, and validate at construction. Unset emits nothing, which is
why every pre-existing golden is byte-identical.

- **Alignment is *inherited*, not resolved — and that is the epic's central decision.**
  `text-align` is an inherited CSS property, so a declaration on the container's cells
  reaches the prose inside without anything being threaded down. There is deliberately no
  `resolved_align()`: `Component.render()` still takes one argument and `context()` still
  takes none. This is **not** what `Column`/`Cell` do (#117, #118), and the difference is
  the reason: a table cell's alignment has a *second reader* — `textgen.table()` pads the
  plain-text columns with it — so it must be computed. Prose alignment has one reader and
  projects to nothing. Re-deriving in Python what the cascade does for free would
  reintroduce exactly the multi-reader convention #117 was filed to remove.
- **The boundary is free, and a test keeps it that way.** Every structural component
  already declares its own alignment, so inheritance stops where it should — a KPI cell
  stays centred and a table column keeps resolving from its `kind` inside a right-aligned
  section. Nothing arranges that; `TestTheBoundaryHolds` exists because a template edit
  removing one of those declarations would let a section leak in silently.
- **Which components take an `align` is structural.** `CopyAlignment` is a mixin in
  `BoxSurface`'s shape, so the answer is readable off the class hierarchy rather than a
  hand-maintained list, and a test asserts the split is **exhaustive**: every public
  component is either prose or named as structural. `CardGroup` and `DataTable` are
  excluded because their alignment *is* structural and a coarser knob could only override
  the column resolution or be ignored by it; `ImageBlock` because its `align` places a
  block. The reasons live on the class, and a test asserts the docstring still carries them.
- **A container's alignment lands on *two* cells.** The title and the content are sibling
  tables in `full-width.html`, not parent and child, so a declaration on the content cell
  alone leaves the heading where it was. Non-obvious, easy for a future template edit to
  undo, and the specific thing the epic's prototype showed does not happen by itself.
- **Both spellings travel together** (#125): the `align` attribute for Outlook's Word
  engine, the `text-align` style because an attribute is not inherited by descendants and
  inheritance is the whole mechanism. `tests/test_alignment.py` holds that as an invariant
  — present, agreeing, and inside the three-value vocabulary — because the pairing is
  invisible in every browser and every screenshot.
- **Three elements are exceptions, and each is a different kind.** A `caption`'s `align`
  attribute means *placement*, not text alignment, so pairing it would move the element;
  an `a` has no `align` attribute at all; and `base.html`'s outer cell is **attribute
  only**, because its job is centring the email table as a *block* — a browser maps that
  attribute to `-webkit-center`, and the literal `text-align:center` is a different value.
  Pairing that one un-centred every email *and* centred every paragraph in it.

**The epic's real lesson: a byte-verified diff is not a verified render.** #125's golden
diff was script-verified to contain only alignment declarations, and was still a visual
regression in every email. #76 established that layout regressions live with the
screenshots; alignment produced three more findings that no golden could see — the
`base.html` regression above, the column cells that shrink-wrap instead of filling their
column (#129 — ``inline-block`` stopped it being a table box), and body copy escaping its
own styling element (#130). All three are fixed; each needed a browser to see.
Screenshot the change.

**Non-goals, as decisions**: no `align_theme` (see above); **no vertical alignment** —
`columns.html` hardcodes `valign="top"`, and unequal-height columns aligning middle or
bottom is the cross axis, with no inheritance story and its own client-testing burden; and
no `justify`, which does nothing to a single short line and whose absence `TextAlign`
records.

### Typography — the face is one selected vocabulary

Faces were the last hardcoded axis. Colour became a resolved `Theme` in #46 and density a
resolved `SizeScheme` in #45, but `font-family` stacks stayed baked into the templates: 49
declarations of three stacks across 15 files, unnamed and unvariable, so a newsletter wanting
its own house face forked templates. Epic #56 replaced them with
[pyhermes/builder/typography.py](../../pyhermes/builder/typography.py).

```python
from pyhermes.builder import DEFAULT_FONTS, FontStack

EmailBuilder().metadata({..., "font_theme": "modern"})           # a curated preset
EmailBuilder().metadata({..., "font_theme": DEFAULT_FONTS.derive(  # or your own
    heading=FontStack("Publico", "Georgia", "serif"))})
```

`EmailMetadata.font_theme` → resolved **once** in `Email.render()` → four roles
(`heading`, `body`, `label`, `numeric`) → templates read `{{ font.body }}`.

- **The atom is the `FontTheme`, and the surface accepts an object** — like `theme`, unlike
  `size_theme`. The asymmetry is the same one, read the other way: density interacts with the
  clipping limit, the Word engine and the mobile collapse at once, so an unrendered scheme is
  an untested compatibility claim; a *face* fails visibly and locally, and every stack ends in
  a generic family, so the worst case of a caller's own house font is the reader's default
  serif. A house face is exactly the kind of thing a house has.
- **A stack must end in a generic family** (`serif` / `sans-serif` / `monospace`), and a bare
  generic alone is rejected as an empty decision. This is the one rule that makes the point
  above true: email clients have no webfont guarantee and Outlook substitutes silently, so a
  chain with no terminal is a chain whose last resort is whatever the client felt like.
- **Roles are named by the job a face does, not by the face doing it** — the third repetition
  of the vocabulary lesson, and the axis where it was hardest to see: `heading` and `body`
  share one stack in the default, so a value-keyed migration would have merged them and been
  byte-identical. `modern_fonts` is what proves the cut was in the right place, because it
  moves one and holds the other.
- **`FontStack.css` is byte-exact, and families are stored unquoted.** A caller passes
  `FontStack("Courier New", "Courier", "monospace")`; the quoting rule (single quotes iff the
  name contains a space), the `", "` separator and the absence of a trailing separator all
  live in one property, for `Rgba.css`'s reason — an inline `style=` attribute is not a place
  to hand-write escaping, and a family carrying a quote, a semicolon or an angle bracket is
  rejected at construction rather than emitted into one.
- **The migration was two commits, and had to be.** The templates spelled the same stack two
  ways — `Georgia, 'Times New Roman', serif` in 26 declarations and the unspaced form in the
  rest — so tokenising in one step could not be byte-identical, and a golden diff mixing "the
  spelling changed" with "the mechanism changed" is a diff nobody can review. The first commit
  normalised the spellings **as literals** (250 golden lines moved, script-verified to be
  whitespace-only inside `font-family` values); the second tokenised and moved **nothing**.
- **The watch-site is the `[if mso]` block, not the `@media` one.** `body, td, th {
  font-family: … }` is Outlook's floor for the entire message, so a literal there renders a
  themed email custom-faced in Gmail and Georgia in Outlook — a half-theming that only shows up
  in the client hardest to check. The dark-mode and `@media` blocks carry no faces today, and a
  test asserts that too, so an edit adding one has to tokenise it like everything else.

**How the tokens are proved drawn.** The gallery's widest email is rendered under a
`SENTINEL_FONTS` theme whose four roles are four findable families, and the test asserts each
role reaches the page **and** that no shipped family survives. That second half is what earned
its keep: `data-table.html` spelled its mono branch as `{% if loop.first %}Arial…{% endif %}`,
so the literal did not sit behind a `font-family: ` prefix and the migration skipped it. The
goldens could not see that — the render was correct, because the literal was correct — and the
sentinel test failed immediately.

**Adding a preset**: curate, do not permute. Add the `FontTheme` to `FONT_THEMES`, and **land
it with a gallery fixture**, as `modern_fonts` does. Write it as an explicit theme or a
`derive()`, so the roles it *decides* are the literal content of its definition, and add the
pair of tests `modern` carries: that it moves only the roles it claims, and that its render
differs from the default's in `font-family` values and in nothing else. `MODERN_FONTS` is the
worked example — a display swap (`heading` and `label` to a sans, `body` and `numeric` held),
not a wholesale reface, because a newsletter is read in a serif and a data table aligns in a
mono.

**Non-goals, as decisions**: no per-component or per-call-site `font_family=` (the theme is the
whole surface, for the reason a `title_color=` would dissolve the palette); **no webfonts** —
a `<link>` to a font CDN is exactly what the linter's `no-external-css` rule denies, and an
`@font-face` block fetches a font file the major clients strip or ignore, which is why the
terminal-generic rule is the guarantee instead; no
font-size or weight in this vocabulary, because those are #45's axis and #56's whole claim is
that a face swap moves **no px**; and one theme per email, since a face is an email-level voice
exactly as a palette and a density are.

- **The alignment epic (#124) is complete** — #125 normalised the two spellings, #126 gave
  containers an `align`, #127 gave the five prose components one, #128 landed
  `aligned_layout` and these docs. See *Alignment — geometry, not a fourth design axis*
  above for the model. Four things it leaves:
  - **A byte-verified diff is not a verified render.** #125's golden diff was
    script-verified to contain only alignment declarations and was *still* a visual
    regression in every email: pairing `base.html`'s outer cell with a `text-align` style
    un-centred the email frame **and** centred every paragraph, because that attribute is
    doing block alignment. #126 fixed it and added the browser guard. Screenshot the change.
  - **The epic found three defects no golden could see**, which is the strongest evidence
    yet for standing rule 3: that regression, #129's shrink-wrapping column cells, and
    #130's body copy escaping its own styling element — the last of which had shipped
    since the beginning, rendering prose in `font.label` and silently falsifying #56's
    claim that `body` is a separate role.
  - **The obvious fix is worth measuring before believing.** #129's issue proposed
    `width="100%"` on the cell; it changes nothing, because the cell resolves that width
    against an anonymous table that is itself shrink-wrapping. A fixed px width fills on
    desktop and then constrains the copy at the mobile breakpoint. Only `inline-table` —
    keeping the column a table box — actually works, and it was the fourth thing tried.
    #76 taught this once already.
  - **A regression test scoped to the fixtures that had the bug is how the next instance
    hides.** #76's viewport check watched three fixtures; widening it to the gallery in
    #129 immediately found `rich_table` overflowing a phone by 24px, unnoticed since #121.
  - **A guard that only works when the code is correct is not a guard.** #130's first probe
    selected `div.body-text`; reverting the tag made it match nothing and pass green.
    Perturb the code and watch the test fail, every time — it selects by class now.
  - **A completeness rule pays for itself on the layer nobody checked.** Widening standing
    rule 9 to containers immediately found that `Container.background_color` — the
    *original* entry in the closed colour list — had never been set by any fixture.

- **The typography epic (#56) is complete** — #104 built the vocabulary, #105 put `font_theme`
  on the existing binder, #106 migrated the templates in two commits, #107 shipped `modern` and
  its fixture. **The design system now has all three axes**, and they are deliberately the same
  shape: one email-level field, resolved once in `render()`, bound as a shared value, read as a
  namespace in every template, with a preset registry and a gallery fixture per preset. Three
  things it leaves:
  - **Ride the binder; there is still only one.** `TemplateEngine.bound(theme=…, size=…,
    font=…)` now carries three values and no container, component or region has ever changed
    signature to accept any of them. A fourth email-level value should be the fourth keyword,
    not a fourth mechanism.
  - **A vocabulary migration normalises before it tokenises.** The two spellings of one stack
    are the general case: an axis's literals accumulate variants that are equal to a browser
    and different to a golden. Splitting the commit is what lets the reviewer read "the
    spelling moved, 250 lines" and "the mechanism moved, 0 lines" separately.
  - **A sentinel render catches what a golden structurally cannot.** The goldens are
    byte-identity, so a literal left behind is *correct output* to them. Rendering under a
    theme whose every token is a findable sentinel, and asserting no shipped value survives,
    is the check that found the one declaration #106's migration missed — and it is the
    technique to reuse on any axis that claims to have tokenised everything.

- **The banner epic (#88) is complete** — #89 split the masthead from the strip, #90 renamed
  `Header` → `Banner`, #91 gave the headline free-form copy with resolution chains, #92 added
  the department, #93 added `BannerPalette`, #94 landed `custom_banner` and these docs. Three
  things it leaves for whatever comes next:
  - **A caller-supplied surface is what earns a palette.** `BannerPalette` is the standing
    colour rule's single named exception, and the reason is specific rather than
    region-shaped: the masthead is the one place the *caller* supplies the backdrop. The
    scoping is enforced, not just described — the palette covers the banner **slot**, and the
    strip in the same region keeps the theme's tokens.
  - **A presentation field whose fallback is a fact resolves into a key of its own.**
    `banner_title` / `banner_subtitle`, never `firm_name` / `campaign_name` in place. Resolving
    in place would be a region shadowing a fact, which the layering exists to prevent, and the
    render would still work — so a grep test holds it rather than a convention.
  - **The goldens cannot see layout.** #92's placement, the 2×2 pairing and the mobile
    overflow that `white-space:nowrap` reintroduced are all byte-identical questions the
    snapshots answer "fine" to. They live with the screenshots for the reason #76 established.

- **Both theme epics are complete (#46 colour, #45 size).** Three techniques carried from
  one to the other, and worth carrying to the next:
  - **The injection mechanism is built — ride it, do not build a second one.** #48 made the
    choice #40 was told to make: `TemplateEngine.bound(**shared)` returns a per-render
    `BoundEngine`, so nothing in the section tree changed signature. #40 added `size` as
    another shared value on the same binder and touched no container, component or region.
    A future email-level value should do the same.
  - **The audit pattern is worth repeating.** Naming tokens by *role* rather than by value
    is what turned 245 colour literals into a vocabulary, and the same move on ~200 size
    literals surfaced a threshold nobody had written down: column padding steps at 300px.
    A value-keyed substitution would have been byte-identical and useless.
  - **Byte-identity is provable before the intended change.** #49 restored the one comment
    it meant to alter, ran the goldens green, then re-applied it — so the golden diff in the
    PR was exactly the intended change and nothing else. #45 went one better and needed no
    diff at all: every one of its four migration steps left all six pre-existing goldens
    untouched, and the only new files are the two fixtures it shipped.

## The sizing audit — how the token values were established

Moved out of `pyhermes/builder/sizing.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
The email's size vocabulary — one validated object per density.

Sizes were 57 ``font-size`` declarations, 50 ``line-height`` values and
roughly 90 padding/margin literals spread across 20 template files, plus the
680px frame arithmetic written out twice per column in eight container
templates. An implied scale clearly existed; nothing named it, nothing owned
it, and nothing could vary it. This module is that owner.

::

    EmailMetadata.size_theme        ("compact" | "standard" | "spacious")
            |  resolved ONCE in Email.render()
            v
    SizeScheme                      (frozen, validated at construction)
    +-- type       TypeScale        font sizes + the shared line-heights
    +-- space      SpacingScale     section, column, region and rhythm spacing
    +-- component  ComponentScale   sizes that do not follow the global scale
    +-- frame      FrameGeometry    outer width and padding; column widths
                                    are arithmetic over this, not literals
            |  bound onto the engine as one namespace
            v
    templates read {{ size.type.body }}, {{ size.space.gutter }}, ...

**Callers pick a theme, never a px.** ``size_theme`` accepts a
:class:`~pyhermes.builder.enums.SizeTheme` member or its bare string and nothing
else — deliberately narrower than ``theme``, which also accepts a custom
:class:`~pyhermes.builder.theming.Theme`. The asymmetry is the point: a palette is
an email's voice and a house style may legitimately need its own, whereas
density interacts with the 102 KB clipping limit, Outlook's Word engine and
the mobile collapse all at once. A scheme nobody has rendered in a real
client is a compatibility claim nobody has tested. Widening this later is
additive; narrowing it would not be.


The audit — token, value, and the sites each one covers
-------------------------------------------------------

Every number below was read out of the templates before anything moved, and
``STANDARD`` reproduces each one exactly. ``r/`` is ``regions/``, ``c/`` is
``common/containers/``.

**type** — font sizes (px) and the line-heights shared across components::

    title            28    r/header, r/header-minimal (firm name)
    title_mobile     22    base.html .mobile-title override
    section          17    the <h2> in every container; numbered-list ordinal
    subheading       16    r/footer-contact heading
    item_title       15    text/numbered-list item title
    body             14    container cell default, text/text-block prose,
                           text/numbered-list body, text/author-block name
    secondary        13    every component subtitle, masthead campaign name,
                           analysis/data-table cell, card body,
                           r/footer-contact description and CTA label
    small            11    masthead date/issue bar, author job title + email
    label            10    analysis/data-table column header
    micro            9.5   card label and sublabel, chart/table source,
                           image caption, masthead disclaimer bar,
                           r/footer-legal disclaimer and copyright

    title_line       1.2   title, section <h2>, card value, list ordinal
    heading_line     1.3   campaign name, list item title, author name
    body_line        1.72  container cell, text-block prose
    secondary_line   1.4   subtitles, card sublabel, disclaimer bar,
                           author job title

**space** — spacing, in px. ``pad_x`` (32) lives on the frame, since the
frame's horizontal padding is what makes the content 616 wide::

    gutter                    16   between columns (margin-right + ghost table)
    section_title_top         22   section <h2> cell, top (full-width and split alike)
    section_title_bottom      12   section <h2> cell, bottom
    content_top               16   c/full-width content cell, top
    content_bottom            14   c/full-width content cell, bottom
    column_top                 2   a column cell, top
    column_bottom             26   a column cell, bottom
    column_pad_x              20   a column at least frame.narrow_column wide
    column_pad_x_narrow       16   a column narrower than that
    mobile_pad_y / _x       20/18  base.html .mobile-pad override
    block_gap                 16   text-block paragraph, between list items
    subtitle_gap              12   below any component subtitle
    caption_gap                8   above a source, caption, or card body
    masthead_bar_y             7   disclaimer bar
    masthead_top              18   the masthead block, above the title/logo
                                   row
    masthead_title_bottom      6   between the title/logo row and the
                                   subtitle/department row
    masthead_campaign_bottom   8   below the subtitle/department row
    masthead_meta_top         10   date/issue bar, top
    masthead_meta_bottom      18   date/issue bar, bottom
    masthead_vml_height      180   the v:rect box Outlook draws instead of
                                   the CSS background image; see the note
                                   below — it is not a bound on the content
    footer_contact_top         8   contact band, top
    footer_contact_bottom     30   contact band, bottom
    footer_legal_top          20   disclaimer band, top
    footer_legal_bottom        8   disclaimer band, bottom
    footer_copyright_top       6   copyright band, top
    footer_copyright_bottom   24   copyright band, bottom

**component** — what does not follow the global scale::

    kpi_value             21    card value font-size
    card_pad_y / _x     14/16   a vertical card's cell — and, deliberately,
                                base.html's .kpi-cell mobile override, since
                                the collapse *is* the vertical layout
    kpi_pad_y / _x      16/12   a horizontal KPI cell
    card_label_gap         6    below the card label
    card_value_gap         4    below the card value
    card_body_line       1.6    card prose
    table_cell_pad        12    analysis/data-table <th> and <td>
    table_cell_pad_mobile  6    the same cells under the mobile breakpoint (#132)
    list_ordinal_width    22    the ordinal column
    list_ordinal_gap      12    between ordinal and item body
    list_title_gap         6    below a list item's title
    list_body_line       1.68   list item prose
    author_name_gap        4    below the author's name
    author_sep_gap         4    around the middot between title and email
    author_rule_gap       14    above the byline, both halves of the rule
    cta_width            150    contact button, VML and CSS alike
    cta_height            38    ditto (VML height == CSS line-height)
    contact_pad_y / _x  22/24   inside the contact card
    contact_heading_gap    6    below the contact heading
    contact_cta_gap       16    above the contact button
    contact_line         1.55   contact description
    legal_line           1.6    footer disclaimer

**frame** — the geometry every column width is derived from::

    width              680   the outer email table
    pad_x               32   its horizontal padding, so inner == 616
    outer_pad_y         28   the wrapper band above and below the email
    mobile_breakpoint  700   the @media max-width that collapses columns
    narrow_column      300   at or above this, a column takes the wider
                             horizontal cell padding; below it, the narrower

Four line-heights say the same thing
------------------------------------

``body_line`` 1.72, ``list_body_line`` 1.68, ``card_body_line`` 1.6 and
``legal_line`` 1.6 / ``contact_line`` 1.55 are five spellings of "roomy"
that differ only because they were typed in five files. The audit records
that rather than fixing it: collapsing them changes rendered output, and
this epic's whole claim is that ``STANDARD`` does not move. They are named
by site so a later PR can collapse them deliberately, with a golden diff
that is the point rather than the problem.

Deliberate literals — sizes that stay hardcoded
-----------------------------------------------

A px value in a template is a bug *unless* it is one of these, each of which
is structural rather than scale-participating:

* ``font-size:1px`` on the preheader — a hider, not type.
* ``font-size:0; line-height:0`` on the accent rule's spacer cell, with
  ``height="1"`` — a 1px rule drawn with a border, not a line of text.
* ``padding:1px 1px 1px 1px`` on a highlighted container — the hairline
  frame itself.
* ``border-width`` (1px, 2px), ``border-radius`` (3px, 4px) and
  ``arcsize="8%"`` — shape, not density.
* ``letter-spacing`` (0.2–0.6px) — optical correction for uppercase micro
  type; it tracks the typeface, not the scale.
* ``text-shadow`` offsets and ``max-width:{{ logo_width }}px`` — the latter
  is the caller's own number.

Validation
----------

Every token is a positive ``int`` or a **non-integral** ``float``. That
second half is not fussiness: a scheme storing ``14.0`` would render
``font-size:14.0px``, which is legal CSS and a byte-identity failure, and
the one genuinely fractional size in the email (``micro`` = 9.5) means the
rule cannot simply be "ints only". Line-heights obey the same rule, so
``1.72`` is fine and ``2.0`` is rejected in favour of ``2``.
```

## The colour audit — how the palette's roles and values were established

Moved out of `pyhermes/builder/theming.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Theming — every colour and shadow in the email, as one validated object.

Colour used to be 18 distinct hex values in 245 occurrences across all 20
template files, plus three ``rgba()`` literals and three Python-side
fallbacks. A palette *comment* in ``base.html`` named 13 roles, but it was
dead text: it could not be read by anything, and it had already drifted (see
the audit below). This module is what replaces it — a named home for every
value, frozen and validated, so a caller can re-skin the newsletter from one
field instead of forking 20 templates.

**The theme is the unit of customisation, never a single colour at a call
site.** Coherence survives because the whole theme is the atom: the layers
are frozen, no token field is optional, and every value is validated at
construction. There is no way to build a ``Theme`` that later fails a render
under ``StrictUndefined`` — completeness is structural, not remembered.

Four layers, because they answer different questions:

============== ==================================================
:class:`Palette`        surfaces and structure — what the email is made of
:class:`TextColors`     the type, on light grounds and on the navy masthead
:class:`SemanticColors` what a *number* means; defaults and fallbacks only
:class:`ShadowStyle`    the three composed ``rgba()`` values
============== ==================================================

``SemanticColors`` deserves its own note. ``KpiItem.color`` and
``TableRow.colors`` are the caller's statement about the **data** ("this
number is down"), not a styling choice — they stay caller-supplied. The
theme provides only what is used when the caller says nothing.

The audit
---------

Every default below is exactly what the templates hardcode today. Occurrence
counts are over ``pyhermes/builder/templates/``; the palette comment's own 13
lines are excluded from "renders in".

Palette
    ``wrapper_bg``     ``#F2F1EE``  13×  base, footer-legal — the warm stone padding,
                                         and the preheader text hidden against it
    ``surface``        ``#FFFFFF``  63×  everywhere — the white email body
    ``header_bg``      ``#2C3E50``   9×  the masthead band — soft navy
    ``accent``         ``#5B8A9A``   9×  links, the CTA button, rules — muted teal
    ``rule``           ``#D6D2CB``  33×  the standard hairline, all 8 containers
    ``rule_subtle``    ``#EAE8E4``   2×  data-table row separators, author-block top
    ``rule_dark``      ``#2C3E50``   1×  the section-title underline
    ``highlight_tint`` ``#F8F7F5``  27×  ``highlight=True`` in all 8 containers
    ``row_alt``        ``#F8F7F5``   9×  data-table alternating rows

TextColors
    ``primary``        ``#3B3B3B``  26×  body copy
    ``secondary``      ``#7A7A72``  12×  captions, sources, sublabels
    ``light``          ``#A09E97``   6×  as-of lines, the copyright line
    ``heading``        ``#2C3E50``  11×  section titles, table headers, author name
    ``fine_print``     ``#8A8880``   1×  the footer disclaimer
    ``on_dark``        ``#FFFFFF``   2×  the firm name over navy
    ``on_dark_secondary`` ``#CFD8DC``  2×  the campaign name over navy
    ``on_dark_muted``  ``#90A4AE``   6×  header disclaimer, date range, issue label
    ``on_accent``      ``#FFFFFF``   2×  the contact CTA's label, on the accent fill

SemanticColors
    ``positive``       ``#4A7C59``   0×  **no render site today** — see below
    ``negative``       ``#B85450``   0×  **no render site today** — see below
    ``neutral``        ``#5A5A5A``   2×  the data-table header row and its cell
                                         fallback; also what an unset
                                         ``Card.color`` resolves to

ShadowStyle
    ``scrim``          ``#141E2C`` @ 0.65  the header hero's legibility overlay
    ``title``          ``#000000`` @ 0.4   ``text-shadow`` on the firm name
    ``subtitle``       ``#000000`` @ 0.3   ``text-shadow`` on the campaign name

Four things the audit found, recorded rather than quietly fixed
---------------------------------------------------------------

* **The palette comment was wrong, not merely incomplete.** It named "Row alt
  ``#F5F4F1``", but ``data-table.html`` alternates rows with ``#F8F7F5`` — the
  same value as the highlight tint. ``#F5F4F1`` appears nowhere else in the
  repo. The *role* was real; the value the comment claimed was not, which is
  precisely the failure mode a comment nothing can read is prone to.

* **``row_alt`` and ``highlight_tint`` are separate tokens that happen to
  share a value.** Collapsing them would make the coincidence permanent and
  deny a theme author the distinction the comment itself drew.

* **``rule_dark`` is ``header_bg``'s value by design, and stays a distinct
  token** for the same reason — a section heading's underline matching the
  masthead is a decision a theme may want to keep or break.

* **``default_color`` and ``validate_hex_color`` were registered filters that
  no template called.** ``default_color``'s ``#5A5A5A`` was therefore a
  literal in a code path nothing exercised. The migration puts the filter to
  work — ``{{ card.color | default_color(theme.semantic.neutral) }}`` — which
  removes the literal, resolves an unset ``Card.color`` against the live
  theme, and validates an explicit one on the way through.

* **``positive`` and ``negative`` render nowhere by default.** They live in
  the docstring examples and in callers' own ``KpiItem`` data. They are
  tokens here because they are the vocabulary the palette comment published
  and callers already use — but tokenising them changes no byte, and nothing
  in the templates reads them.
```

## The typeface axis — how the font roles and stacks were chosen

Moved out of `pyhermes/builder/typography.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
The email's typeface vocabulary — one validated object per house voice.

Faces were the last hardcoded axis of the design system. Colour became a
resolved :class:`~pyhermes.builder.theming.Theme` in #46 and density a resolved
:class:`~pyhermes.builder.sizing.SizeScheme` in #45, but ``font-family`` stacks
stayed baked into the templates: repeated per declaration, unnamed,
unvariable. A newsletter wanting a different house face forked templates.
This module is that owner.

::

    EmailMetadata.font_theme        (a preset name, or a FontTheme)
            |  resolved ONCE in Email.render()
            v
    FontTheme                       (frozen, validated at construction)
    +-- heading    FontStack        masthead title, section titles, item titles
    +-- body       FontStack        prose, the page default, KPI values
    +-- label      FontStack        meta, captions, table text, footer, chrome
    +-- numeric    FontStack        the data table's figure columns

**The audit this module is pinned to** — every ``font-family`` declaration in
``pyhermes/builder/templates/``, 2026-08-28. Three stacks, 49 declarations:

===========================================  =====  ==============================
stack                                        count  drawn at
===========================================  =====  ==============================
``Georgia, 'Times New Roman', serif``           21  the page default (``<body>``
                                                    inline **and** the ``[if mso]``
                                                    ``body, td, th`` fallback),
                                                    masthead title, section titles,
                                                    italic subtitles, item titles,
                                                    list ordinals, prose body, and
                                                    the **KPI values**
``Arial, Helvetica, sans-serif``                27  the strip, masthead subtitle /
                                                    meta / department, card labels
                                                    and sublabels, table headers and
                                                    cells, captions, contact copy,
                                                    the footer
``'Courier New', Courier, monospace``            1  the data table's non-first
                                                    columns, via ``{% if
                                                    loop.first %}`` — the figures
===========================================  =====  ==============================

**Four roles, not three, and the difference is the whole point.** Naming them
after the values — ``serif`` and ``sans`` — is the mistake the colour and size
audits each existed to avoid, and here it would also be *wrong*: the serif is
not "headings", it is the editorial voice, and it sets the KPI numerals as
readily as the masthead. A preset that wants a sans masthead over a serif body
— the motivating variant — needs ``heading`` and ``body`` separately
addressable, so the vocabulary is cut by the job a face does rather than by
which face happens to do it today. That ``heading`` and ``body`` are the same
stack in the default is a fact about the default, not about the roles.

**A stack is the atom, never a face.** Every :class:`FontStack` must end in a
CSS generic family, because in email the fallback chain *is* the rendering:
Outlook's Word engine walks the chain and lands wherever it lands, so the
generic is the floor that makes a custom face safe rather than a gamble. That
rule is checkable without maintaining a list of "websafe" names that would rot,
and it is what lets ``font_theme`` accept a caller's own object where
``size_theme`` accepts only a preset name.

**Weights, italics and letter-spacing stay literal, and that is a decision.**
The audit found ``font-weight`` at ``bold`` (16), ``400`` (2) and ``300`` (1),
plus ``font-style:italic`` (10). These are structural emphasis riding the role
sites — the same call ``border-width`` and ``letter-spacing`` got in #45: shape
rather than voice. Numeric weights beyond 400/700 are also unreliable in the
Word engine, which synthesises what a face does not supply. A theme that wants
a lighter voice picks a lighter *face*, in the stack, where the fallback chain
can be reasoned about.
```
