---
paths:
  - "svc/builder/**/*"
---

# The builder's composition model, ownership rule and public API


`svc/builder/` is the shared kit. Its public surface is re-exported from
[svc/builder/__init__.py](../../svc/builder/__init__.py).

**Superseded (#158): "`svc/builder/` is the only implementation."** It was, until the
medium was named. A `Medium` now owns the skeleton, the slot contract and the constraints
a composed document must pass, and `svc/email/` owns the shipped email one — including the
102 KB Gmail check, which is a fact about a client rather than about rendering. Epic #157
moves the rest of the email-only half there; the kit keeps what every medium shares.

(A legacy flat string-replace assembler, `svc/assembler.py`, was removed in #14. It is
recoverable from git history if ever needed for reference.)

### The four-layer composition model

Every email is `skeleton ← regions (header | banner | body | footer) ← containers ← components`:

| Region | Slot | Variants | What it is |
|---|---|---|---|
| `Header` | `header_bar_html` | `EmptyHeader` | The strip at the very top: one band of free-form copy |
| `Banner` | `banner_html` | `MinimalBanner` | The masthead: headline, logo, department, dates |
| *(the body)* | `sections_html` | — | The ordered section list, deliberately not a class |
| `Footer` | `footer_html` | — | The closing block: copyright, links, optional disclaimer |

**Each region owns exactly one slot, and a test asserts it.** Between #89 and #95 the banner
owned two — the strip had its own template and its own slot but someone else's class — and #95
promoted it. That the skeleton's slot set never changed across either step is what made the
split a change of *owner* rather than of markup, and it is the strongest evidence the region
mechanism generalises.

1. **Skeleton** — [svc/builder/templates/base.html](../../svc/builder/templates/base.html). The full HTML page (head,
   preheader, palette comment) with four variable holes: `{{ header_bar_html }}`,
   `{{ banner_html }}`,
   `{{ sections_html }}`, and `{{ footer_html }}`.
   Rendered last by [Email.render()](../../svc/builder/email.py).
2. **Regions** — the named areas of the email. Templates in
   [svc/builder/templates/regions/](../../svc/builder/templates/regions/); Python wrappers in
   [svc/builder/regions.py](../../svc/builder/regions.py), all sharing a `Region` base that owns
   validation, the image walk, the facts-over-presentation layering and `render_slots()`.
   Three region classes and two variants, per the table above. The **body region is
   the ordered section list** — deliberately not a class, since wrapping it would add a
   layer with no behaviour. The footer has no variant today; that is a gap, not a decision —
   `Footer.REQUIRED_SLOTS` means a variant may not drop the closing block, never that no
   variant may exist.
3. **Containers** — layout geometry only. In [svc/builder/templates/common/containers/](../../svc/builder/templates/common/containers/).
   Each produces a `<tr>` block sized to the 680px outer email table. Python wrappers in
   [svc/builder/containers.py](../../svc/builder/containers.py).
4. **Components** — content blocks. Templates in
   [svc/builder/templates/analysis/](../../svc/builder/templates/analysis/) and
   [svc/builder/templates/text/](../../svc/builder/templates/text/); Python wrappers in
   [svc/builder/components.py](../../svc/builder/components.py).

A `Container` holds one or more `Component`s, calls `component.render(engine)`, and embeds
the fragment into its own template. `Email` renders each region into the slots it fills,
concatenates all section HTML, and drops all of it into the skeleton. **Adding a content
type = new template file + new `Component` subclass** that sets `template_path` and
implements `context()`.

**A region fills its named slot(s)** — a region declares `SLOTS` (the skeleton's contract, fixed)
and `TEMPLATE_PATHS` (what *this variant* fills), and `Region.render_slots()` returns one HTML
string per slot in `SLOTS`, filled or not. That distinction is the whole variant mechanism: an
unfilled slot renders the empty string, so `EmptyHeader` omits the strip by declaring
`TEMPLATE_PATHS = {}` and the skeleton needs no conditional. `Banner.render()` survives as the
whole-region convenience and delegates to `render_slots()` — one rendering path, not two.

**"No fourth region" was a real decision, and #87 reopened it deliberately.** This file used to
say *"banner, body and footer are the complete set; a fourth region is a decision to reopen,
not a gap to fill."* It is recorded as superseded rather than deleted, because the reasoning
that retired it is worth keeping: the strip and the masthead were one region **only by accident
of file layout** — different content, different owner, different reasons to change — so the
fourth region was not a new idea bolted on but one that had been there all along, unnamed.

**The other half of that decision still stands: the preheader stays skeleton plumbing.** It is
a hidden `<div>` carrying inbox-preview text, not a named area of the email, and nothing about
it wants validation, an image walk or a presentation surface. A fifth region is still a
decision to reopen — and the bar #87 met is the one to meet: name the thing that is already
structurally separate, rather than find a gap to fill.

### The ownership rule — facts flow down

**Facts about the email live on `EmailMetadata`; how a region presents them lives on the
region.** Stated once, for all three: a region presents facts, it cannot own or contradict
them.

| Stays on `EmailMetadata` (facts / constraints) | Lives on the region (presentation) |
|---|---|
| `header_disclaimer` | `Header.align`, `background_color`, `text_color` (the shared `BoxSurface`) |
| `email_subject`, `preheader_text`, `language` | `Banner.background_image_url` |
| `firm_name`, `campaign_name` | `Banner.logo_url`, `logo_alt`, `logo_width` |
| (the same two, as the headline's fallbacks) | `Banner.title`, `subtitle`, `resolved_title()`, `resolved_subtitle()` |
| (the theme, as every colour's fallback) | `Banner.palette` — the masthead's own `BannerPalette` |
| `date_range`, `issue_label`, `header_disclaimer`, `department` | `Banner.resolved_logo_alt()`, `resolved_logo_width()`, `DEFAULT_LOGO_WIDTH` |
| `firm_name`, `current_year` | `Footer.align`, `background_color`, `text_color` (the shared `BoxSurface`), plus `border`, `border_color`, `image`/`image_alt`/`image_width` |
| `unsubscribe_url`, `view_in_browser_url` | `Footer.unsubscribe_label`, `view_in_browser_label`, `disclaimer` (optional, free-form HTML) |
| (those two + `firm_name`, `current_year`, as the row's default) | `Footer.link_row` — a `LinkRow` the caller composed; `None` builds the default row from the facts |

Two boundary calls, each made for a reason rather than by shape:

- **`header_disclaimer` is a fact, and the split is what let it travel for free.** It is legal
  copy that belongs to the email, not to any region's design. #95 moved it from `BANNER_FACTS`
  to `HEADER_FACTS` and handed it to the new region — the field itself never moved, because a
  fact was never the banner's to begin with. That is the fact/presentation rule paying for
  itself: a region change that would otherwise have been a data migration was a one-line
  reassignment.
- **`language` is a fact, and it is the one whose default is a claim rather than a
  blank (#115).** What language an email is written in is true of the email, like
  `firm_name` and `department` — so it sits on the metadata, not on a region. Two
  things about it are decisions rather than shape. It defaults to **`"en"`, not
  empty**: every other optional field's absence is neutral, but an absent `lang`
  makes a screen reader guess from the *recipient's* locale, so the field is
  required and validated rather than skipped when blank. And it validates the
  **shape, never the registry** — subtags of letters and digits joined by single
  hyphens, `_validate_url`'s philosophy on the other attribute a reader depends
  on. Whether `fr-CA` is a registered IANA subtag is not this library's business,
  and a lookup table shipped in a wheel goes stale between releases while a
  trailing hyphen stays wrong forever. **`dir` and RTL layout are deliberately not
  here**: mirrored table geometry is an epic with its own client-testing burden,
  and emitting the attribute without the layout would claim a support the
  templates do not honour.
- **The masthead's headline is presentation, and its fallbacks are facts (#91).** Until then
  the large type *was* `firm_name` and the second line *was* `campaign_name`, so an email
  leading with "Q3 Outlook" had to lie about who sent it. `Banner.title` / `subtitle` are
  free-form copy; unset, they resolve to those two facts. The resolution lands in **keys of
  its own** — `banner_title`, `banner_subtitle` — which the templates read *instead of* the
  facts, because resolving in place would be a region shadowing a fact, the one thing the
  layering exists to prevent. A test greps both templates so the chain cannot be quietly
  bypassed: reading `{{ firm_name }}` again would render correctly for every email that
  never sets a title, and make the field unreachable with nothing failing.
- **`department` is a fact, though the headline beside it is presentation (#92).** The desk
  an email comes from is *who sent it*, the same kind of truth as `firm_name` — putting it on
  the region would let two renders of one email disagree about its sender. It is optional, and
  absence **collapses rather than blanks**: the `{% if %}` guards the element, not its text, so
  an email that sets no department leaves no empty `<p>` and reserves no height.

**The masthead is a 2×2 grid, and that is what makes it fit.** The logo shares a row with the
title and the department shares one with the subtitle, rather than both stacking in a band
above the copy. Three things follow, and none of them is cosmetic:

- **It fits the Outlook hero box now; stacked, it never did.** `masthead_vml_height` is a
  `v:rect` the content cannot grow (`mso-fit-shape-to-text:false`), and the stacked masthead
  measured 178.6 / 207.5 / 244.6px against boxes of 150 / 180 / 220 — overflowing at every
  density, with the department taking it to ~46px over. Paired, it is 143.0 / 163.9 / 190.6px:
  inside the box everywhere, and the department costs nothing because it shares a row. Keep
  that headroom in mind before adding a masthead line, because exceeding it degrades quietly
  (the photograph stops, the flat band continues).
- **The left cell carries `width="100%"` so the right one shrinks to its content.** An explicit
  right-column width would have to be wide enough for the logo *and* the department, and
  whichever is narrower would then sit short of the frame edge.
- **The department wraps; it must not `nowrap`.** Keeping it on one line beside the subtitle
  looked right and reproduced #76 exactly: a real desk name pushed a 375px viewport to 572px.
  A browser test pins it, alongside the four that pin the pairing itself — the goldens can see
  `valign` and `align="right"` in the markup, and neither says where a box lands.
- **The footer's two URLs are facts**, though the header's `logo_url` is presentation. A
  logo is an image the *region* chose; an unsubscribe address is a property of the mailing,
  and `EmailMetadata.validate()` already checks both schemes. What the footer owns is
  the wording *around* them — the link labels — and the optional `disclaimer` block (free-form
  HTML, emitted raw and unwrapped; escaping untrusted text in it is the caller's job).

`EmailMetadata.BANNER_FACTS` and `FOOTER_FACTS` name what is handed down at render time.

The rule is **mechanical, not remembered**: `Region.context()` layers the email's facts *over*
its own keys rather than under them, so a region cannot shadow a fact even by accident — and a
test per region asserts the two key sets stay disjoint.

**The flat region keywords still work.** `EmailMetadata(logo_url=…, logo_alt=…, logo_width=…,
header_bg_image_url=…)` builds the header for you, so an email written before the header split
renders byte-identically. They are `InitVar`s — constructor arguments only, never attributes,
absent from `fields()`, `repr` and `==` — so the region stays the single owner. Passing them
*and* the explicit region raises rather than silently picking one.

Two consequences worth knowing: a bad masthead URL now raises at `EmailMetadata` construction
rather than at `.validate()`, and the message names `banner.logo_url` /
`banner.background_image_url` — where the field actually lives.

**An explicit region replaces the one the flat keywords built.** `Email(footer=…)`,
`set_footer()` and `EmailBuilder.footer()` are swaps, not merges, so a flat
`unsubscribe_label` alongside an explicit `footer=` is silently discarded — the conflict
check only fires inside `EmailMetadata`, where both spellings are visible at once. Put
presentation on whichever region actually renders; `qa/fixtures/minimal_footer.py` is the
worked example.

**The header and the footer are the email's two customisable boxes, and they share one
surface.** `BoxSurface` declares `align`, `background_color` and `text_color` once and both
regions mix it in, so the parity is *structural* rather than a convention someone has to keep
re-checking. `TestTheTwoBoxesShareOneSurface` is what makes that a rule rather than a hope: it
asserts both regions **inherit** the mixin rather than redeclaring the fields, that the shared
defaults match, that both validate identically, and that both resolve through
`theme_context()`. A claim with an enforcing test is a rule; one without is a wish.

What the mixin deliberately does *not* share is the tokens. The strip's box falls back to
`palette.header_bg` / `text.on_dark_muted` and the footer's to `palette.wrapper_bg` /
`text.fine_print` + `text.light` — parity that forced one token set on both would be parity as
costume, and a test pins that the two resolve to different backgrounds. The footer's
`text_color` is one knob over *two* theme tokens on purpose: a caller sets it because they set
a background, and recolouring only one of the two rows would leave the other illegible on the
new ground.

**The footer's row always renders; what is *in* it is the caller's call.** `REQUIRED_SLOTS`
makes an unfilled slot a `ValidationError` at construction, so a variant cannot drop the block
— `Footer` has no variant at all today (PR #86 removed the `MinimalFooter` that used to omit a
contact card the footer no longer renders). **That is a rule about variants, never about
callers**, and the distinction is the one thing here worth not eroding: pyHermes does not
require disclaimer language, an unsubscribe link, or any other content. It cannot know whether
an email is a commercial newsletter, an internal research note or a transactional receipt, and
each answers that differently — a library that guessed would be wrong for two of the three. So
`Footer.disclaimer` may be empty, `LinkRow(links=[])` renders a link-free row, and a row that
omits the unsubscribe destination renders exactly what the caller composed. The attribute was
described as a "compliance floor" until #100; that over-claimed in precisely this direction.

**The copyright row is a `LinkRow` (#100), not a template.** `© {year} {firm} · Unsubscribe ·
View in browser` was fixed structure — #64 parameterised the *labels*, but the *set* stayed the
markup's, so adding a "Privacy" link meant forking the file. `Footer.link_row` takes a
`LinkRow(copyright, links)`; `None` means today's behaviour, built from the email's own facts
and this footer's labels, which is why the default path is byte-identical and #64's label
fields still work. The trigger for making it an object is the one that made `Card` and
`TableRow` objects: **the row has a variable-length part, and variable length is what fields
cannot express.** The copyright keeps the `&copy;` **entity** rather than a bare `©` — this is
an email library, and U+00A9 mis-decoded as latin-1 renders as a mojibake pair. A caller's own
line is plain text, escaped by the resolver, which is why the template reads one already-HTML
key instead of branching.

**Both branches of that resolver escape to ASCII (#148), and the symmetry is the rule.** The
decision above applied to the *default* only: a caller writing `&copy;` got it escaped to
literal text, and a caller writing `©` got the raw bytes the decision exists to avoid — so the
one field with a recorded charset decision honoured it on one of its two paths. Both now go
through `escape_html_ascii`, which spells **every** non-ASCII character as a numeric reference:
scoping it to the symbol would be arbitrary, since an em dash mis-decoded is `â€"` in the same
way. Two things follow. The field stays **plain text** — a caller writes the character, never
the entity — because making it a raw-HTML surface would add a sixth to the closed list of five,
and this line renders inside a `p`, which #130 forbids. And the plain-text projection needs no
branch: the degrader decodes character references, so `_text()` still degrades the one source
`resolved_copyright_html()` produces.

**The filter is deliberately not applied to every plain-text field.** The charset exposure is
identical everywhere, so the narrow scope is a decision rather than an oversight: going global
costs bytes against the 102 KB budget — a reference is 8 where the character is 3 — and is a
policy change for the whole package, not a bug fix for one row. The gallery had been quietly
paying for the old behaviour: `kitchen_sink` and `custom_footer` both wrote their copyright
line *without a symbol at all*, which is what a caller does when the correct spelling does not
work.

### Public API (import from `svc.builder`)

```python
from svc.builder import EmailBuilder, Email, \
    Theme, Palette, TextColors, SemanticColors, ShadowStyle, Rgba, BannerPalette, \
    DEFAULT_THEME, SLATE_THEME, THEMES, \
    SizeScheme, TypeScale, SpacingScale, ComponentScale, FrameGeometry, \
    STANDARD_SIZES, COMPACT_SIZES, SPACIOUS_SIZES, SIZE_SCHEMES, \
    FontStack, FontTheme, DEFAULT_FONTS, MODERN_FONTS, FONT_THEMES, \
    Region, Header, EmptyHeader, Banner, MinimalBanner, Footer, \
    FullWidth, TwoColumn, ThreeColumn, \
    CardGroup, DataTable, ChartBlock, ImageBlock, TextBlock, NumberedList, AuthorBlock, ContactBlock
from svc.builder.models import Card, KpiItem, TableRow, Cell, Column, NumberedItem, EmailMetadata, \
    SectionConfig, LinkRow, FooterLink
from svc.builder.enums import TwoColumnRatio, ThreeColumnRatio, CardOrientation, \
    EmbedStrategy, ImageAlign, SizeTheme, ColumnAlign, ColumnKind, RowKind
from svc.builder.images import EmailImage, ImageAsset
```

**`Header` means the strip; it meant the masthead until #90, and no alias bridges the two.**
The name was *reused*, not retired — #90 renamed the masthead `Banner` and #95 gave the name
to the strip — so a deprecated warn-and-forward shim (the courtesy `KpiStrip` extends to
`CardGroup`) would have collided with the incoming class rather than eased the migration. The
break is clean and loud on purpose: between #90 and #95 `from svc.builder import Header`
raised `ImportError`, and since #95 an old-style `Header(logo_url=…)` raises `TypeError` at
construction, because the class answering to the name has no such field. Both fail at the call
site, immediately, which is the whole point — a name that quietly changed meaning would keep
running and be wrong. The flat keywords are unaffected and still build the masthead: they are
the common call path, and they never named the class.

Choosing a region is an argument, never a template fork — and there is no selection
mechanism beyond passing the object. Every region and variant works identically:

```python
Email(metadata, header=EmptyHeader(), banner=MinimalBanner(logo_url=logo))   # non-fluent
EmailBuilder().metadata({...}).header(Header(align="left")).banner(MinimalBanner()).section(...)
```

`EmailBuilder.header()` / `.banner()` / `.footer()` follow the same sequencing rule as
`section()`: calling one before `metadata()` raises `RuntimeError` — a programming error in the
call sequence, not rejected data. Omit them and the regions come from the metadata, which the
flat keywords built. `Email.header`, `Email.banner` and `Email.footer` are read-only accessors
for the same reasons as `Email.metadata`; use `Email.set_header()` / `set_banner()` /
`set_footer()` to swap them.

Column ratios and card orientation are `StrEnum`s in [svc/builder/enums.py](../../svc/builder/enums.py):
`TwoColumn`/`ThreeColumn` take a `ratio` and `CardGroup` takes an `orientation` as
**either the enum member or its bare string** (`ratio=ThreeColumnRatio.WIDE_LEFT` ==
`ratio="50-25-25"`), so the enums are an additive convenience — existing string calls are
unchanged. `enums.py` holds only the allowed values; the ratio→template mapping stays in
`containers.py`.

### Cards and the highlight property

Two deliberate shapes here, both chosen over adding more types:

- **`highlight` is a property of any container, not a container.** `Highlight` used to be a
  `Container` subclass, but its template was `full-width.html` plus a tint and hairline
  rules — presentation, not geometry. It was **removed**; use
  `FullWidth(..., highlight=True)`, which also works on `TwoColumn`. An explicit
  `background_color` still wins over the highlight tint.
- **`CardGroup` takes an `orientation`, rather than there being two components.**
  `horizontal` is the KPI strip (2–4 cards across); `vertical` stacks the same cards one
  per row — which is also what the horizontal strip collapses to on mobile, via the
  `.kpi-cell` rule in `base.html`. `KpiStrip` survives as a **deprecated alias** for the
  horizontal case and warns.

### Images and the asset manifest

An image carries two independent facts: **where the bytes live** (a hosted URL, a file on
disk, bytes in memory) and **how they reach the reader**. `EmailImage`
([svc/builder/images.py](../../svc/builder/images.py)) owns both, via three factories:

```python
from svc.builder.images import EmailImage

EmailImage.hosted("https://cdn.example.com/chart.png", alt="Factor returns")  # REMOTE
EmailImage.attached("charts/factor.png", alt="Factor returns", width=616)     # CID
EmailImage.inline(png_bytes, alt="Sparkline", width=120)                      # DATA_URI
```

| Strategy | Size cost | Gmail | Outlook desktop |
|---|---|---|---|
| `REMOTE` | none | proxied and cached | blocked until "download images" |
| `CID` | *message* size, **not** HTML size — does not count toward the 102 KB limit | renders; may show a paperclip | renders immediately, no prompt |
| `DATA_URI` | +33% base64, straight into the 102 KB budget | **stripped entirely** | Word engine will not render it |

**The builder declares CID embeds; it never performs one.** Attaching a MIME part is a
transport act belonging to a delivery service (`svc/gmail`, `svc/outlook`), so the builder
emits two things instead of one — the HTML, and an **asset manifest**:

```python
html = email.render()
for asset in email.assets():        # list[ImageAsset]
    message.attach(asset.data, asset.mime_type,
                   cid=asset.content_id, filename=asset.filename)
```

This is the seam the per-service layers plug into: **for every `src="cid:X"` in the HTML,
`assets()` has the entry describing what to attach as `X`.** Only `CID` images appear —
hosted images have no bytes and data URIs carry their own. `ImageAsset.content_id` is
**bare**: the `cid:` prefix (HTML) and the `<>` (MIME header) are each added by whichever
consumer needs them.

Aggregation walks the section tree without rendering it: `Component.images()` →
`Container.components()` → `Email.assets()`. `Email.images()` is **header + banner + sections
+ footer**: the masthead's `logo_url` and `background_image_url` reach the manifest through
`Banner.images()`, not through the metadata, and both accept an `EmailImage` as well as a
bare URL string. No shipped header or footer carries an image, and both are walked anyway —
the slot has to exist before a variant with a signature block or social icons is written, or
its bytes drop silently. **A new image-bearing component — or region — must override `images()`** or
its bytes never reach the manifest, and its `cid:` reference will render as a broken image.
(A component must also join `kitchen_sink()` — see the standing rules in
`working-in-the-code.md`, which a test enforces.)

Rules the module enforces at construction, per the validation philosophy below:

- **Format is sniffed from magic bytes, not the file extension** — PNG, JPEG and GIF only.
  WebP and SVG are detected specifically so the rejection can say why (Outlook's Word engine
  renders neither, and SVG can carry script).
- **`alt` is required, with one named exception.** It is what the reader sees whenever images
  are blocked, which for Outlook desktop is the default state. The exception is
  `decorative=True` (#149), which emits `alt=""` — **an assertion, not an absence**: omitting
  the attribute makes a screen reader announce the filename, and any string makes it announce
  the decoration, so the empty string is the only correct value for an image carrying no
  information. It cannot be reached by passing `""`; that still raises, and the message now
  names the opt-out. Supplying both raises too — they are contradictory claims about one image.
  The opt-out is on `EmailImage`, `coerce_image` and `ImageBlock`, and deliberately **not** on
  `ChartBlock`: a chart is never decorative. Region images (`Banner.logo_*`, `Footer.image_*`)
  resolve alt through their own fallback chains and were left alone; giving them the opt-out is
  a separate decision.
- **A decorative image declares itself in the markup**, with `role="presentation"` beside the
  empty `alt`. This is standing rule 8's lesson on a second element: `alt=""` deliberate and
  `alt=""` forgotten are **identical in the render**, so a guard reading the HTML cannot tell
  them apart and the annotation is what does. The `img-alt` lint rule is enforced **both ways**
  like `table-role` — an empty alt without the role fires, and the role *with* alt text fires —
  so the marker cannot drift from the thing it marks. The projection mirrors it: a decorative
  image contributes nothing to the text part rather than an empty `[]`, though its caption
  still projects, because a caption is copy either way.
- **Content-IDs are content-addressed** — `sha256(bytes)[:16]` by default, so the same image
  used in two sections is attached once, and the same input always yields the same output.
  An explicit `content_id` is checked against `[A-Za-z0-9._+-]{1,128}`.
- **Inline images are capped** at `Config.inline_image_limit_kb` (48 KB of base64;
  `INLINE_LIMIT_KB` is the mirrored default) so one image cannot eat
  the 102 KB budget; over that raises `SizeError` naming `EmailImage.attached()` as the fix.
  A whole-email `SizeError` additionally reports how much base64 the inlined images
  contributed.
- **`width` is emitted as the HTML attribute**, not just CSS, because Outlook's Word engine
  ignores `max-width`. For a retina asset pass the *display* width, not the file's.

`ImageBlock` is the generic image component (optional caption, link, alignment);
`ChartBlock` is the charting specialisation that adds the border and attribution line. Both
accept an `EmailImage` **or** a bare URL string, so every pre-existing call site keeps
working unchanged.

### Parameters and defaults

Anything that is not **core controlled formatting** should be passable, with a default that
reproduces today's output — so an existing email renders unchanged unless it opts in.

- **Alt text is always a parameter.** `ImageBlock`/`ChartBlock` take `alt`; the masthead
  logo takes `Banner.logo_alt`, which resolves **explicit banner value → the `EmailImage`'s
  own `alt` → `firm_name`**. `logo_width` resolves the same way, ending at
  `Banner.DEFAULT_LOGO_WIDTH` (90). The chains live on the region, and `firm_name` is a
  *parameter* to `resolved_logo_alt()` rather than a field — the header is handed the fact,
  it does not hold it. Defaults still reproduce the pre-split output.
  `Banner.background_image_url` is a CSS background, and a CSS background cannot carry alt
  text — it is decorative by construction.
- **The masthead's copy is a parameter, with the fact as its default.** `Banner.title` and
  `Banner.subtitle` follow `logo_alt`'s shape exactly — a presentation field, a resolution
  chain, the fact arriving as a *parameter* to `resolved_title()` rather than as a field.
  Both are **plain text and escaped on the way out**: "free form" means arbitrary copy, not
  markup, and the raw-HTML surface stays where it already is (the disclaimers,
  `TextBlock.content`).
- **Footer copy is parameterised** and lives on the `Footer` region:
  `unsubscribe_label`, `view_in_browser_label`, and the optional `disclaimer` (free-form HTML).
  Defaults reproduce what `base.html` used to hardcode, so a newsletter in another language no
  longer needs a template fork. The contact call-to-action is no longer part of the footer —
  use `FullWidth(content=ContactBlock(heading=…, cta_url=…))` as a body section instead.
- **Colour is a parameter — but the whole `Theme` is the atom.** A caller picks a preset or
  builds a theme; they never set a colour at a call site. The masthead has a second atom,
  `Banner.palette` (a `BannerPalette`), for the one surface a caller supplies — same shape,
  same rule, bounded to one region. See *Theming* in `design-axes.md`.
- **Density is a parameter — but the atom is the whole `SizeScheme`, and only by name.**
  `EmailMetadata(size_theme="compact")` is the entire caller-facing sizing surface. See
  *Sizing* in `design-axes.md`.
- **The typeface is a parameter — but the atom is the whole `FontTheme`.**
  `EmailMetadata(font_theme="modern")`, or a `FontTheme` object, is the entire caller-facing
  typography surface. See *Typography* in `design-axes.md`.
- **Not parameters, deliberately**: any individual px anywhere, and any individual face at a
  call site. Padding, the 680px frame and the faces are no longer *fixed* — a theme moves all
  three — but none of them is something a caller sets per email or per component. That
  distinction is the whole of the rule: **callers pick a theme, never a px and never a
  family.** A `font_size=` or a `font_family=` on a call site would dissolve the design system
  one component at a time, exactly as a `title_color=` would dissolve the palette, and a
  template that stops surviving Outlook is how it would show up. A test introspects every
  exported class and fails if such a parameter ever appears.

### Validation philosophy

Validation runs at **construction time**, not render time. Models (`KpiItem`, `TableRow`,
`NumberedItem`, `EmailMetadata`) and components raise `ValidationError` from their
`__init__`. By the time you call `.render()`, the data shape is already known good.
**Preserve this pattern** when adding components — validate in `__init__`, not in `context()`.

### Exceptions

All errors inherit from [EmailBuilderError](../../svc/builder/exceptions.py): `TemplateError`
(Jinja load/render), `ValidationError` (data shape), `SizeError` (102 KB limit). Catch the
base class for "anything the builder rejected" — that now holds without exception, including
inside a template render: the `validate_hex_color` / `default_color` filters raise
`ValidationError`, not a bare `ValueError` (#18). A filter's `ValidationError` propagates
out of the render as-is rather than being re-wrapped as `TemplateError`: it is a data
failure, not a template one.

The one deliberate exception is `EmailBuilder`'s `RuntimeError` for calling `section()` or
`build()` before `metadata()` — a programming error in the call sequence, not rejected
data.

### Hard constraints baked into the engine

- **102 KB Gmail clipping limit** — [Email._validate_size()](../../svc/builder/email.py) raises
  `SizeError` above 102 KB and warns above 90 KB. The single most important runtime check;
  never disable it without confirming a non-Gmail channel. Both thresholds come from
  [Config](../../svc/config.py) at check time, so a non-Gmail channel can raise them deliberately
  rather than by commenting the check out.
- **Jinja2 `StrictUndefined`** — [TemplateEngine](../../svc/builder/engine.py) fails fast on a
  missing template variable. New template vars need a matching key in the component's
  `context()` dict, or the render raises.
- **Autoescape is OFF, and escaping is split by field kind** (#12). HTML emails need raw
  output, so escaping is explicit rather than automatic:
  - **Plain-text fields are escaped by the builder**, in the templates, via the
    `escape_html` filter — section titles, subtitles, KPI labels/values/sublabels, table
    headers/cells/source/as-of, chart alt text and source, author name/title/email,
    numbered-item number and title, and the plain metadata fields. **Pass these as raw
    text**; pre-escaping them now double-escapes (`&` would render as `&amp;`).
  - **HTML fields are emitted raw**, because callers deliberately pass markup:
    `TextBlock.content`, `NumberedItem.body`, `Footer.disclaimer`, and `header_disclaimer`.
    **Escaping untrusted text in these is the caller's job** — use
    [escape_html()](../../svc/builder/filters.py) (`from svc.builder.filters import escape_html`).
    `header_disclaimer` is the one worth naming twice (#95): making the strip a first-class,
    obviously-reusable region makes it likelier someone passes untrusted text to it, and the
    contract was *kept* rather than tightened because escaping it now would break every caller
    passing markup. So `Header`'s docstring states it, and a test asserts the docstring still
    does — a region whose text is raw HTML is a footgun, and a warning that lives only in a
    commit message is how it stays one.
  - **A raw-HTML field is emitted inside a `div`, never a `p` (#130).** Five surfaces
    carry caller markup, and the documented shape of the first two is the caller's own
    paragraph tags — so a `p` wrapper is auto-closed the moment their content opens, the
    copy becomes the wrapper's *sibling*, and everything that wrapper was styling escapes.
    That shipped: for the whole life of the package, `TextBlock` prose inherited the
    containing cell's `font.label` instead of its own `font.body`, and a `NumberedItem`
    body took the cell's leading instead of `list_body_line`. **No golden could see it** —
    the HTML was byte-stable and looked correct; only a parser resolving the nesting
    reveals it, which is why the guard lives with the screenshots. `Card.body` and
    `Footer.disclaimer` were already `div`s; the other three joined them. A test asserts
    all five, so a sixth cannot be added wrongly.
  - **Attributes** (`src`, `href`, `alt`, `<title>`) are always escaped, quotes included,
    so a value cannot break out of the attribute it sits in.

- **URL schemes are validated** (#24) — escaping keeps a URL inside its attribute; it says
  nothing about what the URL does when followed. `models._validate_url()` allows `http`,
  `https`, `mailto`, `cid` and relative URLs, and rejects everything else (`javascript:`,
  `data:`, `vbscript:`, `file:`) with `ValidationError` at construction. Applies to the five
  `EmailMetadata` URL fields, `ChartBlock.image_url`, `ImageBlock.link_url`, and every
  `EmailImage.hosted()` URL. Scheme only — whether a URL resolves, and its host/path, are
  not checked. A builder-generated `data:` URI from `EmailImage.inline()` bypasses this by
  construction — it is validated by magic-byte sniffing instead, never by scheme.
- **Hex-color enforcement** — colors use `#RRGGBB` everywhere. Validated by
  [models._validate_color()](../../svc/builder/models.py) at construction time and by the
  `validate_hex_color` filter ([svc/builder/filters.py](../../svc/builder/filters.py)) in templates.
  `DataTable` cell colors come from the `TableRow.colors` list — index-aligned with `cells`.

- **The region model is complete (#38 header, #55 footer)**, and between them `base.html`
  went from 277 lines to 109. What the remaining epics inherit:
  - **The mechanism is generalised, not duplicated.** `Region` owns validation, the image
    walk, the facts-over-presentation layering and `render_slots()`; a region declares its
    slots, its templates and its fields. A future region-like idea should start there.
    #87 was the mechanism's own test and it passed: the strip already rendered from a
    template of its own into a slot of its own, so promoting it was a change of *owner*, not
    of markup, and the skeleton's slot set never moved. The preheader stays skeleton plumbing
    regardless — that one is a decision, not a gap.
  - **`EmailMetadata` is facts only.** A new field belongs there if it is *true of the
    email* and on a region if it is *how something looks*. The flat-keyword `InitVar` pattern
    is how a field moves off the metadata without breaking an existing call site.
  - **`base.html` is down to the head, the skeleton and the preheader** — which is why the
    two theme epics (#45, #46) contended on far less of one file than they would have, and on
    almost none of the markup that made it fragile.
  - **A variant is what proves a seam.** `MinimalBanner` differs from `Banner` in exactly
    which slots it fills — it composes `TEMPLATE_PATHS` rather than replacing it, so the two
    cannot drift on the slot they share; it has a gallery fixture and a golden.
    A seam with one implementation is a refactor.

## The region layer — the two rules that give it its shape

Moved out of `svc/builder/regions.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Regions — the layer between the skeleton and the containers.

The composition model is ``skeleton ← regions (header | banner | body | footer) ←
containers ← components``. A *region* is a named area of the email that
renders itself from its own template(s) and declares its own images, the way
a :class:`~svc.builder.components.Component` already does for a content
block.

Two rules give the layer its shape:

**Facts flow down.** The firm's name, the campaign, the dates, the
disclaimers and the outbound URLs are facts about the *email*; they live on
:class:`~svc.builder.models.EmailMetadata` and are passed into the region at
render time. A region presents them — it cannot own or contradict them,
which :meth:`Region.context` enforces by layering the facts *over* its own
keys rather than under them.

**The design system is not a parameter.** Fonts, palette, padding and the
680px geometry stay in the templates, exactly as for containers and
components. A region varies the *structure* of the masthead, not its look.

**A region fills one or more named slots.** The banner fills two since #89 —
``{{ header_bar_html }}`` for the strip at the top of the email and
``{{ banner_html }}`` for the masthead below it, which shared a template only
by accident of file layout; the footer fills one (``{{ footer_html }}``),
rendered as a self-contained sibling table below the body.
:meth:`Region.render_slots` is the contract the skeleton consumes, and a
slot a variant leaves unfilled renders empty, which is how a variant
*omits* a block rather than conditionalising it away.

**``Banner`` was called ``Header`` until #90, and there is no alias.** The
name is being reused: #87 gives the strip at the top of the email a region of
its own, and *that* becomes ``Header``. A deprecated warn-and-forward shim —
the courtesy ``KpiStrip`` extends to ``CardGroup`` — would collide with the
new class rather than ease the migration, so the break is clean and loud on
purpose. Between #90 and #87, ``from svc.builder import Header`` raises
``ImportError``; afterwards an old-style ``Header(logo_url=…)`` fails at
construction, because the class that answers to the name has no such field.
Both failures happen at the call site, immediately, which is the point: a
name that quietly changed meaning would keep running and be wrong. The flat
keywords (``logo_url``, ``logo_alt``, ``logo_width``, ``header_bg_image_url``
on :class:`~svc.builder.models.EmailMetadata`) are unaffected and still build
the region — they are the common call path, and they never named the class.

The body region is deliberately not a class: it *is* the email's ordered
section list, and wrapping that in an object would add a layer with no
behaviour. The preheader stays skeleton plumbing for the same reason. The
strip the banner still renders becomes a region of its own in #87; until
then the banner owns both of its slots.
```

## Images — the strategies, the manifest, and why the builder cannot embed

Moved out of `svc/builder/images.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Image sources and embed strategies for HTML email.

An image in an email carries two independent facts: **where the bytes live**
(a hosted URL, a file on disk, bytes in memory) and **how they reach the
reader**.  This module owns both, and is the generic foundation the
per-service delivery layers build on.

The builder can decide the strategy and emit the correct ``src``, but it
cannot *perform* a CID embed — attaching a MIME part is a transport act
belonging to a delivery service (``svc/gmail``, ``svc/outlook``).  So the
builder emits two things instead of one: the HTML, and an **asset
manifest** of the :class:`ImageAsset` parts the delivery layer must attach.
Reach the manifest via :meth:`Email.assets <svc.builder.email.Email.assets>`.

The three strategies, and why all three exist:

==============  ===========================  =====================  ==========================
Strategy        Size cost                    Gmail                  Outlook desktop
==============  ===========================  =====================  ==========================
``REMOTE``      none                         proxied and cached     blocked until "download
                                                                    images"
``CID``         *message* size, not HTML     renders; may show a    renders immediately, no
                size — does not count        paperclip              prompt
                against the 102 KB limit
``DATA_URI``    +33% base64, straight into   **stripped entirely**  Word engine will not
                the 102 KB budget                                   render it
==============  ===========================  =====================  ==========================

``REMOTE`` is the default because it is the only one that is universally
*safe*, and ``CID`` is the one that actually renders everywhere — pick it
when the reader must see the image without clicking anything.  ``DATA_URI``
looks the most like "embedding" and works the least; it is supported for
browser preview and non-Gmail channels, guarded by a hard size check, and
is never a default.

Usage::

    from svc.builder.images import EmailImage

    hosted   = EmailImage.hosted("https://cdn.example.com/chart.png", alt="Factor returns")
    attached = EmailImage.attached("charts/factor.png", alt="Factor returns", width=616)
    inline   = EmailImage.inline(png_bytes, alt="Sparkline", width=120)

Format support is deliberately narrow: PNG, JPEG and GIF are the three
raster formats every mail client renders.  WebP and SVG are recognised only
so the rejection can say why.
```

## The builder package's front-door example, in full

Moved out of `svc/builder/__init__.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
pyHermes Email Builder Service
==============================

Object-oriented email assembly using Jinja2 templates.

Quick start::

    from pathlib import Path

    from svc.builder import CardGroup, EmailBuilder, FullWidth, TextBlock
    from svc.builder.models import KpiItem

    # email_subject, firm_name and campaign_name are required; the rest of
    # EmailMetadata is optional.  metadata() must be called before section().
    email = (EmailBuilder()
        .metadata({
            "email_subject": "Weekly Market Wrap",
            "firm_name": "Research & Strategy",
            "campaign_name": "weekly-wrap",
        })
        .section(FullWidth(
            content=CardGroup([
                KpiItem("S&P 500", "5,234", "#4A7C59", "+1.42%"),
                KpiItem("UST 10Y", "4.28%", "#B85450", "+6 bps"),
                KpiItem("VIX", "14.32", "#4A7C59", "-2.18 pts"),
            ]),
            title="Market Snapshot",
            highlight=True,
        ))
        .section(FullWidth(
            content=TextBlock("Equity markets advanced..."),
            title="Week in Review",
        ))
        .build()
    )

    email.save(Path("output.html"))
```

## The enum vocabulary — why StrEnum, and what stays out of it

Moved out of `svc/builder/enums.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Centralized enum vocabulary for the email builder.

A single home for the small closed sets of string options the builder
accepts — column ratios, card orientation — so the allowed values live in
one place instead of being scattered as bare string literals across the
container and component classes.

Every enum here is a :class:`~enum.StrEnum`: each member *is* its wire
string (``TwoColumnRatio.EQUAL == "50-50"`` and hashes the same), so a
caller may pass either the enum member or the plain string interchangeably.
That keeps the enums a purely additive, backward-compatible convenience —
existing ``ratio="50-50"`` / ``orientation="horizontal"`` calls are
unaffected. Note the containers/components may now *store* the value as an
enum member (e.g. from the default), but a member is-a ``str``
(``isinstance(TwoColumnRatio.EQUAL, str)`` is ``True``), so attribute reads
and ``==`` comparisons behave exactly as with the plain string.

Note these enums hold only the *vocabulary*. The mapping from a ratio to
its template file stays with the container that owns it (``_ratio_map`` in
``containers.py``), because a template path is a rendering detail, not part
of the type.
```

## The three-way escaping split, stated in full

Moved out of `svc/builder/filters.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Custom Jinja2 filters and tests for the email builder.

**Escaping contract.** Jinja2 ``autoescape`` is OFF — HTML emails need raw
output, and rich fields are meant to carry markup.  Escaping is therefore
explicit, and split by field kind:

* **Plain-text fields** (section titles, subtitles, KPI labels/values, table
  headers and cells, chart alt text and sources, author details, and the
  plain metadata fields) are escaped **by the builder**, in the templates,
  via the ``escape_html`` filter.  Pass these as raw text — do *not*
  pre-escape them, or they will be double-escaped.
* **HTML fields** (``TextBlock.content``, ``NumberedItem.body``, and the
  metadata disclaimers) are emitted raw, because callers deliberately pass
  markup.  **The caller is responsible for escaping anything untrusted in
  them** — use :func:`escape_html` for that.
* **Attributes** (``src``, ``href``, ``alt``, ``<title>``) are always escaped
  by the builder, including quotes, so a value can never break out of the
  attribute it sits in.
```

## Containers — the computed-width rule in full

Moved out of `svc/builder/containers.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Container classes for the email builder.

A container defines the layout geometry for a section of the email —
single column, two-column split, highlight band, etc.  Each container
wraps one or more rendered component HTML fragments and produces a
``<tr>`` block that drops into the main email body table.

Column widths are **computed, never written down**: the ratio's own name
is its weights, and :func:`~svc.builder.sizing.column_layout` splits the
active scheme's content width by them. That is why one template serves
every split — see #42 in :mod:`svc.builder.sizing`.

Usage:
    engine  = TemplateEngine()
    kpi     = KpiStrip(items=[...])
    section = FullWidth(content=kpi, title="Market Snapshot")
    html    = section.render(engine)
```

## Email and EmailBuilder — the two construction patterns

Moved out of `svc/builder/email.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Email builder — the main orchestrator.

Provides two usage patterns:

1. Direct construction::

    email = Email(metadata={...})
    email.add_section(FullWidth(content=TextBlock("Hello"), title="Intro"))
    email.save(Path("out.html"))

2. Fluent builder::

    html = (EmailBuilder()
        .metadata({...})
        .section(FullWidth(content=TextBlock("Hello"), title="Intro"))
        .render())
```
