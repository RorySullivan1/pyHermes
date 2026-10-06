---
paths:
  - "pyhermes/email/**/*"
  - "pyhermes/document/**/*"
  - "pyhermes/pdf/**/*"
  - "pyhermes/builder/medium.py"
  - "pyhermes/builder/document.py"
  - "pyhermes/builder/templates/document/**/*"
  - "pyhermes/builder/templates/common/stamp.html"
  - "pyhermes/qr/**/*"
---

# Media — one section tree, several destinations

Epic #157 rescoped pyHermes from *an email builder* to **a document builder with an email
medium**. The section tree, the three design axes and the two projections are shared; a
**medium** decides where the result is read.

## A medium is a product, not a fourth axis

Theme, density and typeface are *presentational choices that leave the structure untouched* —
same skeleton, same slots, same constraints. A medium changes all of those, so it is chosen by
**which class you construct**, never by a field you flip:

```python
Email(metadata)          # pyhermes/builder/email.py   — EMAIL_MEDIUM
PagedDocument(metadata)  # pyhermes/document/          — PAGED_MEDIUM, A4 by default
Document(metadata)       # pyhermes/builder/document.py — DEFAULT_MEDIUM, plain HTML
```

Once chosen it **rides the binder as the fourth keyword**, so a shared template can ask
`{% if medium.paged %}` and no container, component or region ever changed signature:

```python
engine.bound(theme=…, size=…, font=…, medium=…)
```

That was design-axes.md's own instruction — *"a fourth email-level value should be the fourth
keyword, not a fourth mechanism"* — and it held. `Renderer` grew a `medium` property only in
#163, when `Page` became the first thing that needed the object in Python; the bar for adding
to a contract every container, component and region shares is a reader, not a plausible one.

What a `Medium` owns:

| | |
|---|---|
| `skeleton` | The template path rendered last, with every slot filled |
| `region_types` | The region classes whose slots the skeleton names. `slots` is **derived** from them |
| `page_format` | The page — see below |
| `constraints` | Checks run over the *composed* document |
| `template_search_path` | Directories searched ahead of the shared tree |
| `paged` / `email` | What a shared template may branch on. Independent, because a standalone HTML deliverable is neither |

`slots` is derived rather than declared beside `region_types` because a medium that listed both
could disagree with itself, and the skeleton would then be right about one of them.

## The page belongs to the medium, not the density

`FrameGeometry` used to be the fourth layer of `SizeScheme`, so the 680px email column
travelled with the density presets — which never touched it. `PageFormat` now carries `width`,
`height` and `mobile_breakpoint`, a `Medium` owns one, and `SizeScheme.with_page()` lays it
over the density's frame at render time. `size.frame` still exposes exactly the field names all
thirty template sites already read.

- **The page is layered *over* the density, never under it** — the precedence a region gives an
  email's facts and `BoundEngine` gives a bound value. A caller who derived a frame width of
  their own does not quietly change the page a document is printed on.
- **`with_page` returns `self` when the density already describes that page.** Not an
  optimisation: `TestTheSchemeReachesEveryTemplate` asserts the shipped scheme *object* reaches
  every template, which proves it is threaded rather than rebuilt.
- **Two absences are states, not gaps.** `height=None` is a continuous frame (an email body
  ends where its content does) and `mobile_breakpoint=None` never collapses (what paper does).
  `_validate_size_fields` learns this through an `OPTIONAL` declaration, so every other token
  keeps its rule.
- **`orientation` is derived, never stored** — a declared one is a second fact about the same
  two numbers and the two can disagree.

