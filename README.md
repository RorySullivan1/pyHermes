# pyHermes

Write a research document once. Send it as an email, or print it as a PDF.

An HTML email is not a web page. Gmail clips the message body past ~102 KB and shows a
"View entire message" link; Outlook on Windows renders through Microsoft Word's layout
engine, which ignores `max-width`, drops most modern CSS, and will not display a `data:`
URI at all. The usual answers — a CSS framework, a `<div>` grid, an external stylesheet —
all fail there.

**New here?** The [user manual](docs/manual/README.md) walks through building, checking and
sending an email, task by task, with a troubleshooting page for every error message.

pyHermes composes Jinja2 templates into a single inline-CSS, table-based document
engineered for those constraints, and enforces the ones that break silently. It depends on
**Jinja2 and nothing else**.

The same section tree renders onto more than one **medium**. An `Email` gets the four-slot
skeleton, the Outlook accommodations and the 102 KB check; a `PagedDocument` gets a cover,
running margin boxes, real page breaks and an A4 or Letter or 16:9 page. You choose by
constructing one — the components, the colours, the density and the typefaces are the same
either way.

```python
from pyhermes.builder import Banner, EmailBuilder, FullWidth, CardGroup, TextBlock
from pyhermes.builder.models import KpiItem

email = (
    EmailBuilder()
    .metadata({
        "email_subject": "Weekly Market Wrap",
        "firm_name": "Research & Strategy",
        "campaign_name": "weekly-wrap",
        "department": "Rates Strategy",          # optional; omitted, the line collapses
    })
    .banner(Banner(
        title="Q3 Outlook",                      # unset, this is the firm name
        subtitle="What the curve is pricing",    # unset, the campaign name
        logo_url="https://cdn.example.com/logo.png",
    ))
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
        content=TextBlock("<p>Equity markets advanced on softer inflation data.</p>"),
        title="Week in Review",
    ))
    .build()
)

email.save("output/weekly-wrap.html")   # warns above 90 KB, raises above 102 KB
```

## The same content, printed

