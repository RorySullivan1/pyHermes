---
paths:
  - "pyhermes/**/*"
  - "qa/**/*"
  - "tests/**/*"
---

# The annotated repo map, and the standing rules the harness enforces

## Directory map

```
pyhermes/
├── py.typed            ← PEP 561 marker, empty: without it a consumer's mypy types every
│                         symbol as Any. Deleting it, or a packaging change that drops it,
│                         fails `python -m qa.distribution` in CI's `wheel` job (#243)
├── config.py           ← the tunable numbers, in one frozen dataclass
├── builder/            ← the shared kit: everything every medium has
│   ├── __init__.py     — public API surface (re-exports everything below)
│   ├── engine.py       — TemplateEngine + BoundEngine (binds theme, size, font, medium;
│                         a ChoiceLoader searches the medium's overlay before the root)
│   ├── medium.py       — Medium + DEFAULT_MEDIUM: skeleton, slots, page, constraints
│   ├── document.py     — Document: metadata + sections + the three projections, and the
│                         walk that numbers exhibits and notes and fills a Contents (#171)
│   ├── apparatus.py    — anchors, slugs, footnote markers, reference parsing. `apparatus.md`
│   ├── email.py        — Email(Document) + EmailBuilder (fluent): the four-slot region set
│   ├── regions.py      — Region base + Banner/MinimalBanner, Footer
│                         (body = the section list, deliberately not a class)
│   ├── containers.py   — Container, FullWidth, TwoColumn, ThreeColumn (+ `highlight=` property),
│                         and Appendices, which letters its sections (#309)
│   ├── components.py   — Component, CardGroup, DataTable, ChartBlock, ImageBlock, TextBlock, NumberedList, AuthorBlock, ContactBlock, Contents
│                         (+ the Exhibit mixin, and the private Endnotes the document appends)
│   ├── surfaces.py     — Callout, Button, Divider: blocks that set content apart (#265)
│   ├── glance.py       — BarList, Sparkline, HeroStat: data at a glance, drawn without
│                         images (#318). `glance.md`
│   ├── organising.py   — FactList, Timeline + Event, TeaserList + Teaser: organising
│                         content (#329). `design-axes.md`
│   ├── research.py     — Reference + Bibliography, Term + Glossary: a note's sources and
│                         terms, resolved by the document's walk (#220). `apparatus.md`
│   ├── models.py       — EmailMetadata (the email's facts), Card, KpiItem, TableRow, NumberedItem, Footnote, SectionConfig
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
│   ├── prose.py        — the `prose` filter: theme styles on the eight tags a raw-HTML
│                         prose field may carry, and the h1/h2 refusal (#280)
│   ├── formats.py      — finance formatters (#177): number, pct, bps, delta, money,
│                         compact; stdlib only, half-up, ASCII. `data-layer.md`
│   ├── exceptions.py   — EmailBuilderError hierarchy
│   └── templates/      ← packaged with the wheel (moved here in #10)
│       ├── base.html                — the EMAIL skeleton (four slots: header_bar_html,
│                                      banner_html, sections_html, footer_html)
│       ├── document/base.html       — the PAGED skeleton (@page, six slots, the break
│                                      rules and the apparatus's print-engine CSS), reached
│                                      by the document medium's template overlay
│       ├── document/page.html       — the sheet-boundary wrapper (a `tr`, not a `div`)
│       ├── document/regions/*.html  — cover.html, contents.html, back-matter.html, and
│                                      running-box.html which emits CSS rather than markup
│       ├── common/*.html            — disclosure, notes (the footnote macro), endnotes,
│                                      contents-list: partials several templates share
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
│                         related nested), inside multipart/mixed with Attachments (#197) and
│                         the attachment size budget (#198); to_wire_bytes(); save_eml()
│   ├── retry.py        — retry_with_backoff(): shared policy, per-adapter classification
│   └── exceptions.py   — DeliveryError / MessageError / TransportError (siblings of
│                          EmailBuilderError)
├── email/              ← the email medium: the Gmail size constraint, the four slots
├── document/           ← the paged medium
│   ├── medium.py       — PAGED_MEDIUM, paged_medium(page)
│   ├── document.py     — PagedDocument: cover | running boxes | body | back matter
│   ├── page.py         — Page: a sheet boundary that FLATTENS in a non-paged medium
│   └── regions.py      — Cover, ContentsPage, ExhibitsPage, RunningHeader/Footer (@page
│                         margin boxes), BackMatter, plus an Empty variant of each
├── brochure/           ← the folded medium (#172): one sheet, panels, both sides
│   ├── fold.py         — FoldFormat, FoldKind, four presets; the tuck is a distance
│   ├── panel.py        — Panel (flattens elsewhere) and PanelBox, where one sits
│   ├── imposition.py   — reader order → (side, position), one table per fold
│   ├── document.py     — Brochure: panels in reader order, two sides, proof()
│   ├── checks.py       — safe area and print resolution, at construction
│   └── fit.py          — overflowing_panels(): the print engine says what clipped
├── gmail/              ← Gmail send adapter (consumes delivery; owns no credentials)
│   └── sender.py       — GmailTransport protocol, GoogleApiTransport shim, send_message()
├── outlook/            ← Outlook send adapter over Microsoft Graph (same shape as gmail)
│   ├── sender.py       — OutlookTransport protocol, GraphApiTransport shim, send_message()
│   └── desktop.py      — create_draft(): classic Outlook's drafts through COM (#279)
├── check/              ← the portability check, shipped (#278): lint.py, target.py, and
│                         `python -m pyhermes.check path.py:callable`
├── data/               ← the data adapters (#179, #180); "[data]" and "[charts]" extras
│   ├── frames.py       — table_from_frame: a DataFrame as a DataTable
│   ├── charts.py       — image_from_figure / chart_from_figure: a Figure as an image
│   └── exceptions.py   — DataError, BackendMissingError (a sibling of EmailBuilderError)
├── math/               ← the equation renderer (#221); "[math]" extra. `math.md`
│   ├── render.py       — render_math: LaTeX → PNG through mathtext, lazily imported
│   ├── adapter.py      — math_block / image_from_math: painted for a theme and a density
│   └── exceptions.py   — MathError, BackendMissingError, MathSyntaxError
├── pdf/                ← the PDF exporter, on the adapters' contract; "[pdf]" extra
│   ├── exporter.py     — render_pdf / save_pdf / layout / page_count / available; lazy backend
│   ├── profile.py      — PdfProfile, PRINT (render_pdf's default) and SCREEN (#196). `digital-pdf.md`
│   ├── attachment.py   — pdf_attachment(): a document as an application/pdf Attachment (#197)
│   ├── fetcher.py      — serves cid: from the manifest, refuses every other URL
│   └── exceptions.py   — PdfError, a sibling of EmailBuilderError and DeliveryError
qa/                     ← QA harness (epic #54); NOT shipped in the wheel
├── goldens.py         — the golden snapshot harness: check_fixture(), write_fixture(),
│                        render_manifest(), and the diagnosable mismatch report
├── screenshots.py     — headless-Chromium runner: `python -m qa.screenshots`, cid→data URI
│                        substitution, run.json recording the browser build
├── lint.py            — re-exports pyhermes.check.lint, where the rules ship since #278
├── outlook_desktop_check.py — the human check for #279, run on Windows
├── preview.py         — the CLI that composes the rest: `python -m qa.preview <target>`
│                        [--lint] [--screenshot] [--open] [--list]
├── distribution.py    — checks the built wheel (and sdist) a consumer installs, not the
│                        tree: `python -m qa.distribution dist/` (#237)
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
   introspects every public `Component` subclass exported from `pyhermes.builder` and fails when
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

Moved out of `pyhermes/__init__.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
pyHermes Service Layer
======================