**The page is a sheet with a margin, and the frame is what the margin leaves** (#175). Before
it, `@page` had a hardcoded horizontal margin of zero and took its vertical margin from
`frame.outer_pad_y`. That is the band an *email* draws above and below itself, so a density
token was deciding a print margin. `PageFormat` now carries a `PageMargin`. Its `width` and
`height` stay the **sheet**, which is what `@page size` prints. `frame_width` and `frame_height`
are the sheet less the margin, and the body tables fill the frame.

- **`with_page` lays the frame and the margin over the density.** `size.frame.width` is the
  frame, and every existing template site kept reading it. `sheet_width` and `sheet_height` are
  properties that add the margin back, and the skeleton's `@page` rule reads only those and
  `size.frame.margin`.
- **The cover spans the sheet, not the frame.** Its named page has no margin, so a frame-wide
  cover would leave a gutter down one side.
- **`PageMargin` is its own type because zero is legal there.** Every other size token must be
  positive. The continuous email page has no margin at all, and that keeps every email golden
  byte-identical.
- **No preset's frame is 680px wide, and that was a decision.** A 15mm side margin on A4 gives
  exactly 680, the email's column width. A template still reading the email frame would then
  render correctly on paper, and nothing could see it. A4 takes 20mm all round instead.
- **The running boxes sit in the margin, aligned to the frame edge**, not to the copy inside
  `pad_x`. They print level with a highlighted band's hairline, and the raster shows them
  clear of the content.
- **The sentinel is `TestThePageMarginIsTheMediums`**, on a 9001 by 9002px sheet with four
  distinct margins. Three perturbations were each checked to fail it by name: `@page` reading
  the density again, the body table reading the sheet, and the cover reading the frame.

**The sentinel moved with the owner, and that is the part to remember.** The existing
token-liveness test perturbed the frame *through the scheme*, which the medium now overwrites —
so it would have proved nothing while staying green. It perturbs `SENTINEL_PAGE` now, and a
second test renders at a 9001px page asserting no shipped page value survives anywhere.

## A medium forks one template, never the tree

`TemplateEngine` loads through a `ChoiceLoader`: each of the medium's `template_search_path`
directories first, the shared root last. A file at `<medium>/text/block.html` shadows
`text/block.html` for that medium and is invisible to every other.

It ships switched on and doing nothing — `EMAIL_MEDIUM` declares `("email",)` and that
directory does not exist, so every lookup falls through. A `FileSystemLoader` over a missing
directory finds nothing and raises nothing, which is what an unforked medium looks like and why
no placeholder ships in the wheel. `test_nothing_is_forked_yet` asserts the overlay stays
empty and names the obligation for whoever first fills it.

**To fork one:** copy it to the same relative path under the medium's directory, change it,
regenerate that medium's goldens, and say in the PR **why the shared template was wrong here**.
A fork is a claim that two media genuinely need different markup, and it doubles the sites a
later change has to reach. The paged medium's skeleton is the worked example: it is named
`base.html` and reached through `document/`.

**What did *not* meet that bar:** `columns.html` carries an `[if mso]` block that reaches paged
output. It is an ordinary HTML comment to every parser but Word's, so it is waste rather than
breakage, and bytes do not count against anything outside Gmail. Recorded with a count instead,
so the day it becomes a fork the diff has a number to beat.

## A caller's overlay is not a medium's fork (#247)

`Document`, `Email`, `EmailBuilder`, `PagedDocument` and `Brochure` take `template_overlay=`, one
directory or several, and `TemplateEngine` searches them **first**: overlay, then the medium's
fork path, then the packaged root. Before it a caller who wanted one house footer, or a
template for a `Component` of their own, vendored all 33 templates and re-vendored on every
upgrade; an absolute `template_search_path` happened to work only because `Path / absolute`
drops the left side.

- **The fork rule above is about the package's own media**, and `test_nothing_is_forked_yet`
  is untouched. An overlay is the caller's, carries no obligation to the package, and can
  shadow a medium fork, which is the caller's intent when they do it.
- **A missing overlay raises `TemplateError` naming the path, at construction.** A medium's
  missing directory is the normal unforked case; a caller's is a typo.
- **No discovery.** An overlay is passed, never read from the environment or an entry point,
  and a component needs no registration: its `template_path` resolves through the overlay.
- `tests/test_template_overlay.py` holds it: the forked footer renders and, with its marker
  removed, `kitchen_sink` is byte-identical to the packaged render; a test component renders
  from an overlay in both projections; the precedence is asserted with one relative path in
  all three places.

## The regions each medium has

Same base class, same `SLOTS` / `TEMPLATE_PATHS` / facts-over-presentation rules, an `Empty`
variant each.

| Medium | Regions | Skeleton |
|---|---|---|
| `email` | `Header`, `Banner`, `Footer` | `templates/base.html` |
| `document` | `Cover`, `ContentsPage`, `ExhibitsPage`, `RunningHeader`, `RunningFooter`, `BackMatter` | `templates/document/base.html` |
| `brochure` | none: every face is a `Panel` the caller composes | `templates/brochure/base.html` |
| `deck` | `TitleSlide`, `ClosingSlide`: every sheet between them is a `Slide` | `templates/deck/base.html` |

Three things the second set taught:

- **A slot need not be markup.** The running boxes fill slots inside the skeleton's `style`
  element, because a `@page` margin box *is* CSS. The mechanism needed nothing — a slot was
  always a string hole — but the escaping did, so `css_string` sits beside `escape_html`. The
  trap it closes is not the quoting: a `</style>` inside a firm name would close the stylesheet
  and spill the rest of the rule onto the page.
- **A projection left empty must say so.** `RunningBox._text` returns `""` **by decision** — a
  folio counts sheets plain text does not have — and is implemented rather than left to raise,
  which is what distinguishes it from standing rule 10's failure case.
- **The back matter mints no new raw-HTML surface.** It renders `header_disclaimer`, a fact
  `DocumentMetadata` owns, so the blessed set stays closed at five.
- **A running box may follow the section (#185), and the title is not a fact.** Which section
  a sheet holds is the page's own knowledge, so it reaches the margin through the print
  engine's named strings (`string-set` on each section title, `string()` in the box) and never
  through the facts layer. `RUNNING_FACTS` are unchanged; `label` is the fallback before the
  first section. `apparatus.md` has the four probes the fallback took.
- **The contents sheet (#183) is opt-in.** `ContentsPage` is handed the sections'
  titles as a derived fact, `contents_entries`, and its page numbers are the print engine's.
  It defaults to `EmptyContentsPage`, because a two-sheet factsheet is not improved by a third.
  **`ExhibitsPage` (#308)** is the same sheet in a slot of its own, listing the exhibits, and
  opt-in for the same reason; the skeleton prints the two slots back to back on one line.

`Page` is the other managed element: a container of containers that **flattens where pages do
not exist**, byte for byte as though it were not there. The decision is made in Python rather
than left to CSS because `break-before` is inert in a mail client and so would *look*
harmless — while the wrapper element around it is not. The break lands on a table `tr`:
containers emit `tr` blocks, and CSS break properties do not apply to a `td`.

**A page that opens the body drops its leading break**, in `PagedDocument._body_sections`
(moved from `_body_context` by #259, so the size report's per-section render matches). The
body always starts a sheet, whether the first or the one after a cover or contents sheet. But
the running boxes' two seed leaves sit ahead of the body table, so a forced break there opened
a blank sheet whenever no contents sheet came first. The factsheet found it: its first sheet
could not be a `Page`, so its two sheets were written two different ways. The caller's `Page`
is not mutated; the body renders `Page.opening()`, a copy.

**`PagedDocument.add_page(sections)` is shorthand for `add_section(Page(sections))`**, with
`Page`'s own arguments. It adds no second model: the page is still a node in the tree, which is
what lets the same sections flatten in an email and lets the apparatus walk read through it.
So it lives on the paged medium only, and the `Page` class stays. A page is not a sheet: it
*starts* one, and its sections flow on across as many as they need. Only a document built to
fit, like the factsheet, has one page per sheet, so the document is never a list of pages.

## Where a sheet may not end — the paged skeleton's break rules

Epic #169 gave the paged medium break discipline inside the content. Before it, the only
break properties in the tree were the sheet boundaries. The rules sit in `document/base.html`'s
`style` block and are keyed on class hooks in the shared markup. That block is to the paged
medium what the `@media` block is to mobile. The email never loads it, so no rule costs an
email a byte, and nothing was forked.

| Hook | Rule | What it stops |
|---|---|---|
| `.data-table tbody tr` | `break-inside: avoid` | A row splitting mid-cell |
| `tr.row-total` | `break-before: avoid` | A total opening a sheet alone |
| `tr.row-subhead` | `break-after: avoid` | A subhead closing a sheet |
| `.data-table > caption` | `break-after: avoid` | A table's name closing a sheet |
| `.section-title` | `break-after: avoid` | A section title stranded at the foot |
| `.subtitle` | `break-after: avoid` | A component's standfirst left behind by its figure |
| `.fine-print` | `break-before: avoid` | An attribution or disclosure opening a sheet |
| `.figure` | `break-inside: avoid` | A chart or image block splitting |
| `body` | `orphans: 2; widows: 2` | The CSS initial values, stated so the decision is visible |

- **Every rule was probed on its boundary case under WeasyPrint 70, with and without it.**
  Each defect reproduced without its rule and was gone with it. The probes varied the length
  of a preceding section until the thing under test landed exactly at a sheet edge.
- **A rule sits on the thing that must not split, never on a container that may.**
  `break-inside: avoid` on a table taller than a sheet pushes it whole and strands a
  half-empty sheet. That is why nothing sits on `.data-table` itself.
- **The section title's rule goes on the title's *table*.** The title and the content are
  sibling tables in both container templates, so the break the rule forbids is the one between
  them.
- **An `avoid` needs an earlier break to fall back to.** When a section is the first thing in
  the document, WeasyPrint has nowhere else to break and strands the title anyway. A probe that
  starts a document with the section under test proves nothing about the rule.
- **Cell padding can move a whole table.** When a table's rows fit on a sheet but the
  container cell's bottom padding does not, WeasyPrint breaks before the table rather than
  inside it. The title rule keeps the title with the table when that happens.
- **Two rules can interact, and only a raster shows it.** The figure rule moves a chart whole,
  and that left the chart's subtitle alone at the foot of the sheet it came from. No issue
  named the defect. The first photograph of the long-table fixture found it, and the
  `subtitle` rule followed. Its test strips that one rule and not the rest, because without
  any rules the chart never moves and the subtitle is never stranded.
- **Each hook is a class and nothing else.** `section-title`, `subtitle`, `fine-print`,
  `figure`, `row-total` and `row-subhead` carry no style of their own. The email golden diffs were
  checked by a script to contain only the inserted attributes, and every email screenshot
  stayed pixel-identical.

## The facts split in two

`DocumentMetadata` holds what is true of any document — firm, campaign, department, dates,
language, `header_disclaimer`, and the three design axes. `EmailMetadata` adds what is true only
of an email: subject, preheader and the two outbound URLs. A paged document reuses the facts
without inheriting a subject line it could never have.

Which fact sits on which side is a **decision**, so a test names both sets rather than deriving
them: moving `issue_label` across the line is byte-identical and passes everything else.

Two ordering details are behaviour. `EmailMetadata.__post_init__` hydrates its regions *before*
calling `super()`, so a flat-keyword conflict still names itself ahead of a bad language tag;
and `validate()` layers the same way — the base requires who and what, the subclass adds the
subject and the URL schemes.

## The exporter contract, extended

`pyhermes/pdf/` is an exporter on `pyhermes/gmail` and `pyhermes/outlook`'s terms exactly: it takes what the
builder produces, owns its wire format, and owns nothing else. WeasyPrint is the optional
`[pdf]` extra, imported lazily, and an AST test holds that nothing under `pyhermes/builder`,
`pyhermes/document` or `pyhermes/email` imports it.

What it **adds** to that contract is a resource policy, and it is the security-relevant part:
**no network requests**. `cid:` is served from the document's own manifest, `data:` resolves
itself, everything else is refused by URL with a message saying what to do instead.
`allowed_protocols=("data",)` leaves the inherited opener nowhere to go; `fail_on_errors=True`
makes a refusal *stop the render*, because WeasyPrint's default is to warn and carry on — which
would drop a chart out of a compliance document and still return a finished-looking PDF.

Consequences worth knowing:

- **A document with hosted images cannot be printed.** That is the policy working. A printable
  document carries its own images, which is why the paged fixtures attach their cover art.
- **The exporter presents its own exception tree.** `fail_on_errors=True` makes WeasyPrint wrap
  the cause in a `FatalURLFetchingError`, so a caller catching `PdfError` — the documented
  contract — would have missed it. It unwraps and re-raises, cause chained. Anything else
  WeasyPrint raises is re-raised as `BackendError`, and a wheel whose Pango, Cairo or HarfBuzz
  will not load fails at import with `OSError`, not `ImportError`, so `available()` catches both
  and `BackendMissingError` names the system packages (#241).
- **The pin is `weasyprint~=70.0`, not a range.** Version 70 replaced the `url_fetcher` contract,
  and it is the fetcher that carries the policy, so a range spanning that change would land the
  failure on the part that matters most.

## The epic's post-mortem

Nine phases, and the first four shipped with **every golden byte-identical** — which is what
made them reviewable as changes of *owner* rather than of markup, the proof #95 established.

- **A check can be wrong about its scope, and fixing the code instead is the trap.** Three
  times: the theme test discovered regions from one module and reported the cover as escaping
  the theme; the golden harness's `write_fixture` created one directory where each medium now
  needs its own; and `page.html` used the wrong colour idiom, where the *house* idiom was both
  more correct and what the rule asked for. None of them was a reason to weaken a rule.
- **A sentinel must perturb the current owner.** The frame lift broke the existing one loudly,
  which was luck — a subtler change would have left it green and meaningless.
- **A byte-verified diff is not a verified render, twice over.** #164's first real PDF put a
  folio on its own cover (a zero `@page` margin does not suppress a margin box; only
  `content: none` does) and shrink-wrapped every table to 188px inside a 794px page (a print
  engine does not map a table's `width` *attribute*, where a browser does). Both were correct
  markup to every golden, every lint rule and every browser screenshot. Standing rule 3 gained
  its third clause for exactly this: **the PDF rasterisation owns pagination.**
- **Measure the medium's cost before predicting it.** #162 predicted "expect some lint findings
  on the paged render". The measurement was that a realistic paged document is *clean* against
  all ten email rules, and exactly one — `size-budget`, Gmail's 102 KB — was wrong rather than
  merely quiet. That number is what made #165 a rule table instead of a rewrite.
- **Two galleries beat one widened one, until the harness is ready.** `all_fixtures()` feeds a
  dozen test modules whose assertions are about emails. Keeping the paged fixtures in a second
  registry for three phases is what let #165 unify them deliberately rather than by accident.


## The third medium: a folded sheet (#172)

`pyhermes/brochure/` is the first medium with **no regions**. A brochure's cover is its first panel,
and a `Cover` region would be a second way to fill it. Its overlay searches `brochure/`, then
`document/`, then the shared tree, so it forks only its skeleton, the side and the panel, and
shares the paged medium's editorial partial. `Document.render` gained one hook for it,
`_body_context()`, which the brochure overrides to lay the body out as two imposed sides and
to hand its skeleton the bleed. Every other document's body is the section list, as before.

**Its PDF is RGB, and that is a decision.** WeasyPrint writes no CMYK, ICC profile or PDF/X,
and converting colour for a press is the print house's step. Pretending otherwise would ship
a wrong colour profile with confidence. The `rgb-only` lint finding says so once per
brochure, at the `INFO` severity that never fails a build. `brochure.md` has the rest.

## The PDF's document information is read off the facts (#195)

The paged and brochure skeletons carry the same three lines in the head. They are inlined in
each rather than shared as a partial: `test_every_template_now_reads_the_theme_namespace`
holds that every template paints, and a head-only partial paints nothing. The lines emit
`author` from `firm_name`, `description` from `campaign_name`, `department` and `date_range`,
and `keywords` from `department` and `issue_label`. WeasyPrint writes these as the PDF's
Author, Subject and Keywords. The title and `lang` were already the skeleton's. No exporter
argument restates any of them: a caller who wants a different author changes the facts.

- **No creation or modification date, deliberately.** A date makes two renders of one document
  differ, and the goldens rest on determinism. A test reads both fields back empty.
- **Determinism needs HarfBuzz-Subset.** Without it WeasyPrint falls back to fontTools, and
  `TTFont.save()` stamps the clock into each embedded font's `head` table. Two renders then
  differ whenever they straddle a second. CI's `pdf` job installs `libharfbuzz-subset0`.
- **The outline keeps the contents sheet and the disclosures.** Both are headed sheets a
  reader navigates to, so both are bookmarks beside the sections, one level under the cover.

## An image's width is stated twice, and the CSS copy is a cap (#201)

A print engine maps no `width` attribute on an `img`, as #164 found for a `table`. The paged
cover's 72px mark, declared at 96, printed at 72; a 1150px image declared at 300 printed at
the column's 578. CSS cannot read an attribute as a length, so the skeleton's
`table[width="100%"]` rule has no image equivalent. The three options #201 listed were
measured on every paged and brochure fixture, sheet by sheet, against the rasters from `main`:

| Option | What the rasters showed |
|---|---|
| `presentational_hints=True` in the exporter | a4_portrait on **six** sheets, and every sheet of a4_long_table and the brochure moved |
| A fixed CSS `width: Npx` beside the attribute | The same six sheets: a 600px chart in a 50-50 split widened the whole frame past the page margin |
| `width: 100%; max-width: Npx` beside the attribute | Only the images changed, each to its declared width. All 28 email screenshots were pixel-identical |

**The third, in `image-block.html`, `chart-block.html` and the paged cover.** WeasyPrint
gives a replaced element with a fixed width a min-content of that width, so a table cell can
never shrink below it. A percentage width has a min-content of zero, the compressible case
in CSS Sizing. `width: 100%` capped by `max-width` therefore shows the smaller of the declared
width and the column, which is what a browser already showed for the attribute. Outlook's
Word engine still reads the attribute, and this is the fluid-hybrid pattern email templates
already use for it. No template was forked, and the email goldens moved by bytes alone. The
cover is paged-only and sits on a full sheet, so it takes a plain `width: Npx`.
`TestAnImagePrintsAtItsDeclaredWidth` reads every case back from the PDF. It also catches
the fixed-width version in a half column.

## The fourth medium: a deck (#218)

`pyhermes/deck/` lays one `Slide` to a sheet, between a title slide and the disclosures.
**It supersedes a decision this file recorded: that a slide and a sheet of A4 are one
medium at two pages.** That was true of a slide-shaped *sheet*, which `slide_16_9` still
is. A deck needs its own skeleton, slots and constraint (overflow is a finding, not a second
sheet), which is #172's test for a medium. `deck.md` has the rest, including the first
density one medium alone may take.

**The digital PDF (#193) is not a medium.** It is a `PdfProfile` on this exporter plus an
attachment path in `pyhermes/delivery`, and `digital-pdf.md` has the decision, the profiles, the size
budget and the PDF/UA measurement.

## There is no DOCX or PPTX exporter, by decision (2026-10-01)

Epic #219 proposed a Word export, and #300, under the deck epic #218, a PowerPoint one, each
walking the section tree with a projection per component. Both were closed as not planned, and
the rule they settled is **pyHermes grows by media, not by portability**: a new destination is a
medium on the one HTML render path, as the paged document, the brochure and the deck are. An
exporter joins the contract above only if it rides that path, as the PDF does.

Why the walk was refused, measured on `main` at `cf2cd5b`:

- **It is a second render path, not an exporter.** The PDF exporter is 652 lines with no
  per-component code because WeasyPrint consumes the HTML. Word and PowerPoint cannot start from
  it, so each walk needed a projection for 46 public classes, the three axes re-bound as styles
  or a master, the apparatus re-implemented (python-docx has no footnote API), and a fourth golden
  artefact with its own read-back harness. The plain-text projection, the one non-HTML path, cost
  1,130 lines against the simplest possible target. A completeness test would have made that a
  permanent tax: three projections per future component instead of one.
- **The fidelity ceiling is low, and the chart is the general case.** A chart enters the tree as
  PNG bytes from a drawn Figure (`chart_from_figure`), so the data is gone before any exporter
  sees it; a native chart needs a chart model the data layer deliberately lacks. Equations stay
  pictures, a `FontStack` collapses to one face, heat and bars become shading. What stays editable
  is titles, prose and tables, and a pitchbook is mostly charts.

**The one door left open:** if someone must edit one table in Word, the shape is an adapter at
the edge, `table_from_frame` in reverse, one function from a `DataTable` to a Word table behind a
`[docx]` extra, with no walk, no styles and no apparatus. A task, filed when asked for. What
would reopen the decision itself is a chart *model* in the tree, which is a second product.
The review that measured this is sessions/2026-10-01-1707-exporter-epics-review.md.

## Section breaks a caller can reach (#364)

`keep_together=True` and `break_before=True` are fields on every section container. On paper
each lands on the section's own `tr` in both spellings, as `Page`'s break does; elsewhere both
are decided away in Python, so an email moves no byte. A brochure panel and a slide refuse
them at construction, since neither breaks. A section that opens the body drops its leading
break for `Page`'s reason, through `Container.opening()`, which `Page` now inherits.

**A kept section taller than a sheet warns.** `break-inside: avoid` cannot hold it, so the
engine moves it and splits it anyway, stranding the space it left (this file's
"never on a container that may split" rule, now the caller's choice). The walk gives each kept
section a row `id`, `kept-section-N`; `layout()` and `render_pdf()` read which sheets carry it
and raise a `PrintQualityWarning` naming the section when there is more than one. Probed under
WeasyPrint 70 first: a kept row moves whole, and a split row's `id` appears in both sheets'
anchors. `render_pdf` takes the two-step path (`render`, then `write_pdf`, which is what
`HTML.write_pdf` does inside) only for a document with a kept section, so every other PDF
keeps its code path.

## Shown in chosen media only (#365) — route B

**The owner's decision, 2026-10-01: two wrappers, no field on existing classes.** `Only(block,
media=...)` is a component on `Stack`'s model; `OnlySections([...], media=...)` a section list on
`Page`'s. A `media=` field on every class (route A) was rejected; so was hiding by CSS, which
would ship the bytes.

- **The decision is made in Python, per projection.** A document's `configured()` scope now
  also binds the medium's name to a context variable (`walking_in`), the `config_override`
  pattern, and every projection runs inside it, `images()` and `add_section`'s walk included.
  `Only.children()`, `images()` and `text()` and `OnlySections.sections` read it; `render`
  reads `engine.medium`. Outside any document a walk shows everything.
- **What an omitted wrapper leaves out:** its markup (a `Stack` drops the row, the body drops
  the section and its newline, so an email with a print-only list is byte-identical to one
  without), its images from the manifest, its text, its contents entries and its anchors, so a
  link to it from the other medium is named by `validate()`.
- **Numbering is refused, not degraded.** A labelled exhibit, a footnote or a citation inside
  either wrapper raises at construction, because omitting one would make "Exhibit 3" or note 7
  mean different things in two media (the risk the epic named; `test_research_note.py` compares
  them).
- **A medium name nothing ships is refused**: `SHIPPED_MEDIA` in `medium.py`, held by a test to
  the shipped `Medium` objects the kit may not import.
- In a cell an omitted block leaves the cell empty; `OnlySections` sits at the top of a
  document, since a page, a panel, a slide and `Appendices` hold sections only.

## The medium owns the measure (#358)

`Medium.measure` is the prose measure a `TextBlock` takes when it names none: `"standard"` on
`PAGED_MEDIUM` (and so every `paged_medium(page)`), `BROCHURE_MEDIUM` and `DECK_MEDIUM`, `None`
on the email and on `DEFAULT_MEDIUM`. It is the medium's because it is geometry: the same
density on a 578px column and a 1,124px slide body needs a cap on one and not the other, and
"density is not width" stands. `design-axes.md` has the tokens and the numbers.

## A page laid the other way up (#341)

`Page(orientation="landscape")`, and the same keyword on `add_page`, lays that page's sheets
on the medium's sheet turned on its side, at the same margin. `"portrait"` turns a landscape
medium's; a page already that way up, a square sheet or a continuous one does not turn.

**Probed under WeasyPrint 70 first**, on a 794 × 1123 sheet with a 76px margin:

| Markup | Sheets |
|---|---|
| `page: landscape` on a body table's `tr` | four portrait: the property is inert on a row |
| on a block or a table in the body's flow | landscape, with the running boxes and `target-counter` right |
| the portrait content after it, no break | stayed on the landscape sheet: `page: auto` forces no break back |
| the same, with `break-before: page` | back on portrait |
| a zero-height leaf ahead of an opening landscape block | a blank portrait sheet first |

- **So a turned page is a body table of its own.** `PagedDocument._body_context` lays the body
  as runs of sheets one way up; the skeleton writes one `document-container` table a run, as
  wide as its frame, the turned one carrying `page: landscape`, the run after it
  `break-before: page`. Unturned, the body is one run and every golden is byte-identical.
- **Each run's first section drops its leading break** in `_body_sections`, which the size
  report shares, so `TestEverySectionIsFound` still finds every section.
- **The page renders against the turned frame**, rebinding the size scheme as a `Panel`
  does, so a table on it is as wide as the landscape frame (read back from the layout).
- **The seed leaves take the turned page's name** when the body opens on one and no contents
  or exhibits sheet sits between, which is the blank-sheet case above.
- `a4_wide_appendix` carries it; `tests/test_landscape_pages.py` reads the sheet sizes, the
  repeated head, the running boxes and two cross-references' page numbers back from the PDF.

## A stamp across every sheet (#342)

`DocumentMetadata.stamp`, plain text up to `STAMP_MAX` (24) characters. It is a fact, not a
region's presentation, so every medium reads it: paper sets it across each sheet, an email in
its header strip's first line, and the text part opens on `[DRAFT]`. **The issue also named
`stamp=` on each document's constructor; that would be a second source for one fact, so the
ownership bullet won.** An email with an `EmptyHeader` would drop the stamp silently, so
`Email.validate` refuses it.

**Probed on the paged, brochure and deck fixtures:** a `position: fixed` box repeats on every
sheet the print engine lays out, the cover, a named page and a title slide included, and its
word is in each sheet's text. **The issue asked for the stamp under the content; it goes over,
translucent.** Under (`z-index: -1`) it vanished behind every painted ground: a section's
surface, the brochure's tinted panel, the cover band. Over, in the theme's `rule` colour at
0.6 opacity, the copy reads through it.

- **Centred by `left: 50%` and half its width back**, one box the diagonal wide. A box wider
  than the page area placed by `left: -50%` drifted; the glyph boxes now centre on every sheet
  within 6pt (`tests/test_stamp.py`, read from the PDF).
- **Its size is the sheet's**: a fifth of the short side, smaller where a long word would run
  past three quarters of the diagonal at 0.78em a bold capital (measured), slanted along the
  diagonal. `stamp_type()` in `builder/document.py` computes it, and the template reads it.
- `kitchen_sink` and `a4_wide_appendix` say DRAFT, `pitch_16_9` CONFIDENTIAL.

## A way back from paper to the web (#344)

`QrCode(image, url, caption=None, size=96)` holds a PNG and the URL it encodes, on `MathBlock`'s
split: **the component takes bytes, the `[qr]` extra renders them.** `pyhermes.qr.qr_code(url)`
paints the symbol through segno (pure Python, no system library) in the theme's primary text
on its surface, with whole-pixel modules enough for `Config.print_dpi` at the printed size,
and writes no metadata chunk, so two renders share a Content-ID. `[qr]` is the sixth extra,
by the owner's decision (2026-10-01).

- **On paper it prints at `size` px** with the caption and the URL beneath. **In an email it is
  the theme's `Button`, byte for byte**, since a code on a screen is pointless, and its image
  leaves the manifest: `images()` reads the walk's medium against `PAGED_MEDIA`, which a test
  holds to the shipped media's `paged`.
- **A URL a phone cannot open is refused**: the builder's scheme check, then `http`, `https` or
  `mailto` only. Below 72px it is refused as too small to scan.
- **The gallery's code is a constant.** Goldens run where segno is absent, so
  `qa/fixtures/_qr.py` holds the module matrix and `_png.matrix_png` draws it; a `[qr]` test
  holds the constant to segno's encoding of its URL. `zxing-cpp`, a self-contained wheel, joins
  `[qa]` as the decoder, and `tests/test_qr.py` decodes the code from a rasterised paged page
  and the brochure's back panel.
