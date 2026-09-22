---
paths:
  - "svc/**/*"
  - "qa/**/*"
  - "tests/**/*"
---

# The annotated repo map, and the standing rules the harness enforces

## Directory map

```
svc/
├── config.py           ← the tunable numbers, in one frozen dataclass
├── builder/            ← the shared kit: everything every medium has
│   ├── __init__.py     — public API surface (re-exports everything below)
│   ├── engine.py       — TemplateEngine + BoundEngine (binds theme, size, font, medium;
│                         a ChoiceLoader searches the medium's overlay before the root)
│   ├── medium.py       — Medium + DEFAULT_MEDIUM: skeleton, slots, page, constraints
│   ├── document.py     — Document: metadata + sections + the three projections
│   ├── email.py        — Email(Document) + EmailBuilder (fluent): the four-slot region set
│   ├── regions.py      — Region base + Banner/MinimalBanner, Footer
│                         (body = the section list, deliberately not a class)
│   ├── containers.py   — Container, FullWidth, TwoColumn, ThreeColumn (+ `highlight=` property)
│   ├── components.py   — Component, CardGroup, DataTable, ChartBlock, ImageBlock, TextBlock, NumberedList, AuthorBlock, ContactBlock
│   ├── models.py       — EmailMetadata (the email's facts), Card, KpiItem, TableRow, NumberedItem, SectionConfig
│   ├── images.py       — EmailImage (hosted/attached/inline), ImageAsset manifest, format sniffing
│   ├── enums.py        — StrEnum vocab: TwoColumnRatio, ThreeColumnRatio, CardOrientation, EmbedStrategy, ImageAlign, SizeTheme
│   ├── theming.py      — Theme (Palette/TextColors/SemanticColors/ShadowStyle),
│                         DEFAULT_THEME, SLATE_THEME, THEMES, resolve_theme
│   ├── typography.py   — FontStack, FontTheme (heading/body/label/numeric),
│                         DEFAULT_FONTS, MODERN_FONTS, FONT_THEMES, resolve_font_theme
│   ├── sizing.py       — SizeScheme (TypeScale/SpacingScale/ComponentScale/FrameGeometry),
│                         STANDARD/COMPACT/SPACIOUS_SIZES, SIZE_SCHEMES, resolve_size_scheme,
│                         column_layout() — the frame arithmetic eight templates used to hold
│   ├── textgen.py      — the plain-text projection's shared half: html_to_text() (#108's
│                         closed-tag-set degrader) + the formatting policy — wrap, underline,
│                         table, join_blocks/join_sections, format_link/link_line
│   ├── filters.py      — Jinja filters (e.g. validate_hex_color)
│   ├── formats.py      — finance formatters (#177): number, pct, bps, delta, money,
│                         compact; stdlib only, half-up, ASCII. `data-layer.md`
│   ├── exceptions.py   — EmailBuilderError hierarchy
│   └── templates/      ← packaged with the wheel (moved here in #10)
│       ├── base.html                — the EMAIL skeleton (four slots: header_bar_html,
│                                      banner_html, sections_html, footer_html)
│       ├── document/base.html       — the PAGED skeleton (@page, five slots), reached
│                                      by the document medium's template overlay
│       ├── document/page.html       — the sheet-boundary wrapper (a `tr`, not a `div`)
│       ├── document/regions/*.html  — cover.html, back-matter.html, and running-box.html
│                                      which emits CSS rather than markup
│       ├── regions/*.html           — header-bar.html, banner.html, banner-minimal.html,
│                                      footer.html
│       ├── common/containers/*.html — layout geometry: full-width.html + columns.html
│                                      (one file for every split since #42; widths computed)
│       ├── analysis/*.html          — data components (card-group, data-table, chart-block)
│       ├── media/*.html             — image components (image-block)
│       └── text/*.html              — text components (text-block, numbered-list, author-block, contact-block)
├── delivery/           ← transport-neutral MIME assembly (consumes the builder)
│   ├── __init__.py     — public API: build_message, save_eml, collect_cid_references
│   ├── message.py      — build_message() → multipart/alternative (text first, HTML last,
│                         related nested); to_wire_bytes(); save_eml()
│   ├── retry.py        — retry_with_backoff(): shared policy, per-adapter classification
│   └── exceptions.py   — DeliveryError / MessageError / TransportError (siblings of
│                          EmailBuilderError)
├── email/              ← the email medium: the Gmail size constraint, the four slots
├── document/           ← the paged medium
│   ├── medium.py       — PAGED_MEDIUM, paged_medium(page)
│   ├── document.py     — PagedDocument: cover | running boxes | body | back matter
│   ├── page.py         — Page: a sheet boundary that FLATTENS in a non-paged medium
│   └── regions.py      — Cover, RunningHeader/Footer (@page margin boxes), BackMatter,
│                         plus an Empty variant of each
├── gmail/              ← Gmail send adapter (consumes delivery; owns no credentials)
│   └── sender.py       — GmailTransport protocol, GoogleApiTransport shim, send_message()
├── outlook/            ← Outlook send adapter over Microsoft Graph (same shape as gmail)
│   └── sender.py       — OutlookTransport protocol, GraphApiTransport shim, send_message()
├── data/               ← the data adapters (#179, #180); "[data]" and "[charts]" extras
│   ├── frames.py       — table_from_frame: a DataFrame as a DataTable
│   ├── charts.py       — image_from_figure / chart_from_figure: a Figure as an image
│   └── exceptions.py   — DataError, BackendMissingError (a sibling of EmailBuilderError)
├── pdf/                ← the PDF exporter, on the adapters' contract; "[pdf]" extra
│   ├── exporter.py     — render_pdf / save_pdf / page_count / available; lazy backend
│   ├── fetcher.py      — serves cid: from the manifest, refuses every other URL
│   └── exceptions.py   — PdfError, a sibling of EmailBuilderError and DeliveryError
qa/                     ← QA harness (epic #54); NOT shipped in the wheel
├── goldens.py         — the golden snapshot harness: check_fixture(), write_fixture(),
│                        render_manifest(), and the diagnosable mismatch report
├── screenshots.py     — headless-Chromium runner: `python -m qa.screenshots`, cid→data URI
│                        substitution, run.json recording the browser build
├── lint.py            — email-client portability rules over rendered HTML: lint_html(),
│                        lint_email(), size_report(), SOURCES, DEFERRED_RULES
├── preview.py         — the CLI that composes the rest: `python -m qa.preview <target>`
│                        [--lint] [--screenshot] [--open] [--list]
└── fixtures/          — the gallery: minimal, kitchen_sink, image_matrix, minimal_banner,
                        minimal_footer, slate_theme, compact_size, spacious_size,
                        + all_fixtures()
    └── goldens/       — the checked-in snapshots: <name>.html + <name>.assets.txt
                          + <name>.txt (the plain-text projection, #110)
output/                 — generated email HTML (gitignored; not committed)
tests/                  — pytest unit suite (validation, error paths, size limits)
.github/workflows/      — CI: ruff, mypy, pytest
.claude/                — curated tooling library (skills, agents, commands, hooks, memory)
```

