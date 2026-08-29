---
paths:
  - "svc/builder/theming.py"
  - "svc/builder/sizing.py"
  - "svc/builder/typography.py"
  - "svc/builder/enums.py"
  - "svc/builder/containers.py"
  - "svc/builder/templates/**/*"
---

# The four design axes — colour, size, typeface, alignment

### Theming — colour is one validated object

Colour was 18 hex values in 245 occurrences across all 20 template files, three `rgba()`
literals and three Python fallbacks, described by a palette *comment* in `base.html` that
nothing could read — and that had already drifted, naming a row-alt colour the data table
never used. Epic #46 replaced it with [svc/builder/theming.py](../../svc/builder/theming.py).

```python
from svc.builder import DEFAULT_THEME, Palette, Theme

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
two sources is the drift this module exists to end. Three tests hold the wiring: the templates
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
[svc/builder/sizing.py](../../svc/builder/sizing.py).

```python
EmailBuilder().metadata({..., "size_theme": "compact"})     # or "standard" / "spacious"
```

`EmailMetadata.size_theme` → resolved **once** in `Email.render()` → four frozen layers
(`type`, `space`, `component`, `frame`) → templates read `{{ size.type.body }}`.

- **Callers pick a theme, never a px — and here that is stricter than colour.** `size_theme`
  accepts a `SizeTheme` member or its bare string and **nothing else**, where `theme` also
  accepts a custom `Theme` object. The asymmetry is deliberate: a palette is an email's voice
  and a house style may legitimately need its own, whereas density interacts with the 102 KB
  clipping limit, Outlook's Word engine and the mobile collapse all at once — a scheme nobody
  has rendered in a real client is a compatibility claim nobody has tested. Widening this
  later is additive; narrowing it would not be.
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

**Non-goals, as decisions**: no free-form size parameters (`size_theme` is the whole surface);
**no narrow-frame theme** — all three keep the 680px frame, and #42 made width *derivable* so
that shipping a different one becomes a deliberate act with its own client-testing burden and
its own interplay with image `width=` attributes, rather than a side effect; one theme per
email, since density is an email-level voice; and no font theming — which stopped being a
non-goal when #56 landed, and is the axis below.

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
[svc/builder/typography.py](../../svc/builder/typography.py).

```python
from svc.builder import DEFAULT_FONTS, FontStack

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