pyhermes/
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

    from pyhermes.builder import CardGroup, EmailBuilder, FullWidth
    from pyhermes.builder.models import Card, KpiItem
    from pyhermes.delivery import build_message, save_eml
    from pyhermes.gmail import GoogleApiTransport, send_message
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

12. **A spacing override names a token its object reads; a pixel in a template is still a
   bug.** Added by epic #209. Every container and component declares `SPACING_TOKENS`, and
   `Spacing` refuses a name outside it at construction, so moving a token the template never
   reads cannot be a silent no-op. The teeth are two sentinel tests in `tests/test_spacing.py`:
   one sets each declared token to a sentinel and finds it in the markup, the other perturbs
   every undeclared token at document level and asserts the markup does not move. A wrong
   declaration fails both. Rule 5 is untouched: the override is a derive of the bound scheme,
   so every template still reads `size.*`.

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

## The package a consumer installs (#237)

Nine epics of rendering work had never shaped the package for the person who runs
`pip install`. The checks read the **built artefacts**, never the tree, because every
earlier check passed on a tree that would have shipped wrong.

- **`py.typed` ships in the wheel (#243).** Without it a consumer's mypy reported "missing
  library stubs or py.typed marker" and typed every symbol as `Any`, so no construction-time
  contract was visible at a call site. CI type-checks a two-line consumer with `--strict`
  against the installed wheel; deleting the marker from that install turns it into the
  missing-stubs error and a revealed `Any`, measured.
- **The sdist is the library alone (#244).** Hatchling's default sdist takes every file git
  does not ignore, which here is 2.2 MB of `.claude/`, 4.8 MB of `tests/` and its goldens, and
  `qa/`, `examples/`, `drafts/`, `docs/`. `only-include` names four roots, and
  `qa/distribution.py` fails CI on any other. Two entries it allows are hatchling's own:
  `PKG-INFO`, and a `.gitignore` it adds whatever `exclude` says (tried). Widening
  `only-include` to `qa` and `tests` was checked to fail it.
- **The metadata is honest (#244).** The licence is MIT, chosen by the owner, as an SPDX
  `license` expression (PEP 639) with `license-files`, and **no licence classifier**, which
  the expression supersedes. `twine check --strict` runs on both artefacts. A `Homepage` URL
  label is what `pip show` prints as the home page; pip 24.0 printed no
  `License-Expression` where 26.2 does, so CI upgrades pip before `pip show --verbose`.
- **Both artefacts render the same email**, each installed into its own venv with no source
  tree, from one smoke script run in a loop.
- **CI runs every Python the metadata admits (#245):** `check` on 3.11, 3.12, 3.13 and 3.14,
  and `data` (the cheapest extras job) on 3.11 as well as 3.13, so the pandas, matplotlib and
  numpy pins are proven on the floor. Before this the comment said "the current release" of a
  matrix that stopped at 3.13. Run here before the change: all four pass `check` (3.14 as
  3.14.0rc2), and `[data,charts,math]` installs and passes on 3.11. A red Python is a finding
  to fix, or to file with `requires-python` capped, never a reason to narrow the list.
- **The import root is `pyhermes`, decided in #248.** The distribution was `pyhermes` and
  the import was `svc`, a generic top-level name: two wheels that ship a top-level `svc/`
  overwrite each other's files in site-packages, `pip check` sees nothing, and a reader
  had to learn the import from the README. The cost was one PR of mechanical rewrite, 1,349
  references in 187 files, with the wheel and sdist checks above proving it shipped whole.
  Kept on the other side: the session logs, which record what was true when written.
- **`svc` was a shim, and #255 removed it before any release shipped it.** #248 kept
  `svc/__init__.py` for one release: it warned once with a `DeprecationWarning` and put a
  meta-path finder in front that resolved `svc.X` to the module `pyhermes.X` already is.
  Its one trap is worth keeping for the next alias: the import system overwrites an aliased
  module's `__spec__` with the alias's, which is no package, and `importlib.resources` then
  refused the templates, so the loader put the real spec back. The package was never
  published, so no installer saw the warning, and the owner removed the shim at once (#255)
  rather than carry the collision risk a release it protected no one in. Now
  `qa/distribution.py` fails CI on any top-level package in the wheel beside `pyhermes`, the
  wheel job asserts `import svc` fails from each artefact, and a test in
  `test_distribution.py` fails if anything in the repo imports `svc`.
