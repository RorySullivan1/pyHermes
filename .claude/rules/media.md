---
paths:
  - "svc/email/**/*"
  - "svc/document/**/*"
  - "svc/pdf/**/*"
  - "svc/builder/medium.py"
  - "svc/builder/document.py"
  - "svc/builder/templates/document/**/*"
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
Email(metadata)          # svc/builder/email.py   — EMAIL_MEDIUM
PagedDocument(metadata)  # svc/document/          — PAGED_MEDIUM, A4 by default
Document(metadata)       # svc/builder/document.py — DEFAULT_MEDIUM, plain HTML
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

## The regions each medium has

Same base class, same `SLOTS` / `TEMPLATE_PATHS` / facts-over-presentation rules, an `Empty`
variant each.

| Medium | Regions | Skeleton |
|---|---|---|
| `email` | `Header`, `Banner`, `Footer` | `templates/base.html` |
| `document` | `Cover`, `RunningHeader`, `RunningFooter`, `BackMatter` | `templates/document/base.html` |

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

`Page` is the other managed element: a container of containers that **flattens where pages do
not exist**, byte for byte as though it were not there. The decision is made in Python rather
than left to CSS because `break-before` is inert in a mail client and so would *look*
harmless — while the wrapper element around it is not. The break lands on a table `tr`:
containers emit `tr` blocks, and CSS break properties do not apply to a `td`.

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
- **Each hook is a class and nothing else.** `section-title`, `fine-print`, `figure`,
  `row-total` and `row-subhead` carry no style of their own. The email golden diffs were
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

`svc/pdf/` is an exporter on `svc/gmail` and `svc/outlook`'s terms exactly: it takes what the
builder produces, owns its wire format, and owns nothing else. WeasyPrint is the optional
`[pdf]` extra, imported lazily, and an AST test holds that nothing under `svc/builder`,
`svc/document` or `svc/email` imports it.

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
  contract — would have missed it. It unwraps and re-raises, cause chained.
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