### Standing rules the harness enforces

These are not conventions to remember — each has teeth, and the teeth are named:

1. **A new component joins `kitchen_sink()`.** Not by good intentions: a completeness test
   introspects every public `Component` subclass exported from `svc.builder` and fails when
   one never appears in the fixture. The same holds for a new `EmailMetadata` field, which is
   additionally checked to differ from its own default — a field left at its default is one
   the golden cannot pin. Exemptions are named in `DEPRECATED_COMPONENTS`, with a reason.
2. **A golden diff in a PR is a claim that the visual change is intended.** Regeneration is
   `pytest --update-goldens` and nothing else; a missing golden fails rather than being
   created. Never regenerate to silence a failure — if the diff is not one you meant to make,
   the change is wrong, not the golden.
3. **Screenshots approximate Gmail-in-a-browser; the lint pass owns Outlook; the PDF
   rasterisation owns pagination.** "The screenshot looks fine" never closes a
   compatibility question — Chromium renders `display:flex` perfectly and Outlook's Word
   engine does not. The filenames say `chromium` for exactly this reason. Conversely, a
   clean lint says nothing about whether the layout *reads* well; that is what the images
   are for. **The third clause is #165's**: a browser renders a paged document's HTML as
   one long scroll, which is precisely the property that medium does not have, so a paged
   fixture is rastered from its PDF one image per sheet — and #164 is why it earns a clause
   rather than a footnote, since the first real PDF put a folio on its own cover and
   shrink-wrapped every table to 188px, both of them correct markup to every other check.