Swap the product and the section tree renders onto sheets instead. A cover, a folio in the
margin of every page, a real break before the appendix, and a closing disclosures page (a
contents sheet, footnotes and cross-references are [below](#numbers-notes-contents-and-references)):

```python
from pyhermes.builder import FullWidth, TextBlock
from pyhermes.document import BackMatter, Cover, Page, PagedDocument, RunningFooter
from pyhermes.pdf import save_pdf

document = PagedDocument(
    {
        "firm_name": "Hermes Research",
        "campaign_name": "Quarterly Review",
        "date_range": "Quarter ending 30 September",
        "header_disclaimer": "<p>For illustrative purposes. Not investment advice.</p>",
    },
    cover=Cover(title="Quarterly Review", subtitle="What the curve priced"),
    running_footer=RunningFooter(label="Confidential", show_page_number=True),
    back_matter=BackMatter(heading="Important Disclosures"),
)
document.add_section(FullWidth(content=TextBlock("<p>The curve steepened.</p>"), title="Narrative"))
document.add_section(Page([FullWidth(content=TextBlock("<p>Method.</p>"), title="Appendix")]))

document.save("review.html")       # the HTML is a deliverable on its own
save_pdf(document, "review.pdf")   # ...and so is the PDF  (needs the [pdf] extra)
```

`A4_PORTRAIT` is the default; `paged_medium(SLIDE_16_9)` and the Letter presets are in
`pyhermes.builder.sizing`. Each preset carries a print margin: 20mm on A4, 0.75in on Letter. The
running header and footer print inside that margin. For a margin of your own, pass
`PageFormat(width, height, margin=PageMargin(...))` to `paged_medium`. A `Page` **flattens**
in the email medium — one tree, two outputs — so the same sections can go to both.
`PagedDocument.add_page([...])` is shorthand for `add_section(Page([...]))`.

A printed document does not split what belongs together. A table repeats its column headers
on every sheet it crosses, and a row never splits. A total never opens a sheet alone. A
section title never ends one, and an exhibit keeps its source line and disclosure with it.

**The PDF exporter makes no network requests.** It serves `cid:` references from the
document's own manifest and refuses every other URL by name, so a document whose cover art
lives on a CDN raises rather than silently printing without it. Attach images with
`EmailImage.attached()` and they travel with the document.

## Sent as a PDF

A cover email and the report behind it go out as one message. `pdf_attachment` renders the
report for a screen and hands it to `build_message` as a file:

```python
from pyhermes.builder import EmailBuilder, FullWidth, TextBlock
from pyhermes.builder.sizing import LETTER_LANDSCAPE
from pyhermes.delivery import build_message, save_eml
from pyhermes.document import ContentsPage, Cover, PagedDocument, paged_medium
from pyhermes.pdf import pdf_attachment

facts = {"firm_name": "Hermes Research", "campaign_name": "Global Rates Review"}

report = PagedDocument(
    {**facts, "department": "Global Rates", "date_range": "July to September 2026"},
    medium=paged_medium(LETTER_LANDSCAPE),
    cover=Cover(title="Global Rates Review", subtitle="Six curves, one quarter"),
    contents=ContentsPage(heading="Contents"),
)
report.add_section(FullWidth(content=TextBlock("<p>Six curves steepened.</p>"), title="Summary"))
report.add_section(FullWidth(content=TextBlock("<p>Keep the steepener.</p>"), title="Outlook"))

email = (
    EmailBuilder()
    .metadata({**facts, "email_subject": "Global Rates Review: the third quarter"})
    .section(FullWidth(content=TextBlock("<p>This quarter's review is attached.</p>")))
    .build()
)

message = build_message(
    email,
    sender="research@example.com",
    to="clients@example.com",
    attachments=[pdf_attachment(report, "global-rates-review.pdf")],  # needs the [pdf] extra
)
save_eml(message, "review.eml")   # a dry run; send it through pyhermes.gmail or pyhermes.outlook as before
```

The message becomes a `multipart/mixed`: the email first, unchanged, and the PDF after it as
an attachment. The cover email's own `cid:` images still render in place.

- **`pdf_attachment` renders under the `SCREEN` profile.** It caps every image at 150 dpi where
  it is shown and re-encodes JPEGs at quality 85. `render_pdf` and `save_pdf` default to
  `PRINT`, which leaves images as they arrived. Pass `profile=` to either to choose.
- **A message with an attachment has a size budget.** Above 20 MB on the wire,
  `build_message` raises and names each file with its size. That is Microsoft 365's default
  limit, below Gmail's 25 MB, and base64 makes a 16 MB PDF a 22 MB message. A PDF rendered
  under `PRINT` is named with the fix. Above 15 MB it warns. Both numbers are in
  `Config`.
- **The PDF's Author, Subject and Keywords come from the document's facts**: the firm, then
  the campaign with the department and dates, then the department and issue. It carries no
  creation date, so one document renders to the same bytes every time.
- **Tagged PDF is opt-in.** `PdfProfile(name="tagged", dpi=150, variant="pdf/ua-1")` writes a
  structure tree, the language and every image's alt text. It is not the default, because
  WeasyPrint 70 tags the layout tables as data tables.

## The same content, folded

A brochure is one sheet folded into panels. You hand over the panels in the order a reader
meets them, front cover first; the fold decides which side of the sheet each one prints on
and where:

```python
from pyhermes.brochure import TRI_FOLD_LETTER, Brochure, Panel
from pyhermes.builder import FullWidth, PullQuote, TextBlock
from pyhermes.pdf import save_pdf


def face(title, copy):
    return Panel([FullWidth(content=TextBlock(f"<p>{copy}</p>"), title=title)])


brochure = Brochure(
    {"firm_name": "Hermes Research", "campaign_name": "Rates, Folded"},
    panels=[  # in the order a reader meets them
        face("Rates, Folded", "A quarterly view of the gilt curve, on one sheet."),
        face("Why the curve", "The front end repriced."),
        Panel([FullWidth(content=PullQuote("Duration is back.", attribution="The desk"))]),
        face("Three positions", "Steepeners, linkers and cash."),
        face("About us", "Rates, credit and currencies."),
        face("Talk to the desk", "rates@example.com"),
    ],
    fold=TRI_FOLD_LETTER,
)
save_pdf(brochure, "brochure.pdf")                # both sides, imposed for the press
save_pdf(brochure.proof(), "brochure-proof.pdf")  # plus fold guides and reader labels
```

Four folds ship: `BI_FOLD_LETTER`, `TRI_FOLD_LETTER` (a letter fold, whose inside panel is
1/8in narrower so it closes flat), `Z_FOLD_LETTER` and `GATE_FOLD_A4`. A wrong panel count
raises at construction and lists every face in reader order. Each panel is a fixed box: copy
that overflows it is clipped, never carried onto another panel, and
`pyhermes.brochure.overflowing_panels(brochure)` names any that did.

**The PDF is print-ready but RGB.** Each side carries 1/8in of bleed, with each panel's colour
or picture running into it, and crop and registration marks outside that. A panel whose copy
sits nearer the trim than the fold's safe distance raises. So does an image with fewer than
half the pixels it needs to print at 300 dpi, and one short of the full count warns
with a `PrintQualityWarning`. Converting colour for a press is the print house's step, and the lint pass says so
once per brochure.

The editorial pieces are shared, so a report can use them too: `PullQuote`,
`TextBlock(drop_cap=True)`, `FlowedColumns` for one passage set in columns, and
`TextBlock(figure=ImageBlock(..., wrap="left"))` for a picture the prose wraps round. Each
degrades in an email: the drop cap and the float disappear, and the columns become one.

## Install

Requires Python 3.11+. Not published to PyPI — install from a clone. The distribution and the
import are both `pyhermes` (`from pyhermes.builder import EmailBuilder`). Code written against
the old `svc` import needs its imports changed; nothing else moved:

```bash
pip install -e ".[dev]"     # editable, plus pytest / ruff / mypy
pip install -e ".[pdf]"     # optional: WeasyPrint, to print a document
pip install -e ".[qa]"      # optional: Playwright + pypdfium2, for screenshots
pip install -e ".[data]"    # optional: pandas, to build a table from a DataFrame
pip install -e ".[charts]"  # optional: matplotlib, to build a chart from a Figure
pip install -e ".[math]"    # optional: matplotlib, to render an equation from LaTeX
```

**The optional extras are genuinely optional**, all five of them, and the suite proves it
rather than claiming it: their tests *skip* when the extra is absent, so `pip install -e ".[dev]"` and
`pytest` run anywhere. `[pdf]` needs Pango and Cairo from the system, which is exactly why
it is not in the floor.

`python -m build` makes a wheel and an sdist, and both carry the library alone: the sdist
holds `pyhermes/`, `pyproject.toml`, this README and the [MIT licence](LICENSE), and nothing from
the tests, the QA harness or the tooling. The wheel ships a `py.typed` marker, so your type
checker reads pyHermes's annotations. CI builds, checks and installs both on every change.

The `dev` extra also pulls `requests` and `httplib2`. Those are the HTTP transports the send
adapters *document*, not ones they use: the adapters import neither, and an AST-parsing test
in each keeps it that way. They exist so retry classification can be tested against the real
exception hierarchies — a bug once shipped precisely because the tests only ever injected
builtins.

## Sending

Building is the bulk of the product, but the chain is complete. Assembly is transport-neutral
and pure; the adapters transmit.

```python
from pyhermes.delivery import build_message, save_eml

message = build_message(
    email,
    sender="research@example.com",
    to=["reader@example.com"],       # subject defaults from the email's metadata
)

save_eml(message, "output/preview.eml")   # dry run: no credentials, no network
```

Every message is a `multipart/alternative` — pyHermes generates the `text/plain` part from the
same section tree it renders the HTML from, so there is nothing extra to write and no way for
the two to say different things:

```
multipart/alternative            (an email with no CID images)
├── text/plain
└── text/html

multipart/alternative            (an email with CID images)
├── text/plain
└── multipart/related
    ├── text/html
    └── image/*  × N

multipart/mixed                  (with attachments=[...])
├── multipart/alternative        (either shape above, unchanged)
└── application/pdf  × N         (Content-Disposition: attachment)
```

Text first, HTML last, per RFC 2046's order of increasing preference: a graphical client
renders the HTML, a text-mode client falls back to the part before it. `email.text()` gives you
that part on its own if you want to look at it. There is no opt-out — it is derived and costs
nothing, and suppressing it would hurt both deliverability and the readers who rely on it.

That `.eml` is a faithful preview, not an approximation — `save_eml()` and both adapters
serialise through the same `to_wire_bytes()`, and each adapter asserts the bytes it transmits
equal the bytes written to disk.

To actually send, bring an authorized transport:

```python
from googleapiclient.discovery import build       # your dependency, not pyHermes'
from pyhermes.gmail import GoogleApiTransport, send_message

service = build("gmail", "v1", credentials=creds)  # you authenticate
message_id = send_message(message, transport=GoogleApiTransport(service))
```

```python
import requests                                    # your dependency, not pyHermes'
from pyhermes.outlook import GraphApiTransport, send_message

session = requests.Session()
session.headers["Authorization"] = f"Bearer {token}"
send_message(message, transport=GraphApiTransport(session))   # returns None; Graph gives no id
```

**The adapters take an authorized transport, never credentials.** Each defines a one-method
`Protocol` the caller satisfies. Token acquisition, refresh and revocation stay with the
caller, where an application's secret handling already lives. Three consequences follow, all
deliberate: pyHermes gains no provider SDK dependency, no credential ever touches this code,
and the whole send path is testable with no mailbox, no network, and no recorded HTTP
fixtures to drift.

## The composition model

Every email is **skeleton ← regions ← containers ← components**, and the regions are
`header | banner | body | footer`:

| Layer | What it owns | Where |
|---|---|---|
| **Skeleton** | the whole page — head, preheader, wrapper — with four holes: `{{ header_bar_html }}`, `{{ banner_html }}`, `{{ sections_html }}`, `{{ footer_html }}` | `pyhermes/builder/templates/base.html` |
| **Regions** | the strip (`Header`, `EmptyHeader`), the masthead (`Banner`, `MinimalBanner`) and the close (`Footer`). (The *body* region is the ordered section list — not a class) | `pyhermes/builder/regions.py` |
| **Containers** | layout geometry only: `FullWidth`, `TwoColumn`, `ThreeColumn`, `FourColumn`, at a named ratio or any weights such as `ratio=(60, 40)`; each takes a `background_color` whose type stays readable, a `text_color`, and a `border` | `pyhermes/builder/containers.py` |
| **Components** | content: `CardGroup`, `DataTable`, `ChartBlock`, `ImageBlock`, `TextBlock`, `NumberedList`, `AuthorBlock`, `ContactBlock`, `Button`, `Divider`; and three that hold others, `Stack` (several blocks in one cell), `Columns` (a split inside a cell) and `Callout` (one block in a box) | `pyhermes/builder/components.py`, `composition.py`, `surfaces.py` |

A container holds components, renders each, and embeds the fragments into its own `<tr>`
block sized to the 680px outer table. Each region renders into exactly one slot, and `Email`
drops all of it into the skeleton. A region that fills *no* slot renders nothing — which is
how `EmptyHeader` omits the strip without the skeleton needing a conditional.

**Facts about the email live on `EmailMetadata`; how a region presents them lives on the
region.** The firm name, campaign name, dates and outbound URLs are handed *down* at render
time — a region presents them, it cannot contradict them. Swapping the header region is one
argument, not a template fork:

```python
from pyhermes.builder import EmailBuilder, MinimalBanner

(EmailBuilder()
    .metadata({...})
    .banner(MinimalBanner(logo_url=logo))
    .section(...))
```

The footer always renders its closing block — see **Footer** below for what goes in it. For a
contact call-to-action, add a `ContactBlock` body section instead of putting it in the footer:

```python
from pyhermes.builder import EmailBuilder, FullWidth, ContactBlock

(EmailBuilder()
    .metadata({...})
    .section(FullWidth(content=ContactBlock(
        heading="Get in touch",
        cta_label="Contact Us",
        cta_url="mailto:research@example.com",
    )))
    .build())
```

The pre-split spelling still works: `EmailMetadata(logo_url=…, logo_alt=…, logo_width=…,
header_bg_image_url=…)` builds the header for you.

Adding a content type is a new template file plus a `Component` subclass that sets
`template_path` and implements `context()`.

Column ratios and card orientation are `StrEnum`s that accept either the member or its bare
string — `ratio=ThreeColumnRatio.WIDE_LEFT` is `ratio="50-25-25"`.

## Language

The `lang` attribute on the root element, which is what a screen reader picks its
pronunciation from. It defaults to `"en"`, so an email that says nothing is unchanged.

```python
EmailBuilder().metadata({..., "language": "fr"})        # or "en-GB", "pt-BR", "zh-Hant-TW"
```

The shape is validated — subtags of letters and digits joined by single hyphens — but not
the tag registry: whether `fr-CA` is registered is not this library's business. Right-to-left
layout is *not* included; the attribute alone would claim a support the table geometry does
not honour.

## Viewports

Emails are built for a **680px frame on desktop and a 375px floor on mobile** — the two
widths the QA harness screenshots and asserts. Below 375 an email may scroll sideways: a
wide `DataTable` and an image sized for the desktop column are the first things to overflow.

If you need a narrower floor, measure it — `python -m qa.preview <fixture> --screenshot`
captures both viewports, and `SUPPORTED_WIDTHS` in `qa/screenshots.py` is where the claim
lives.

## Alignment

Where a section's copy sits. Set it on the container; a block inside can disagree.

```python
FullWidth(title="Q3 Outlook", align="center", content=TextBlock("..."))
FullWidth(align="center", content=TextBlock("...", align="left"))   # the block opts out
```

`left`, `center` or `right` — on `FullWidth`, `TwoColumn`, `ThreeColumn`, and on the five
components that carry prose (`TextBlock`, `NumberedList`, `AuthorBlock`, `ContactBlock`,
`ChartBlock`). A container's alignment covers its heading as well as its content.

Unset means inherit, so an email that says nothing renders exactly as before. `CardGroup`
and `DataTable` keep their own alignment inside an aligned section — a KPI cell is centred
because it is a KPI cell, and a table column resolves from its kind. Use `Column`/`Cell` to
align a table.

## Header

The strip at the very top of the email: one band of free-form copy, above the masthead. Its
text is an email-level fact; the region owns how the box presents it.

```python
from pyhermes.builder import EmptyHeader, Header

EmailBuilder().metadata({..., "header_disclaimer": "For illustrative purposes."})
    .header(Header(align="left", background_color="#EEF2F5", text_color="#1B1B1B"))

EmailBuilder().metadata({...}).header(EmptyHeader())   # no strip at all
```

Three fields, and the footer's box takes the same three, so you learn one surface for the
email's two outer boxes. Unset colours are the theme's. The pair ships together rather than
the background alone: a ground you chose makes the theme's text colour a guess.

`EmptyHeader` renders nothing — no band, no empty row. An empty `header_disclaimer` on a plain
`Header` still renders the band, deliberately: "I have no copy" and "I don't want this box"
are different statements, and the variant is the second one.

**`header_disclaimer` is emitted as raw HTML**, as it always has been — escaping untrusted
text in it is your job, with `escape_html()`. It is the same contract as `TextBlock.content`
and `Footer.disclaimer`, and it is worth saying twice for a box this easy to reuse.

## Banner

The masthead is a region you pass, not a template you fork. Omit it and one is built from the
metadata; pass a `Banner` and it renders instead:

```python
from pyhermes.builder import Banner, BannerPalette, MinimalBanner, Rgba
from pyhermes.builder.images import EmailImage

Banner(
    title="Q3 Outlook",                      # unset → firm_name
    subtitle="What the curve is pricing",    # unset → campaign_name
    logo_url=EmailImage.attached("marks/hermes.png", alt="Hermes Research", width=118),
    background_image_url="https://cdn.example.com/masthead.jpg",
)

MinimalBanner(logo_url=...)                  # the same masthead as a flat band, no photograph
```

It lays out as a 2×2 grid: the title with the logo beside it, the subtitle with the optional
`department` beside that, then the date range and issue label. A department nobody sets leaves
no empty line and reserves no height.

The title and subtitle are *presentation* — free-form copy for this email's masthead — while
`firm_name`, `campaign_name` and `department` are facts about the email, and a banner that
renames itself changes only the masthead. The footer's copyright line still says who sent it.

**One colour exception lives here.** Everywhere else you pick a whole `Theme` and never a
colour; the masthead is the one place *you* supply the surface, because a background
photograph is something the theme has never seen. White-on-navy tokens over a pale image are
a guess, so a banner may carry its own palette:

```python
Banner(
    background_image_url=...,
    palette=BannerPalette(
        band="#123A3E", title="#F4EADA", subtitle="#CBD9D6",
        meta="#8FAEA9", accent="#D9A05B", scrim=Rgba("#08211F", 0.45),
    ),
)
```

Every role you leave out takes the theme's own token, so this stays an override of a few
colours rather than a second palette to maintain. It is still an *atom* — validated, frozen,
picked as a set — and it is bounded to the masthead: no other region has one, because no
other region renders on a surface you supplied.

## Footer

The closing block, and the header's counterpart: it takes the **same three box fields**, so
the email's two outer boxes cost one API to learn.

```python
from pyhermes.builder import Footer
from pyhermes.builder.models import FooterLink, LinkRow

Footer(
    align="left",                      # the shared surface, as on Header
    background_color="#1B2A38",
    text_color="#D6E0E8",
    border=True,                       # the footer's own
    disclaimer="<p>Distributed to registered recipients only.</p>",
    link_row=LinkRow(                  # omit it and the default row is built for you
        copyright="2026 Hermes Research — all rights reserved",
        links=[
            FooterLink("Privacy", "https://example.com/privacy"),
            FooterLink("Unsubscribe", "https://example.com/unsubscribe"),
        ],
    ),
)
```

The copyright row is a `LinkRow`, not a template: pass one to add a link, drop one, or reword
the copyright. Leave `link_row` unset and it is built from the email's own facts —
`© {current_year} {firm_name}` plus a link for each of your two URLs that is set, worded by
`unsubscribe_label` and `view_in_browser_label`. An unset URL leaves its link out rather than
rendering an empty `href`.

**pyHermes does not decide what your email must say.** Disclaimer language, unsubscribe links
and every other compliance question are your judgement — the library cannot know whether this
is a commercial newsletter, an internal note or a receipt. So `LinkRow(links=[])` renders a
link-free row and an empty `disclaimer` renders no fine print, and both are valid. What it does
guarantee is that a region *variant* will not silently drop content you supplied, and that what
renders is shape- and safety-valid: hex colours, and URL schemes checked so a `javascript:`
never lands in an `href`.

`Footer.disclaimer` is raw HTML, like the header's — escaping untrusted text in it is your job.
The box stacks **sign-off image → disclaimer → copyright row**, each independently optional.

## Per-exhibit disclosure

`Footer.disclaimer` carries the *document's* legal copy. The sentences that qualify one
figure — *"returns are shown gross of the 0.75% fee"* — belong under that figure, so the
three data exhibits take an optional `disclosure`:

```python
DataTable(
    headers=["Factor", "1M", "YTD"],
    rows=[TableRow(cells=["Value", "+1.8%", "+7.4%"])],
    source="Hermes Research",
    disclosure=(
        "Factor returns are shown gross of fees and transaction costs. "
        "Past performance is not indicative of future results."
    ),
)
```

`ChartBlock` and `ImageBlock` take the same field. It renders as justified fine print
**beneath** the attribution line — the two coexist, and the order is always exhibit,
attribution, disclosure. It projects into the plain-text part too, so a text-mode reader
sees the compliance line rather than a document that quietly omits it.

Unlike the two disclaimers, `disclosure` is **plain text and escaped for you** — pass it
raw, and do not pre-escape. That means no inline link today; the reasoning, and the
figure-specific-vs-document-wide steering that keeps a repeated boilerplate off the 102 KB
budget, are in `.claude/rules/disclosure.md`.

## Numbers, notes, contents and references

A research document is navigated by its apparatus, and pyHermes numbers all of it in Python —
once — so the email, the PDF and the plain-text part agree:

```python
from pyhermes.builder import Contents, DataTable, FullWidth, TextBlock
from pyhermes.document import ContentsPage, PagedDocument, RunningHeader

document = PagedDocument(
    facts,
    contents=ContentsPage(heading="Contents"),              # a sheet after the cover
    running_header=RunningHeader(follow="section"),         # the current section, per sheet
)
document.add_section(FullWidth(title="Factor Returns", content=DataTable(
    headers=["Factor", "1M"], rows=rows,
    caption="Style factor returns", label="Exhibit",        # "Exhibit 1 · Style factor returns"
    source="Hermes Research[^1]", notes=["Equal-weighted across quintiles."],
)))
document.add_section(FullWidth(title="Method", content=TextBlock(
    '<p>The returns in <a class="xref" href="#exhibit-1">Exhibit 1</a> are gross.</p>'
)))
```

| | On paper | In an email | In plain text |
|---|---|---|---|
| `label="Exhibit"` | Exhibit 1 · …, `id="exhibit-1"` | the same | the same |
| `[^1]` + `notes=` | at the foot of the marker's sheet | endnotes after the last section | `[1]`, then a Notes list |
| Contents | `ContentsPage`, with page numbers | the `Contents` component, linked | the titles |
| `class="xref"` | Exhibit 1 (p. 3) | Exhibit 1, linked | Exhibit 1 |
| `follow="section"` | the running header tracks the section | — | — |

- **Exhibits number per label** — `Table 2` and `Figure 1` coexist — in reading order, across
  splits and pages. The separator is `Config.exhibit_separator`.
- **A footnote marker is `[^n]`, local to its component**, and the document renumbers across the
  tree. Every marker must call a note and every note must be called, checked at construction.
  A note is plain text, escaped for you, like `disclosure`.
- **Every titled section is an anchor**, a slug of its title (`#factor-returns`); `anchor=`
  overrides it. Two claimants to one anchor raise when the second is added.
- **A reference to an anchor nothing defines raises** at the start of `render()` or `text()`,
  naming it — which is how a relabelled exhibit is caught before a reader finds it.
  `document.validate()` checks sooner.

The page numbers are the print engine's (WeasyPrint's `target-counter`); everything else is
Python's, which is why the text part can carry it.

## Colour

Every colour and shadow comes from one validated `Theme`, chosen with one metadata field:

```python
from pyhermes.builder import DEFAULT_THEME, EmailBuilder

EmailBuilder().metadata({..., "theme": "slate"})                 # a curated preset
EmailBuilder().metadata({..., "theme": DEFAULT_THEME.derive(     # or your own
    palette={"header_bg": "#1B3A5C", "accent": "#7FA8B8"})})
```

The theme is the unit of customisation — you pick or build a whole one, never a colour at a
call site. Its layers are frozen and validated at construction, so a theme that exists is a
theme that renders. `KpiItem.color` and `TableRow.colors` stay yours: they say something
about the *number*, and the theme only supplies the fallback behind them.

Validation checks shape, not taste — a low-contrast palette is legal and will render.

## Size

Density works the same way, from one more metadata field:

```python
EmailBuilder().metadata({..., "size_theme": "compact"})   # or "standard" / "spacious"
```

Three curated email presets. `compact` fits the same letter into about 17% less height, `spacious`
gives it 23% more, and every font size, line-height, padding, gutter and column width follows
— including the mobile `@media` overrides, so an email is never desktop-themed and
mobile-standard. Column widths are computed from the frame rather than hardcoded, so they
still fill the content width to the pixel at any density.

A fourth preset, `dense`, is tuned for print: a table row about 21px tall where `compact`
gives it 37, which is what a two-sheet factsheet needs. You set spacing with three controls,
from the general to the particular, and none of them takes a px string:

```python
# 1. A preset for the whole document.
PagedDocument({..., "size_theme": "dense"})

# 2. A house density, derived from a shipped one, passed as the object.
HOUSE = COMPACT_SIZES.derive(space={"content_top": 8}, component={"table_cell_pad": 5})
PagedDocument({..., "size_theme": HOUSE})

# 3. One object, and everything inside it, moving named tokens.
DataTable(headers, rows, spacing=Spacing(table_cell_pad=3))
FullWidth(content=table, title="Returns", spacing={"content_top": 6})
```

An override can name only the tokens that object's template reads. It cannot change a width,
a type size or a line-height. `Page(..., spacing=...)` reaches every section on the sheet.

The email takes more care, because its density meets the clipping limit, Outlook's Word
engine and the mobile collapse at once. An `Email` refuses `dense` and a custom scheme until
you have rendered yours in the clients you send to and set
`Config(allow_custom_email_density=True)` or `PYHERMES_ALLOW_CUSTOM_EMAIL_DENSITY=1`. It also
refuses an override of a token its mobile `@media` block reads (`pad_x` and the card padding),
which would render one way wide and another collapsed.

## Typeface

The third axis, and the same shape as the other two:

```python
from pyhermes.builder import DEFAULT_FONTS, EmailBuilder, FontStack

EmailBuilder().metadata({..., "font_theme": "modern"})              # or "classic"
EmailBuilder().metadata({..., "font_theme": DEFAULT_FONTS.derive(   # or your own
    heading=FontStack("Publico", "Georgia", "serif"))})
```

Four roles — `heading`, `body`, `label`, `numeric` — named by the job a face does rather than
by the face doing it, so a theme can move the titling without touching the reading copy or the
figures. That is what `modern` is: a sans display and sans chrome over the default serif body,
with the data table's mono held so its columns still align.

Every stack must end in a generic family (`serif`, `sans-serif`, `monospace`). Email clients
give no webfont guarantee and Outlook substitutes silently, so the terminal is what decides
what a reader actually sees. There are no webfonts here for the same reason: a font-CDN
`<link>` is the external stylesheet the lint pass denies outright, and an `@font-face` block
fetches a font file the major clients strip or ignore.

A face swap moves no px — sizes belong to `size_theme` — but rendered line lengths do move with
the metrics, which is what the screenshots are for.

## Data tables

The one component with real structure, and the only table in the email that carries table
semantics — every other table is layout scaffolding marked `role="presentation"`.

```python
DataTable(
    caption="Sleeve performance, gross of fees",
    headers=["Sleeve", Column("Manager", kind="text"), Column("Weight", align="center"), "1M"],
    rows=[
        TableRow(["Equities"], kind="subhead"),
        TableRow(["Global core", "Ashford", "18%", Cell("+1.8%", color="#4A7C59")]),
        TableRow(["Total", "", "100%", "+0.6%"], kind="total"),
    ],
)
```

Headers take bare strings or `Column` objects and cells take bare strings or `Cell` objects,
mixed freely — so every table written before these existed keeps working unchanged.

- **Columns** carry an `align` and a `kind` (`text` or `numeric`). Unset, they resolve from
  position — first column text and left, the rest numeric and right — which is what the
  library did before they were expressible.
- **Cells** carry an `align`, a `color` and a `background`. The two colours are the caller's
  claim about a *figure* — *this is down*, *this mark is stale* — not a styling surface;
  there is no cell font, size or border, deliberately.
- **Rows** carry a `kind`: `data`, `total` or `subhead`. A total is ruled off and bold; a
  subhead is a label band. Unlike a cell's colour, a row's kind draws only from the theme.
- **Alignment is resolved once and read by both projections**, so the HTML and the plain-text
  part can never disagree about which column is the label.
- **The table is named and navigable**: the caption is its accessible name, the heading row is
  `scope="col"` and the label column is `scope="row"`.

A quantitative table has more words (epic #217). Groups span the heads, a units row states each
unit once, a column formats and tones the raw figures it is given, and the figures line up on
the point:

```python
from pyhermes.builder import ColumnGroup, HeatScale
from pyhermes.builder.formats import pct

ret = lambda v: pct(v, 1, sign=True)
DataTable(
    headers=[
        "Class",
        Column("1Y", format=ret, tone="auto", unit="%", align_decimal=True),
        Column("3Y", format=ret, tone="auto", unit="%", scale=HeatScale(0, 0.1)),
        Column("Weight", format=lambda v: pct(v, 1), bar=True),
    ],
    groups=[ColumnGroup("Share class"), ColumnGroup("Annualised", 2), ColumnGroup("Book")],
    rows=[TableRow(["Accumulation", 0.0452, 0.0612, 0.62]),
          TableRow(["Income", -0.0031, Cell("4.1%[^1]", value=0.041), 0.38])],
    notes=["The income class launched a year later."],
)
```

- **Groups** are a second header row, `scope="colgroup"`, the one place a span is allowed. A
  print engine repeats the whole head on every sheet.
- **A raw figure** in a row is written by its column's `format` at construction. The markup
  and the text part print that one string, and the number stays on the cell as `value`.
- **A `[^n]` marker** in a cell or a head joins the table's notes, like one in its caption.
- **`scale`** tints each cell from the theme's surface toward its positive token, or toward
  negative below a `mid`. **`bar`** draws the figure as a bar in the accent colour. Neither
  takes a colour from you, and neither changes the text part.

## Figures as numbers

Pass numbers, not strings. `pyhermes.builder.formats` formats a figure once, and both the HTML and
the plain-text part read the same string:

```python
from pyhermes.builder.formats import bps, compact, money, pct

pct(0.0142, sign=True)   # '+1.42%'
bps(0.0006)              # '+6 bps'
money(-1200)             # '-$1,200'
compact(1_240_000_000)   # '1.2bn'
```

Rounding is half up (`0.125` is `0.13`), the output is ASCII, zero is never signed, and a
missing figure renders as `--`. There is no `locale`: pass `thousands=` and `decimal=`.

**A cell or card can carry a tone instead of a colour.** `tone="positive"`, `"negative"` or
`"neutral"` renders in the active theme's semantic colour, so a toned table recolours with the
theme. `Cell.from_number` formats and tones in one step. The sign decides unless you say
otherwise, and a figure shown as zero is never coloured:

```python
from functools import partial
from pyhermes.builder import Tone
from pyhermes.builder.models import Cell, KpiItem, TableRow

ret = partial(pct, dp=1, sign=True)
TableRow(["Momentum", Cell.from_number(-0.004, ret)])        # '-0.4%', negative
KpiItem("VIX", "14.32", sublabel="-2.18 pts", tone=Tone.POSITIVE)  # down is good news
```

An explicit `color=` still wins over a tone.

**A DataFrame or a matplotlib Figure can be passed directly**, through `pyhermes.data`
(`[data]` and `[charts]` above):

```python
from pyhermes.data import chart_from_figure, table_from_frame

table = table_from_frame(df, formats={"1M": ret}, tones={"1M": "auto"},
                         total_row=True, source="Hermes Research")
chart = chart_from_figure(fig, alt="Cumulative returns", width=320,
                          source="Hermes Research")
```

The frame's dtypes decide each column's kind, and a named index becomes the row-header
column. The chart is rendered at twice its display width and attached by `cid:`. pyHermes
never styles the plot; it takes the Figure you drew.

**An equation is written in LaTeX**, through `pyhermes.math` (`[math]` above). It renders to an
image in every medium, because no mail client shows MathML, and the source stays with it as
the alt text and the plain-text projection:

```python
from pyhermes.math import math_block

variance = math_block(r"\sigma_p^2 = w^\top \Sigma w", label="Equation",
                      caption="Portfolio variance", theme="classic", size_theme="standard")
tails = math_block(lines=[r"\text{VaR}_{99\%} = -q_{0.01}(r)",
                          r"\text{ES}_{99\%} = \mathbb{E}[r \mid r \leq q_{0.01}]"],
                   label="Equation", caption="Tail risk")
```

It is numbered like any exhibit ("Equation 2", `#equation-2`), and on paper it never splits
from its caption. The glyphs are painted at build time in the theme and density you pass, so
render them for the theme the document uses. mathtext is a subset of TeX: `\leq` rather than
`\le`, `\dfrac` for a display fraction, and no `aligned` environment. Several lines are set
as one block.

## What it enforces

These are the failures that are invisible until a reader reports them, so they are checked
rather than documented:

- **The 102 KB Gmail clipping limit.** `render()` raises `SizeError` above it and warns above
  90 KB with a `SizeWarning`. Both thresholds are configurable, so a non-Gmail channel can raise them deliberately
  rather than by commenting out the check.
- **Validation at construction, not at render.** Models and components raise `ValidationError`
  from `__init__`; by the time you call `.render()`, the data shape is already known good. The
  one document-wide check, that every `#reference` lands, runs before any template loads.
- **Missing template variables fail loudly** — Jinja2 runs under `StrictUndefined`.
- **URL schemes.** `http`, `https`, `mailto`, `cid` and relative URLs are allowed;
  `javascript:`, `data:`, `vbscript:` and `file:` are rejected at construction.
- **Colors are `#RRGGBB`**, checked in Python and again in the templates.
- **Alt text is required** on every image — it is what the reader sees whenever images are
  blocked, which for Outlook desktop is the default state.
- **Layout tables say they are layout.** Table-based layout is mandatory in email, so every
  structural table carries `role="presentation"` and the one real data table carries `scope`
  on its headers instead. Without that a screen reader announces each layout table's
  dimensions before any content — 68 times in a full-length email. The lint pass checks both
  directions, since marking *every* table would strip the semantics from the one that needs
  them.

**Autoescape is off, and escaping is split by field kind.** HTML email needs raw output, so
it is explicit: plain-text fields (titles, KPI labels, table cells, author names) are escaped
by the builder — pass them as raw text, since pre-escaping now double-escapes. HTML fields
(`TextBlock.content`, `NumberedItem.body`, the metadata disclaimers) are emitted raw, so
escaping untrusted text in those is the caller's job — use
`from pyhermes.builder.filters import escape_html`. Attributes are always escaped.

## Images

An image carries two independent facts: where the bytes live, and how they reach the reader.

```python
from pyhermes.builder.images import EmailImage

EmailImage.hosted("https://cdn.example.com/chart.png", alt="Factor returns")   # REMOTE
EmailImage.attached("charts/factor.png", alt="Factor returns", width=616)      # CID
EmailImage.inline(png_bytes, alt="Sparkline", width=120)                       # DATA_URI
```

| Strategy | Size cost | Gmail | Outlook desktop |
|---|---|---|---|
| `REMOTE` | none | proxied and cached | blocked until "download images" |
| `CID` | *message* size, not HTML size | renders; may show a paperclip | renders immediately |
| `DATA_URI` | +33% base64, into the 102 KB budget | **stripped entirely** | will not render |

**The builder declares a CID embed; it never performs one.** Attaching a MIME part is a
transport act, so the builder emits the HTML *and* an asset manifest: for every `src="cid:X"`
in the output, `email.assets()` has the entry describing what to attach as `X`.
`build_message()` consumes that pair, and cross-checks it — a referenced-but-unattached id is
a broken image the reader sees, so it raises; an attached-but-unreferenced asset only costs
message weight, so it warns.

Format is sniffed from magic bytes rather than the extension (PNG, JPEG, GIF only — WebP and
SVG are detected specifically so the rejection can say why). Content-IDs are content-addressed,
so the same image used twice is attached once. `width` is emitted as the HTML attribute,
because Word ignores `max-width`.

## Configuration

Every judgment-call number is a field on one frozen `Config`:

```python
from pyhermes.config import Config, get_config, set_config, config_override

get_config().inline_image_limit_kb               # what is actually in force
set_config(Config.from_env())                    # the process-wide default, at startup
with config_override(retry_max_attempts=1):      # this thread or task only
    ...
Email(facts, config=Config(size_limit_kb=500))   # this document only
build_message(email, sender=..., to=..., config=Config(attachment_limit_kb=10240))
```

Three levels, and the innermost wins: a document's or a message's own `config`, then the
context's `config_override`, then the default `set_config` installed. An override belongs to
the thread or asyncio task that entered it, so two renders in one service cannot read each
other's limits; a thread you start begins from the default, so hand it a `Config` explicitly.

The line it draws is between **a judgment call and a fact about the world**. The inline-image
cap, the retry ladder and the request timeout were picked by someone, and a picked number you
cannot revisit without editing the library is a bad default wearing a constant's clothes.
Graph's `202 Accepted`, the transient status families and the Content-ID character set
describe what a provider *does* — changing them would not tune behaviour, it would make the
code wrong about its environment, so they stay literals.

Nothing reads the environment on import; `from_env()` is explicit. Consumers call
`get_config()` at use time, so an override installed after import is still seen. An explicit
argument always beats the config.

**A house template overlays the packaged ones.** Pass `template_overlay=` a directory (or
several) to `Email`, `EmailBuilder`, `PagedDocument` or `Brochure`, and a file there at a
packaged path, such as `regions/footer.html`, replaces that one template while every other still
comes from the package. A `Component` of your own sets `template_path` to a file in it.

**A soft limit is a warning, never a line on stdout.** The library prints nothing. Crossing a
size threshold raises a `SizeWarning`, and an image short of its print resolution a
`PrintQualityWarning`; both are `UserWarning`s pointing at your own call, so
`warnings.filterwarnings("error", category=SizeWarning)` makes one fatal and
`logging.captureWarnings(True)` sends them to your logger. The hard limits still raise.

## Development

```bash
pytest                                    # 714 tests: validation, error paths, size limits
ruff check . && ruff format --check .
python -m mypy                            # config in pyproject: files = ["pyhermes", "qa"]
```

CI runs all four on every pull request (and on pushes to `main`), across Python 3.11 and
3.13, plus two more jobs: one builds the wheel and renders an email from a clean venv
outside the source tree — templates ship inside the package, and that job is what keeps
non-editable installs working — and one renders the fixture gallery through headless
Chromium and uploads the PNGs, so a visual change is reviewable from the pull request.

`qa/fixtures/` is the gallery — `minimal`, `kitchen_sink` and `image_matrix`, each a
deterministic email built in code. The suite renders all three, checks that every `cid:`
reference has a manifest entry, that a second build is byte-identical, and that each still
matches its golden. To look at one, use the `preview` command below rather than a scratch
script.

### Golden snapshots

Every fixture is pinned byte-for-byte in `qa/fixtures/goldens/` — the rendered HTML, and
the asset manifest as a short text table (content-id, MIME type, byte length, filename).
Any change to a template, a component or the skeleton that moves an email fails the suite,
naming the fixture, the line, the byte offset and both versions of the line that moved.

Regeneration is deliberate and opt-in:

```bash
pytest --update-goldens      # rewrite the goldens from the current render
git diff qa/fixtures/goldens # read every line of it before committing
```

Nothing regenerates automatically, and a missing golden fails rather than being created —
a golden that writes itself on first run pins whatever happened to be true that day.
**A golden diff in a pull request is a claim that the visual change is intended**, and it
is reviewed as one.

### Screenshots

Renders the gallery through headless Chromium so a visual change can be looked at without
checking out the branch:

```bash
pip install -e ".[qa]" && playwright install chromium
python -m qa.screenshots                 # the whole gallery → output/screenshots/
python -m qa.screenshots kitchen_sink    # one fixture
```

Two viewports per fixture — `chromium-desktop` (1000px) and `chromium-mobile` (375px, below
`base.html`'s 700px breakpoint, so the mobile rules actually fire). `cid:` images are swapped
for data URIs **in the screenshot copy only**, since a browser has no MIME message to resolve
them against; the rendered HTML and the goldens are untouched.

**These are checks, not artifacts.** They are gitignored, never diffed, and never committed.
Viewports and scale factor are pinned; the *browser build* is not — each run records the
Chromium version that produced it in `run.json` beside the images. And the names say
`chromium` on purpose: this approximates Gmail in a browser and says nothing about Outlook's
Word engine, which is the client most likely to break a layout. Client compatibility belongs
to the lint pass ([#60](https://github.com/RorySullivan1/pyHermes/issues/60)).

Playwright is the optional `[qa]` extra, so `pip install -e ".[dev]"` and `pytest` stay
browser-free — the screenshot tests skip rather than fail. Where the environment supplies its
own Chromium instead of one Playwright manages, point `PYHERMES_CHROMIUM` at the binary.

### The lint pass

Portability checks over rendered HTML — the rules that decide whether an email survives
Outlook, enforced rather than merely documented:

```python
from qa.lint import lint_email, format_findings

print(format_findings(lint_email(email)))
```

`img-width-attr` and `img-alt` (Outlook's Word engine ignores CSS `max-width`, and blocked
images are its default state), `no-external-css`, `outlook-unsupported-css`,
`outlook-line-height` (Outlook Classic ignores a unitless `line-height`),
`outlook-transparent-background`, `empty-url`, and `size-budget` — which reports the 90/102
KB thresholds **and attributes the bytes to sections**, so a too-large email says what to cut
rather than only how much.

The suite lints every gallery fixture. Each rule carries a citation, and the linter parses
the HTML rather than grepping it — including the conditional comments, so an Outlook-specific
rule stays quiet about markup that is hidden from Outlook.

### One command for the whole loop

`preview` builds an email, saves it, and optionally lints and screenshots it —
for a gallery fixture or for your own in-progress draft:

```bash
python -m qa.preview --list                              # what fixtures exist
python -m qa.preview kitchen_sink --lint --screenshot
python -m qa.preview drafts/weekly.py:build --lint --open
```

The second form takes any zero-argument callable returning an `Email` or an `EmailBuilder`,
which is what makes this useful for drafting a real newsletter rather than only for inspecting
fixtures. Exit codes are meant for a shell: `0` clean, `1` lint errors, `2` the email could not
be built. A missing browser is not a failure — `--screenshot` says so and carries on, since the
`[qa]` extra is optional.

`qa/` is not shipped in the wheel, so there is no installed `preview` entry point: the module
form is the interface.

## Scope

**In:** composing the document, rendering it for an email client, a page or a folded sheet,
assembling the MIME message, transmitting it through Gmail or Microsoft Graph, printing it
to PDF, and attaching that PDF to an email.

**Out, deliberately:** OAuth flows (the caller's, by design); campaign management — no
scheduling, recipient lists, batching or send-time analytics; open tracking and link
rewriting. On the paged side: no index, bibliography or list of figures, no multi-level
numbering, and no DOCX or PPTX exporter — each is a new epic on the same contract rather
than a gap. On the folded side: no CMYK, ICC profile or PDF/X, no booklet imposition, and no
dielines or die-cut, foil or stock metadata.

## Layout

```
pyhermes/
├── config.py     the tunable numbers, in one frozen dataclass
├── builder/      the shared kit: Document, Medium, templates, components, the three axes
├── email/        the email medium: the four slots and the Gmail size check
├── document/     the paged medium: PagedDocument, Page, Cover, running boxes, back matter
├── brochure/     the folded medium: Brochure, Panel, the folds, imposition, print checks
├── delivery/     transport-neutral MIME assembly + shared retry policy
├── gmail/        Gmail send adapter
├── outlook/      Outlook send adapter over Microsoft Graph
├── pdf/          the PDF exporter, on the adapters' contract — no network; profiles, attachments
└── data/         DataFrame -> table and Figure -> chart, each an optional extra
qa/               the fixture galleries, goldens, screenshots, lint, preview CLI
tests/            pytest suite
```

Design rationale, the reasoning behind each constraint, and the decisions recorded as
non-features live in [CLAUDE.md](CLAUDE.md). Open work is tracked in
[GitHub issues](https://github.com/RorySullivan1/pyHermes/issues), organised as epics.