4. **A new template takes its colours from the `theme` namespace.** A hardcoded hex or
   `rgba()` literal in a template is a bug — it is a colour outside the palette, which is
   the drift epic #46 exists to end. Two tests enforce it: one asserts no literal survives
   in any template, another that none survives as a default in Python. There are **no
   documented exceptions**; the audit found none that needed one. Watch the two blocks that
   carry their own copies of surface and text colours — the dark-mode forcing block and the
   mobile `@media` rule — because if they stop reading the same tokens as the inline styles
   they override, a themed email renders half-themed in exactly the clients hardest to test.
5. **A new template takes its sizes from the `size` namespace.** The same rule as 4, for
   the other epic: a hardcoded scale-participating px is a size outside the scheme, which is
   the drift epic #45 exists to end. One test fails on any `font-size` / `line-height` /
   `padding` / `margin` declaration in a template that is neither tokenised nor on the named
   exception list; a second fails if a *documented* exception stops being used, so the list
   cannot outlive its reasons. The exceptions are four, each structural rather than
   scale-participating: the preheader's `font-size:1px` hider, the accent rule's
   `font-size:0; line-height:0` spacer cell, the `padding:1px 1px 1px 1px` hairline frame of
   a highlighted band, and all-zero resets. Border widths, border radii, `arcsize`,
   `letter-spacing` and `text-shadow` offsets are shape rather than density and stay literal.
   Watch the `@media` block for rule 4's reason exactly: overrides carrying their own
   literals leave an email desktop-themed and mobile-standard.
6. **A new template takes its faces from the `font` namespace.** The third of the same
   rule, for the third axis: a hardcoded `font-family` is a face outside the vocabulary,
   which is the drift epic #56 exists to end. One test fails on any `font-family`
   declaration that is not a `{{ font.* }}` read, and there is **no exception list** — the
   audit found none that needed one, unlike sizes' four structural px. A second test renders
   the gallery's widest email under a sentinel `FontTheme` and asserts every role appears
   *and* that no shipped family survives, which is what catches a token bypassed rather than
   merely absent. **The watch-site is the `[if mso]` block**, not the `@media` one: `body,
   td, th { font-family: … }` is Outlook's floor for everything, so a literal there renders
   a themed email custom-faced in Gmail and Georgia in Outlook — the half-themed failure in
   the client hardest to check. The dark-mode and `@media` blocks carry no faces today, and
   a test asserts that too, so a future edit adding one has to tokenise it like everything
   else.
7. **A region that carries images must declare them.** Same rule components already have,
   and the same failure if you skip it: the bytes never reach `Email.assets()` and the
   `cid:` reference renders as a broken image. Declaring means listing the field in
   `IMAGE_FIELDS` — `Region.images()` walks it — or overriding `images()` if the bytes come
   from somewhere else. `Email.images()` is **header + banner + sections + footer**, so the
   region is the only owner of its own images. The header and footer participate even though
   no shipped variant of either carries an image: a test builds a footer that does, because
   the slot has to work *before* someone writes that variant for real.
8. **A new template's tables declare what kind they are.** A layout table takes
   `role="presentation"`; a real data table takes none and gives its header cells
   `scope="col"` (#114). Both directions are enforced by the `table-role` lint rule, because
   the failure is invisible in every browser and every screenshot — an unmarked layout table
   renders identically and simply announces itself to a screen reader as a data table with
   dimensions, once per table. The gallery emits 68 tables for one email, so this is the
   difference between an email a screen-reader user can read and one they cannot.
9. **A new *property* on a component or a container joins the gallery, at a non-default
   value.** Rule 1
   covers a new component *class*; this covers its fields, which had no rule at all until
   epic #116 added seven of them. `TestComponentFieldsAreExercised` introspects
   `DataTable`, `Column`, `Cell` and `TableRow`, the five prose components' `align`, and
   every `Container` field, failing when one is never set to anything but its default —
   because a field at its default is one the golden cannot pin. #121 recorded it as **a
   first instance, not a special case**, and #128 cashed that: epic #124 was the next axis,
   so the rule widened rather than letting eight new fields go unpinned. **Containers had
   never been covered at all**, and widening to them immediately found that
   `Container.background_color` — the *original* entry in the closed colour list — had
   never been set by any fixture in the gallery's life. That is the shape to expect: the
   rule pays for itself on the layer nobody thought to check.
10. **A new component must implement `text()`, and absence fails loudly.** The mirror of rule
   7 with the **opposite default**: an absent image list is empty, an absent projection is a
   `NotImplementedError` naming the class. A component with no visual content can exist — a
   spacer would — but a *content* component invisible to text-mode readers is the
   accessibility failure epic #53 exists to fix, so it fails the first email that projects it
   rather than vanishing from the text part silently. A completeness test rides `kitchen_sink`
   and needs no hand-list; a second holds that the projection routes through
   `_with_subtitle`, which is what a new component would forget.

## The service layer's two seams, stated in full

Moved out of `svc/__init__.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
pyHermes Service Layer
======================

svc/
├── builder/     — OO email assembly (Jinja2): HTML + an asset manifest.
├── delivery/    — transport-neutral MIME assembly: HTML + manifest → message.
├── gmail/       — Gmail send adapter: message → the wire.
└── outlook/     — Outlook send adapter, over Microsoft Graph.

The seam between builder and delivery: the builder *declares* CID embeds
(for every ``src="cid:X"`` in the HTML, ``Email.assets()`` has the entry
describing what to attach as ``X``), and delivery *performs* them.

The seam between delivery and an adapter: delivery assembles bytes, an
adapter transmits them. Adapters own their provider's wire contract and
error semantics; they never own authentication, so pyHermes has no
dependency on any provider SDK.

Usage::

    from svc.builder import CardGroup, EmailBuilder, FullWidth
    from svc.builder.models import Card, KpiItem
    from svc.delivery import build_message, save_eml
    from svc.gmail import GoogleApiTransport, send_message
```

11. **Prose is bounded, and the bound is checked.** A file states its purpose; a class may
   argue its design; a function states its contract; a comment marks a trap. Added by epic
   #134, and the teeth are `tests/test_prose_budget.py` reading
   `.claude/hooks/prose_budget.py` — the *same* measurer as the edit-time advisory hook, so
   a CI failure and an in-session notice cannot disagree about the rule. The caps are in
   `.claude/prose-budget.json`, the exemptions in `qa/prose_baseline.json`, and a second
   test asserts every exemption **still violates**, so one cannot outlive its reason.
   **The baseline may only shrink.** A decision that leaves a docstring is *moved* — to a
   rules file, or to the code it concerns — never deleted; `knowledge-router` decides which.

## Epic #134 — what the prose clean-up found

Two findings outlive the epic, and both are about mechanisms rather than taste.

**Comments ship.** 5.2% of a rendered email was commentary — 1,828 bytes in every
message, 14.8% of the smallest fixture. The 102 KB clipping limit this whole package is
organised around was being spent on prose no recipient reads. A Jinja comment costs
nothing and reaches the only audience that wants it; an HTML comment is downloaded by
everyone. #137 cut the shipped bytes by 79% with no rendered geometry moving.

**The mechanism existed and was bypassed.** `.claude/context/` was created for exactly
the split #136 performed, and `CLAUDE.md` grew to 2,045 lines instead — while
`.claude/memory/INDEX.md` opened with "keep at most 80 lines" at 256 lines long. A
structure nobody is *required* to use is a structure that decays. That is why the epic
ends with a check rather than a convention, and why the check is advisory at edit time
but a gate in CI: an advisory that blocks gets deleted, and a convention that never fails
gets ignored.

A third, smaller, worth keeping because it cost real time: **a measurer can be wrong about
scope.** 64% of the flagged comment blocks were `#:` attribute docs — the documented way
to describe a public constant. Making the code fit that measurement would have deleted
correct API documentation; the fix was a new scope in the measurer (#138). When a check
fires on code that looks right, check the check.

