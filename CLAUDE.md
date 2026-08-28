# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this project is

pyHermes builds **HTML emails for academic / financial newsletters**. Python composes
Jinja2 templates into a single, inline-CSS HTML document engineered to survive email
clients (Gmail, Outlook) — the hard part is staying under Gmail's clipping limit while
keeping the layout table-based and portable.

**Scope today = build *and* send.** Composing the HTML is still the bulk of the product,
but the chain is complete: `svc/builder/` renders the HTML, projects the `text/plain` part and
declares the images; `svc/delivery/` assembles the `multipart/alternative`; `svc/gmail/` +
`svc/outlook/` transmit it. Adapters own their
provider's wire contract and **never** authentication, so pyHermes still depends on nothing
but Jinja2.

## Commands

```bash
pip install -e ".[dev]"       # editable install + pytest/ruff/mypy (see Gotchas)
pytest                        # unit suite — validation, error paths, size limits
ruff check . && ruff format --check .
mypy                          # config in pyproject: files = ["svc", "qa"]

pip install -e ".[qa]"        # optional: adds Playwright for screenshots (#59)
python -m qa.screenshots      # gallery → output/screenshots/ (gitignored)
pytest --update-goldens       # the ONLY way to regenerate a golden (#58)
python -m qa.preview kitchen_sink --lint    # build + save + lint one email (#61)
```

CI runs the first four on every PR, plus a `screenshots` job and the `wheel` job
([.github/workflows/ci.yml](.github/workflows/ci.yml)). `[dev]` alone must stay browser-free:
the screenshot tests skip rather than fail, and that is what proves `[qa]` is optional.

**To eyeball a change, run `preview`** — it is the loop, and it replaced the hand-rolled one
these docs used to prescribe:

```bash
python -m qa.preview kitchen_sink --lint --screenshot --open
python -m qa.preview drafts/weekly.py:build --lint      # your own draft, same command
```

Four things now stand behind that one command, and they answer different questions:

| | Answers |
|---|---|
| **The gallery** (`qa/fixtures/`) | *What do I render?* Four canonical emails, deterministic by rule, so every tool below has stable input |
| **The goldens** (`qa/fixtures/goldens/`) | *Did anything move?* Byte-identity on HTML **and** the asset manifest, for the whole gallery |
| **Screenshots** (`qa/screenshots.py`) | *How does it look?* Two viewports through headless Chromium — a review artifact, not a gate |
| **The lint pass** (`qa/lint.py`) | *Will it survive a real client?* The portability rules, with the size budget attributed to sections |

The `tests/` pytest suite remains the automated safety net, and it now carries the harness:
the goldens fail on any drift, and every fixture is linted on every run.

Slash commands (from the `.claude/` library): `/version-set`, `/version-ship`, `/reindex`.

## Directory map

```
svc/
├── config.py           ← the tunable numbers, in one frozen dataclass
├── builder/            ← current OO email builder (use this for new work)
│   ├── __init__.py     — public API surface (re-exports everything below)
│   ├── engine.py       — TemplateEngine + BoundEngine (per-render theme + size binding)
│   ├── email.py        — Email + EmailBuilder (fluent), _validate_size()
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
│   ├── exceptions.py   — EmailBuilderError hierarchy
│   └── templates/      ← packaged with the wheel (moved here in #10)
│       ├── base.html                — the rendered skeleton (four slots: header_bar_html,
│                                      banner_html, sections_html, footer_html)
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
├── gmail/              ← Gmail send adapter (consumes delivery; owns no credentials)
│   └── sender.py       — GmailTransport protocol, GoogleApiTransport shim, send_message()
├── outlook/            ← Outlook send adapter over Microsoft Graph (same shape as gmail)
│   └── sender.py       — OutlookTransport protocol, GraphApiTransport shim, send_message()
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

## The fixture gallery — `qa/fixtures`

The shared set of representative emails every later QA tool consumes (#57, the first step of
epic #54). Twelve fixtures, each a `build()` returning a built `Email`, enumerated through
`all_fixtures()` so a consumer never imports them one by one:

| Fixture | What it is for |
|---|---|
| `minimal` | The smallest valid email. Its value is negative space — it renders the skeleton with every optional region empty, so it catches a change to `base.html`'s defaults that a richer fixture masks by supplying the value itself |
| `kitchen_sink` | Every public component in every container ratio, `highlight=True` included, **and every `EmailMetadata`, `Banner` and `Footer` field set to a distinctive non-default value**. The fixture the golden is worth the most on, and #32's characterization email |
| `image_matrix` | All three embed strategies, plus the same attached image referenced twice — the shortest proof that `assets()` reports exactly the `cid:` references the HTML contains |
| `minimal_banner` | The `MinimalBanner` variant (#36, renamed in #90). Differs from the others in one argument, so its golden pins that a region swap changes the masthead and nothing else — no VML, no `background-image`, every email-level fact still present, and a CID logo attached exactly once through the region's own `images()` |
| `slate_theme` | The `slate` preset (#50). Differs from `kitchen_sink` in one metadata field, so its golden pins that a palette reaches *everywhere* — every component, every ratio, the dark-mode forcing block and the mobile media query — and that a caller's own `KpiItem` colour survives while an unset `Card.color` takes the theme's neutral |
| `compact_size` / `spacious_size` | The two density presets (#43). Each renders **`kitchen_sink`'s own content** at one non-default `size_theme` rather than restating it, so the pair diffs as a true A/B where every difference is the density: type, spacing, the component sizes that do not follow the global scale, the frame padding every column width is computed from, and `base.html`'s `@media` block moving with the rest. They are what retires `kitchen_sink`'s `size_theme` exemption — that fixture holds the field at its default on purpose, because it is the epic's byte-identity reference |
| `custom_banner` | Every banner axis at once (#94), which is what closes epic #88 — free-form `title`/`subtitle`, a `department`, an **attached** background image and a `BannerPalette` tuned to it. The one fixture a *cross-axis* regression shows up in, since no per-axis test can see an interaction. It also covers the only embed path the gallery otherwise lacked: a `cid:` background, reaching the manifest through `Banner.images()`' walk of `IMAGE_FIELDS` and appearing in both the CSS `background-image` and the VML `v:fill`. Its body is short on purpose — `kitchen_sink` exercises the component library, and a fat body here would make this golden noisy for reasons unrelated to the masthead |
| `no_header` | The `EmptyHeader` variant (#96) — a region that fills **no** slot, so the strip is genuinely absent rather than blank. Differs from `minimal` in one argument, and pairs the **default** banner on purpose (`minimal_footer`'s reasoning: two region choices swapped at once could not say which moved a byte). Its `header_disclaimer` is *set*, which is the point — an empty one would leave the strip absent either way, and the golden could not tell "the variant omitted it" from "there was nothing to render" |
| `custom_footer` | Both footer axes at once (#101), closing epic #98 — the coloured box surface (`align`, `background_color`, `text_color`) and a custom `LinkRow` with a link set that is neither the default pair nor the same length. Paired with the **default header** on purpose, so the two boxes are independent in the diff and their contrast is visible in a screenshot; it also carries the only `mailto:` link in the gallery, since a scheme check must keep passing what it allows and not only reject what it does not |
| `modern_fonts` | The `modern` preset (#107), the third axis's A/B. Renders **`kitchen_sink`'s own content** at one non-default `font_theme`, the `compact_size` shape exactly. It is the first artifact that can show `heading` and `body` are separate **roles**: they share a stack in the default, so until a preset moved one and held the other, nothing could tell them apart. It also pins that the `[if mso]` fallback moves with the rest — a literal there would leave an email custom-faced in Gmail and Georgia in Outlook, the half-themed failure in the client hardest to check. Its diff against `kitchen_sink` is *only* `font-family` values, and a test asserts that by stripping them and comparing the rest byte for byte |
| `minimal_footer` | A minimal-footer build (#66), the same argument at the other end. Paired with the **default** header on purpose: the two region choices are independent, and swapping both at once could not say which one moved a byte |

**Determinism is the rule the gallery rests on**, and it is not a style preference: Content-IDs
are `sha256(bytes)[:16]`, so a fixture image that varies changes the `cid:` references in the
HTML and fails every downstream golden for a reason unrelated to the change under review.
Hence fixed strings, no clock, no `random`, and PNG bytes generated from constants by
[qa/fixtures/_png.py](qa/fixtures/_png.py) rather than checked in as binaries.

**`qa/` is a top-level package, not `svc/qa` and not `tests/fixtures`** — the decision #57 left
to its PR. It is out of `svc/` because the wheel ships `packages = ["svc"]` and the gallery is
test data that would be dead weight for every installing user; it is out of `tests/` because
`tests/` is not importable from an installed position and the epic's later tools (#59
screenshots, #60 lint, #61 the `preview` CLI) are not tests. A root
[conftest.py](conftest.py) puts the repo root on `sys.path` so `import qa` does not depend on
hatchling's editable-install strategy happening to expose it. `qa/` **is** type-checked —
`mypy` runs over `["svc", "qa"]`.

**Adding a component means adding it to `kitchen_sink()`; so does adding an `EmailMetadata`,
`Banner` or `Footer` field.** Four completeness tests introspect rather than hand-list: one
over every public `Component` subclass exported from `svc.builder`, one over
`dataclasses.fields(EmailMetadata)`, a third asserting each metadata value *differs from its
own default*, and a fourth doing both at once over each **region** — parametrized across
header and footer, and read off the *built* region, so it holds however the fixture chooses
to supply it. A field set to its
default is one the golden cannot pin, because the render would not move if the default changed
underneath it. Only exemptions are named, in `DEPRECATED_COMPONENTS` (today: `KpiStrip`, whose
markup duplicates a section already in the gallery and which warns on construction), plus
`EmailMetadata.banner` and `EmailMetadata.footer` themselves — `kitchen_sink` builds both
regions **explicitly**, so their own fields are pinned by the per-region test rather than by
the metadata one — plus `ANCHORED_TO_THE_DEFAULT`, today `size_theme` and `font_theme`. Those
two are the one case where holding the default is the *point*: this fixture is what every
migration's byte-identity claim is measured against, so its density and its faces have to be
the ones the claim is about. Their non-default paths are pinned by `compact_size` /
`spacious_size` and `modern_fonts`, which render this same email one field apart. The flat, pre-split banner keywords used to be pinned by this fixture's
golden and are no longer: #91 gave the banner two fields with no flat spelling (the keywords
exist for a pre-split call site, and a field added after the split has none), so the coverage
moved to `TestTheFlatKeywordsStillWork` — where it is *stronger*, because a golden pins each
spelling's own bytes and would not notice the two diverging, while the test asserts they
**converge**.

Each `build()` also takes an optional `template_dir`, threaded to `EmailBuilder`, so the whole
gallery can be rendered against a *candidate* template set — which is the question a template
migration actually asks ("does this edit move any email?"), and how the golden harness's
detection test perturbs a real template instead of only the compared text. It stays out of the
`FixtureBuilder` alias deliberately: consumers must be able to call a builder with no arguments.

## Golden snapshots — `qa/goldens.py` + `qa/fixtures/goldens/`

The byte-identity bar the migration epics (#33, #41, #42, #49) all promise to hold, made
mechanical (#58). Three artifacts per fixture, because a render, its attachments and its
plain-text projection all drift independently:

| File | What it pins |
|---|---|
| `goldens/<name>.html` | The rendered HTML, byte for byte, no normalization |
| `goldens/<name>.assets.txt` | One tab-separated record per `ImageAsset`, **in manifest order** — content-id, MIME type, byte length, filename |
| `goldens/<name>.txt` | The plain-text projection (#110), byte for byte |

**What is pinned lives in one list.** `artifacts(name, email)` returns the `(label, path,
content)` triples, and `check_fixture()` and `write_fixture()` both walk it — so a fourth
artifact cannot end up checked but never written, or written but never checked.

Five decisions worth not re-litigating:

- **The manifest stores no image bytes.** They already live in the fixture that generates them,
  and a Content-ID is `sha256(bytes)[:16]` — different bytes cannot keep the same id, so id plus
  length catches everything a second copy would, at none of the repo weight.
- **Order is preserved, not sorted.** The header epic moves image aggregation between classes;
  a reordered `assets()` is a real change, and #32 asked for it to fail. A dropped or duplicated
  asset can also happen with the HTML *byte-identical*, which is why this artifact is separate.
- **Regeneration is opt-in and reviewed**: `pytest --update-goldens` is the only path (registered
  in the root [conftest.py](conftest.py), because pytest reads `pytest_addoption` only from the
  rootdir conftest). Nothing regenerates implicitly, and **a missing golden fails rather than
  being created** — one that writes itself on first run pins whatever happened to be true that
  day. *A golden diff in a PR is a claim that the visual change is intended*, and it is reviewed
  as one.
- **The text golden is a third file, not a section of the first.** Since #109 the text part
  is a *second projection of the section tree* rather than a degradation of the render, so a
  component's `text()` can change with the HTML byte-identical and vice versa — neither golden
  can see the other's drift. A test perturbs a component's projection and asserts only the
  `.txt` artifact moves; another perturbs a *fact* and asserts **both** do, which is the
  stronger claim, since a fact the email owns must reach both parts or they have come to
  disagree about what the email says.
- **A mismatch must be diagnosable.** "Bytes differ" on a 47 KB document costs the next reader an
  hour, so the report names the fixture, the artifact, the line, the byte offset, three lines of
  context and both versions of the line that moved. That the harness *bites* is tested by
  perturbing a real template and a real fixture and asserting the reported location, not assumed.

`qa/goldens.py` imports no pytest, so #61's `preview` CLI can check goldens without pulling in a
test framework.

**#32 is satisfied here, not separately.** #58 required that the two resolve to one harness;
#32 had not started, so `kitchen_sink` became the representative email it specified — exhaustive
over `EmailMetadata`, every container ratio, a hosted logo and an attached image. Do not add a
second `tests/test_golden_render.py`.

## Screenshots — `qa/screenshots.py`

Renders the gallery through headless Chromium at two viewports (#59), so a visual change is
reviewable without checking out the branch. `python -m qa.screenshots [fixture ...]` writes
PNGs plus a `run.json` into `output/screenshots/` (gitignored).

**The decision that shapes everything else: these are *checks*, not artifacts.** Nobody
diffs them, nothing commits them, and no test compares them to a stored copy. That is why
the browser build is **recorded rather than pinned** — buying cross-machine reproducibility
with a pinned container image costs more than the guarantee is worth for an image a human
glances at. What *is* pinned is what makes two runs on one machine comparable: viewport
sizes, `device_scale_factor=1`, full-page capture. `run.json` carries the Chromium build,
the Playwright version, the platform and the resolved executable — so if pixel-diff gating
is ever wanted (an explicit non-goal of #54's first cut), that recording is what says
whether two sets are even comparable, and pinning becomes a deliberate act rather than one
inherited by accident.

- **`cid:` is rewritten to a data URI for the screenshot only.** A browser has no MIME
  message, so every attached image would otherwise be a broken-image icon and the screenshot
  could not do its one job. The bytes come from `Email.assets()`, so the substitution is
  exact. `render()` and the goldens are untouched, and a test asserts that separation.
  Only `src` attributes are rewritten, never bare text — `image_matrix` titles a section
  "Attached (cid:)", and substituting on the substring would corrupt copy.
- **External requests are blocked**, so a run never waits on DNS for `example.com` and the
  render shows what a reader with images off sees — which is Outlook's default state.
- **The filenames say `chromium-desktop` / `chromium-mobile`, not `gmail` / `outlook`.**
  Chromium approximates Gmail in a browser and says nothing about Outlook's Word engine.
  Client compatibility belongs to the lint pass (#60), not to these images.
- **Playwright is the optional `[qa]` extra.** `pip install -e ".[dev]"` + `pytest` must
  stay browser-free — that is what proves the extra is genuinely optional, so the capture
  tests *skip* rather than fail, and CI's `screenshots` job is the only place they run.
  `PYHERMES_CHROMIUM` points the runner at a browser the environment supplies instead of one
  Playwright manages (read at use time, never at import).

## Lint pass — `qa/lint.py`

The portability rules the repo *documented* but only enforced where someone remembered a
test (#60). `lint_html(html)` returns `Finding(rule_id, severity, location, message)`;
`lint_email(email)` is the convenience wrapper. The suite lints every gallery fixture, and
#61's `preview` CLI reuses the same entry point on arbitrary HTML.

| Rule | Severity | What it catches |
|---|---|---|
| `img-width-attr` | error | An `<img>` with no integer `width=`. Outlook's Word engine ignores CSS `max-width`, so the display width must be an attribute |
| `img-alt` | error | Missing or blank `alt` — all a reader gets when images are blocked, which is Outlook desktop's default |
| `no-external-css` | error | `<link rel=stylesheet>` or `@import`, including inside an mso conditional |
| `outlook-unsupported-css` | error | `display:flex/grid`, `position:absolute/fixed` in an inline style |
| `outlook-line-height` | error | A **unitless** `line-height`; Outlook Classic ignores it. `0` is allowed |
| `outlook-transparent-background` | error | `background-color` carrying an alpha channel — Outlook demotes it to a background image |
| `empty-url` | error | `url()` with nothing in it; a client may resolve it against the message body |
| `table-role` | error | A layout table with no `role`, **and** a data table carrying one (#114) |
| `size-budget` | warn/error | The 90/102 KB thresholds, **attributing the bytes to section-marker regions** |

Seven decisions worth not re-litigating:

- **`table-role` fires in both directions, and that is what makes it a rule rather than a
  chore.** A check that only demanded `role="presentation"` would be satisfied by marking
  *every* table — which strips the semantics from the one table a screen reader should
  actually navigate. So an unmarked layout table is an error and a marked *data* table is an
  error, and `th` is the discriminator: it distinguishes the two kinds in this codebase
  exactly, and it is the same signal a reader uses. The check runs at the **closing** tag,
  because that is when the verdict is known, but reports the opening one, because that is
  where a reader has to go. The open tables are a stack: the gallery's one real data table
  renders inside two layout tables, and a flat flag would mark all three as data.
- **It parses, it never greps.** The repo learned this the expensive way — a `grep` for
  `Contact Us` matched inside a section-marker comment and produced a confident, wrong
  answer. `html.parser.HTMLParser` is stdlib, so the check costs no dependency.
- **Every rule carries its source**, in `SOURCES`, and a test asserts every rule that can
  fire has one. A rule asserting something about a mail client that nobody can trace is a
  preference wearing a rule's clothes. Most citations are Microsoft's own Outlook Classic
  troubleshooting document; the two image rules cite the repo's own established decisions.
- **`max-width` is deliberately NOT denied.** The templates pair it with a `width=`
  attribute on purpose, so a blanket rule would fire on correct code — and a noisy rule gets
  switched off, which is worse than no rule. `img-width-attr` covers what actually matters.
- **`DEFERRED_RULES` is a recorded decision, not an oversight — and it is now empty.** #60
  shipped green by *filing* the three findings the templates violated rather than arriving
  red, because a linter that arrives red teaches everyone to ignore it. All three were #78
  and all three are fixed, so all three rules moved into `SOURCES`. The mechanism stays for
  the next such finding, which belongs there rather than shipped red or quietly dropped. Two
  tests hold the shape: nothing may sit in both places, and the three rules #78 unblocked
  must be *shipping* rather than merely gone.
- **An Outlook rule does not fire on markup Outlook cannot see.** `<!--[if !mso]><!-->` is
  *downlevel-revealed* — the comment ends immediately, so what follows is real HTML to any
  parser, correctly, since every client but Outlook renders it. The rules in
  `_OUTLOOK_ONLY_RULES` are suppressed between such a conditional and its `<![endif]`. The
  set is **named, not matched on the `outlook-` prefix**: `img-width-attr` is motivated by
  Outlook too and deliberately keeps firing there, because a width attribute is good practice
  in every client. This is what lets the masthead scrim satisfy
  `outlook-transparent-background` by being hidden from Outlook rather than made opaque —
  which would have painted over the very photograph it exists to darken.
- **`size-budget` extends `_validate_size`, it does not reshape it.** That method is a
  `@staticmethod` on purpose and its messages are asserted by existing tests. The linter adds
  the part `render()` never had: *which region* spent the budget. Regions run marker to
  marker, and a marker must contain a letter — the templates also use `<!-- ══════ -->` as
  decorative rules, and counting those made the heaviest "region" a row of box-drawing
  characters, a breakdown that names nothing.

**Markup inside `<!--[if mso]>` is not linted** as standard HTML. `HTMLParser` hands a
conditional comment over as text rather than tags, which is the behaviour wanted: the block
carries Outlook-only VML, so judging it by standard-HTML rules would fire on markup that is
correct *because* it is non-standard. `no-external-css` still reads comment text, since an
`@import` hidden in a conditional is just as external.

## The preview CLI — `qa/preview.py`

One entry point for the loop the docs used to prescribe by hand (#61):

```bash
python -m qa.preview --list
python -m qa.preview kitchen_sink --lint --screenshot
python -m qa.preview drafts/weekly.py:build --lint --open
```

It writes **both** projections — `output/<name>.html` and `output/<name>.txt` (#110). An email
has two readable parts, and writing only the HTML would leave out the half no screenshot and no
lint rule can show you.

**It composes; it never reimplements.** Fixtures come from `all_fixtures()`, findings from
`lint_html()`, images from `capture_emails()`. Tests assert the HTML it writes equals
`Email.render()` byte for byte **and** the text equals `Email.text()`, because the one thing
that would make this tool worse than useless is being a second rendering path — and since
#109 there are two projections it could be a second path for.

That rule earned its keep immediately: `capture_gallery()` could only screenshot names in the
registry, and **a user's draft never is one** — so `qa/screenshots.py` gained
`capture_emails(mapping)`, keyed by email rather than by fixture name, and `capture_gallery`
became a thin wrapper resolving names through the registry. The gap was fixed in the module
that owned it rather than routed around in the CLI.

Four decisions:

- **Two target forms, told apart by the `:`** — a bare name is a gallery fixture; a
  `path/to/module.py:callable` is any zero-argument callable returning an `Email` *or* an
  `EmailBuilder`. Both are public API, so a caller should not have to remember which their own
  function returns. Split on the **last** colon, so a Windows drive letter is not mistaken for
  the separator. The output name is `{module_stem}-{callable}`, so two files both defining
  `build()` do not collide in `output/`.
- **Exit codes are the interface**: `0` clean, `1` lint errors, `2` unbuildable or
  unresolvable. Warnings alone do not fail. That is what lets it run in a hook rather than be
  read by a human every time.
- **A missing browser is a skip, not a failure.** `[qa]` is optional by design, so
  `--screenshot` reports and carries on — and a test asserts that skip does *not* mask a lint
  error, since the two flags are independent.
- **A builder error prints its own message and exits 2** — no traceback wall for what is
  nearly always a data mistake. `EmailBuilderError` raised while *importing* a target module
  propagates as itself rather than being flattened into "failed to import": the builder names
  the field, and that is the useful message.

**No console script**, deliberately. #57 put `qa/` outside the wheel because the gallery is
test data; an installed `preview` entry point would contradict that, so the module form is the
interface. This is the placement decision #61 said to inherit.

## Configuration — `svc/config`

Every judgment-call number in the package is a field on one frozen
[Config](svc/config.py) dataclass, so a caller can retune it without editing the library.

```python
from svc.config import Config, get_config, set_config, config_override

get_config().inline_image_limit_kb              # what is actually in force
set_config(Config(inline_image_limit_kb=64))    # install process-wide
set_config(Config.from_env())                   # or read PYHERMES_*
with config_override(retry_max_attempts=1):     # scoped, restores on exit (tests)
    ...
```

**The line the module draws — and the reason it exists — is between a judgment call and a
fact about the world.** The inline-image cap, the retry ladder, the request timeout and the
error-excerpt length were all *picked by someone*; a picked number that cannot be revisited
without editing the library is a bad default wearing a constant's clothes. Graph's
`ACCEPTED = 202`, the transient status families, and the Content-ID character set describe
what a provider *does* — changing them does not tune behaviour, it makes the code wrong
about its environment, so they stay literals in the modules that own them.

`size_limit_kb` sits across that line deliberately: 102 KB is a real Gmail limit, not taste,
but an email bound for a non-Gmail channel is legitimately not subject to it. It is
configurable *and* documented as a fact, so raising it stays a conscious act.

Rules the module holds to, each for a specific reason:

- **Nothing reads the environment on import.** `from_env()` is explicit, because a library
  whose behaviour changes with ambient state is one you cannot reason about locally — and
  `svc/delivery`'s purity, which the byte-for-byte dry run depends on, would be the first
  casualty.
- **Consumers call `get_config()` at use time, never at import time.** An override installed
  after import must still be seen. Where a module keeps a public constant
  (`INLINE_LIMIT_KB`, `DEFAULT_TIMEOUT_SECONDS`, `_SIZE_LIMIT_KB`) it is the *shipped
  default*, mirrored from `Config()`; the enforced value comes from the active config.
- **An explicit argument always beats the config.** `retry_with_backoff()`'s numeric
  parameters default to `None`, meaning "ask the config" — passing one still wins, which is
  what the adapters and their tests rely on.
- **Validated at construction, like every model here** — including the cross-field rules
  (`size_warn_kb <= size_limit_kb`, `inline_image_limit_kb <= size_limit_kb`, a backoff
  factor of at least 1). These raise plain `ValueError`, **not** `EmailBuilderError` or
  `DeliveryError`: a bad limit is a programming error in setup, not rejected email data.
- **`None` means no timeout**, so it cannot double as "unspecified" —
  `GraphApiTransport(timeout=...)` uses a private sentinel for the latter.

**Adding a tunable**: add the field (with today's literal as its default, so nothing
re-renders or re-retries differently), validate it in `__post_init__`, read it via
`get_config()` at the use site, and add a case to `TestTheWiringIsLive` in
[tests/test_config.py](tests/test_config.py) — that class exists to prove each knob is
actually *reached*, because a config nobody reads is decoration.

## Architecture — `svc/builder`

`svc/builder/` is the only implementation. Its public surface is re-exported from
[svc/builder/__init__.py](svc/builder/__init__.py).

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

1. **Skeleton** — [svc/builder/templates/base.html](svc/builder/templates/base.html). The full HTML page (head,
   preheader, palette comment) with four variable holes: `{{ header_bar_html }}`,
   `{{ banner_html }}`,
   `{{ sections_html }}`, and `{{ footer_html }}`.
   Rendered last by [Email.render()](svc/builder/email.py).
2. **Regions** — the named areas of the email. Templates in
   [svc/builder/templates/regions/](svc/builder/templates/regions/); Python wrappers in
   [svc/builder/regions.py](svc/builder/regions.py), all sharing a `Region` base that owns
   validation, the image walk, the facts-over-presentation layering and `render_slots()`.
   Three region classes and two variants, per the table above. The **body region is
   the ordered section list** — deliberately not a class, since wrapping it would add a
   layer with no behaviour. The footer has no variant today; that is a gap, not a decision —
   `Footer.REQUIRED_SLOTS` means a variant may not drop the closing block, never that no
   variant may exist.
3. **Containers** — layout geometry only. In [svc/builder/templates/common/containers/](svc/builder/templates/common/containers/).
   Each produces a `<tr>` block sized to the 680px outer email table. Python wrappers in
   [svc/builder/containers.py](svc/builder/containers.py).
4. **Components** — content blocks. Templates in
   [svc/builder/templates/analysis/](svc/builder/templates/analysis/) and
   [svc/builder/templates/text/](svc/builder/templates/text/); Python wrappers in
   [svc/builder/components.py](svc/builder/components.py).

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
| `email_subject`, `preheader_text` | `Banner.background_image_url` |
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
cannot express.** The default copyright keeps the `&copy;` **entity** rather than a bare `©` —
this is an email library, and U+00A9 mis-decoded as latin-1 renders as a mojibake pair; a
caller's own line is plain text, escaped by the resolver, which is why the template reads one
already-HTML key instead of branching.

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
3. **Screenshots approximate Gmail-in-a-browser; the lint pass owns Outlook.** "The
   screenshot looks fine" never closes a compatibility question — Chromium renders
   `display:flex` perfectly and Outlook's Word engine does not. The filenames say `chromium`
   for exactly this reason. Conversely, a clean lint says nothing about whether the layout
   *reads* well; that is what the images are for.
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
9. **A new component must implement `text()`, and absence fails loudly.** The mirror of rule
   7 with the **opposite default**: an absent image list is empty, an absent projection is a
   `NotImplementedError` naming the class. A component with no visual content can exist — a
   spacer would — but a *content* component invisible to text-mode readers is the
   accessibility failure epic #53 exists to fix, so it fails the first email that projects it
   rather than vanishing from the text part silently. A completeness test rides `kitchen_sink`
   and needs no hand-list; a second holds that the projection routes through
   `_with_subtitle`, which is what a new component would forget.

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
from svc.builder.models import Card, KpiItem, TableRow, NumberedItem, EmailMetadata, \
    SectionConfig, LinkRow, FooterLink
from svc.builder.enums import TwoColumnRatio, ThreeColumnRatio, CardOrientation, \
    EmbedStrategy, ImageAlign, SizeTheme
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

Column ratios and card orientation are `StrEnum`s in [svc/builder/enums.py](svc/builder/enums.py):
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

[Card](svc/builder/models.py) is the unit: `label` (required), `value`, `color`,
`sublabel`, and an optional `body` for prose. Either `value` or `body` must be present.
`KpiItem` is a `Card` subclass that adds no fields but keeps the stricter rule — a KPI
always has a value. **`Card.body` is an HTML field**, so escaping untrusted text in it is
the caller's job, same as `TextBlock.content`.

[EmailBuilder](svc/builder/email.py) is a thin fluent wrapper: `metadata()` initializes the
underlying `Email`, `section()` appends a container, `build()`/`render()`/`save()` are
terminal. `metadata()` must be called before `section()` or you get a `RuntimeError`. The
non-fluent `Email` class works identically.

### Hard constraints baked into the engine

- **102 KB Gmail clipping limit** — [Email._validate_size()](svc/builder/email.py) raises
  `SizeError` above 102 KB and warns above 90 KB. The single most important runtime check;
  never disable it without confirming a non-Gmail channel. Both thresholds come from
  [Config](svc/config.py) at check time, so a non-Gmail channel can raise them deliberately
  rather than by commenting the check out.
- **Jinja2 `StrictUndefined`** — [TemplateEngine](svc/builder/engine.py) fails fast on a
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
    [escape_html()](svc/builder/filters.py) (`from svc.builder.filters import escape_html`).
    `header_disclaimer` is the one worth naming twice (#95): making the strip a first-class,
    obviously-reusable region makes it likelier someone passes untrusted text to it, and the
    contract was *kept* rather than tightened because escaping it now would break every caller
    passing markup. So `Header`'s docstring states it, and a test asserts the docstring still
    does — a region whose text is raw HTML is a footgun, and a warning that lives only in a
    commit message is how it stays one.
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
  [models._validate_color()](svc/builder/models.py) at construction time and by the
  `validate_hex_color` filter ([svc/builder/filters.py](svc/builder/filters.py)) in templates.
  `DataTable` cell colors come from the `TableRow.colors` list — index-aligned with `cells`.

### Images and the asset manifest

An image carries two independent facts: **where the bytes live** (a hosted URL, a file on
disk, bytes in memory) and **how they reach the reader**. `EmailImage`
([svc/builder/images.py](svc/builder/images.py)) owns both, via three factories:

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
(A component must also join `kitchen_sink()` — see the standing rules above, which a test
enforces.)

Rules the module enforces at construction, per the validation philosophy below:

- **Format is sniffed from magic bytes, not the file extension** — PNG, JPEG and GIF only.
  WebP and SVG are detected specifically so the rejection can say why (Outlook's Word engine
  renders neither, and SVG can carry script).
- **`alt` is required.** It is what the reader sees whenever images are blocked, which for
  Outlook desktop is the default state.
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
  same rule, bounded to one region. See *Theming* below.
- **Density is a parameter — but the atom is the whole `SizeScheme`, and only by name.**
  `EmailMetadata(size_theme="compact")` is the entire caller-facing sizing surface. See
  *Sizing* below.
- **The typeface is a parameter — but the atom is the whole `FontTheme`.**
  `EmailMetadata(font_theme="modern")`, or a `FontTheme` object, is the entire caller-facing
  typography surface. See *Typography* below.
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

All errors inherit from [EmailBuilderError](svc/builder/exceptions.py): `TemplateError`
(Jinja load/render), `ValidationError` (data shape), `SizeError` (102 KB limit). Catch the
base class for "anything the builder rejected" — that now holds without exception, including
inside a template render: the `validate_hex_color` / `default_color` filters raise
`ValidationError`, not a bare `ValueError` (#18). A filter's `ValidationError` propagates
out of the render as-is rather than being re-wrapped as `TemplateError`: it is a data
failure, not a template one.

The one deliberate exception is `EmailBuilder`'s `RuntimeError` for calling `section()` or
`build()` before `metadata()` — a programming error in the call sequence, not rejected
data.

### Theming — colour is one validated object

Colour was 18 hex values in 245 occurrences across all 20 template files, three `rgba()`
literals and three Python fallbacks, described by a palette *comment* in `base.html` that
nothing could read — and that had already drifted, naming a row-alt colour the data table
never used. Epic #46 replaced it with [svc/builder/theming.py](svc/builder/theming.py).

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

  Everything else renders on surfaces the theme owns and gets nothing — every component, and
  every region's structural chrome. What the rule protects survives in all three, which is why
  these are exceptions rather than breaches: a caller picks a validated, coherent **atom**
  (a whole `BannerPalette`, or a background *with* the type that has to be legible on it),
  never a lone colour at a call site.

  **The list being closed is the point.** "Now every region gets a palette" is the failure
  mode, not the roadmap; a fourth exception has to name a ground the caller supplies. The
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
[svc/builder/sizing.py](svc/builder/sizing.py).

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

### Typography — the face is one selected vocabulary

Faces were the last hardcoded axis. Colour became a resolved `Theme` in #46 and density a
resolved `SizeScheme` in #45, but `font-family` stacks stayed baked into the templates: 49
declarations of three stacks across 15 files, unnamed and unvariable, so a newsletter wanting
its own house face forked templates. Epic #56 replaced them with
[svc/builder/typography.py](svc/builder/typography.py).

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

### The plain-text projection — a second walk of the same tree

A production email is `multipart/alternative`: an HTML part and a `text/plain` part. Epic #53
built the second one, and the shape of it is the whole decision — the text part is a **second
projection of the section tree**, not a degradation of the render.

```python
html = email.render()      # the first projection
text = email.text()        # the second — header → banner → sections → footer
```

Generating text by stripping the rendered HTML is the obvious approach and it produces garbage
for exactly the components that matter most: a KPI strip becomes a column of orphaned numbers
and a data table loses the alignment that is the only reason to have one. So each class
projects itself, the same way each already renders itself and declares its own images. **A test
monkeypatches `TemplateEngine.render` to raise and projects every gallery fixture** — the claim
is asserted, not trusted.

- **Absence fails loudly** (standing rule 9) — the `images()` rule with the opposite default.
- **Generated, never hand-authored.** There is no `text_override`, and a test introspects every
  exported class to keep it that way: derived text cannot drift from the HTML's content.
- **Raw HTML degrades through one small parser.** The five blessed surfaces
  ([textgen.py](svc/builder/textgen.py)) reach text through `html_to_text()`, whose tag set is
  **closed** and says so in its docstring — the epic named it as the scope magnet.
- **Regions project their *resolved* state**, never raw fields: `resolved_title()`,
  `resolved_copyright_html()`, `resolved_links()`. An email that renames its masthead says the
  new name in both parts. Reading `title` directly would work for every email that sets one and
  print nothing for every email that does not.
- **A variant that fills no slot projects nothing**, checked once in `Region.text()` — the same
  rule `render_slots()` applies, so `EmptyHeader` omits the strip from both parts without
  anyone remembering to make it.
- **Chrome projects to nothing; content projects its alt text.** A logo, a masthead background
  and a footer sign-off mark are decoration. An `ImageBlock` or `ChartBlock` is the section's
  content, and `alt` is required at construction precisely so that projection is never empty.
- **The `&copy;` entity inverts, from one source.** The footer degrades
  `resolved_copyright_html()` back to text rather than branching, so the entity the HTML needs
  against latin-1 mojibake and the character the charset-declared MIME part needs come from one
  method that cannot drift.

**The formatting policy is decided once**, in [textgen.py](svc/builder/textgen.py)'s docstring
— 78 columns for prose, one blank line between blocks and two between sections, `=` under the
masthead and `-` under a section title, `format_link` inline and `link_line` in a list. The
alternative is a house format that drifts one projection at a time.

**Tables do not wrap, and that is the one place the policy yields.** Column widths come from
the widest cell; the first column is left-aligned and the rest right-aligned — not a guess
about the data, but the convention the HTML template already encodes with `loop.first`, read
off the same rule so the two projections cannot disagree about which column is the label. A
table wider than 78 columns overflows the line-width policy rather than corrupting the
alignment that is the only reason to render it.

**The three design axes do not reach the text part**, and a test asserts it: colour, density and
typeface are HTML concerns by construction, so one email projects identically under every
preset. That is what makes "one house format" a property rather than a coincidence — and it is
why this epic and #56 could have run in parallel, touching no surface in common.

## Architecture — `svc/delivery`

The builder **declares** a CID embed; delivery **performs** it. `Email.render()` gives the
HTML, `Email.text()` the plain-text projection and `Email.assets()` the manifest;
[build_message()](svc/delivery/message.py) turns those three into a sendable `EmailMessage`.

```python
from svc.delivery import build_message, save_eml

message = build_message(email, sender="research@example.com",
                        to=["reader@example.com"])   # subject defaults from the email
save_eml(message, "output/preview.eml")     # dry run — no transport, no credentials
```

- **Structure** — every message is a `multipart/alternative` since #111:

  ```
  multipart/alternative            (an email with no CID images)
  ├── text/plain
  └── text/html

  multipart/alternative            (an email with CID images)
  ├── text/plain
  └── multipart/related
      ├── text/html
      └── image/*  × N
  ```

  **Text first, HTML last** — RFC 2046 §5.1.4 orders an alternative by *increasing*
  preference. Getting it backwards is silent: every graphical client still shows the HTML,
  and only the readers who need the fallback see the wrong thing.

  **The seat was reserved, not discovered.** This file and the module docstring both said the
  HTML part would become half of an alternative and the related subtree would nest inside
  unchanged — which is exactly what happened, byte for byte, one level deeper.

  **The images relate to the HTML part, not to the alternative.** They are resources of the
  HTML specifically; relating them one level up would attach them to the text part too, which
  is how a text-only reader ends up with a paperclip for art they cannot see.

  **A message now carries at least one random MIME boundary, and two when it has CID
  images.** A snapshot comparison must normalise *every* one — code written against the old
  single-boundary shape normalises the first and still differs on the second, which fails for
  a reason that has nothing to do with what it is checking.
- **There is no HTML-only opt-out**, deliberately. The text part is derived and costs nothing,
  and a flag to suppress it would be a deliverability and accessibility regression a caller
  reaches for by accident.
- **The consumer adds the decorations.** `ImageAsset.content_id` is bare, so assembly emits
  `Content-ID: <id>` — Python's `add_related()` stores whatever it is given, and a bare id is
  an RFC-invalid header. It also passes `disposition="inline"` explicitly, because supplying
  a `filename` alone yields `attachment` and shows inline art as a paperclip.
- **The seam is now checked, not just documented** — and the two directions are deliberately
  asymmetric. Assembly cross-checks the HTML's `cid:` references against the manifest: a
  referenced-but-unattached id is a broken image the reader sees, so it raises `MessageError`;
  an attached-but-unreferenced asset only costs message weight, so it warns. **The check is
  scoped to the HTML part**: the text part carries URLs as text and never a `cid:` reference,
  so copy that happens to say `cid:` — `image_matrix` titles a section "Attached (cid:)" — is
  neither read as a reference nor able to satisfy one. Making the second
  fatal would turn any gap in reference collection into a *rejected valid email*. Collection
  covers attributes, `url(cid:…)` in CSS (including `<style>` blocks), `srcset` lists, and
  markup inside `<!--[if mso]>` conditional comments.
- **Assembly is pure**: no credentials, no network, no clock, so it is testable without either.
  It stamps no `Date`/`Message-ID` and accepts no `Bcc` (that header travels with the message
  and leaks the blind-copy list) — both are transport concerns for the adapters. Output is
  byte-identical for a given input **except** the MIME boundary on a `multipart/related`
  result: the stdlib draws a fresh random one per call, so a snapshot test (#58) must
  normalize it. `svc/delivery/message.py`'s docstring says exactly what to normalize.
- **Errors are a separate hierarchy.** `DeliveryError` is a **sibling** of `EmailBuilderError`,
  not a child: a send failure is not a build failure. `MessageError` covers assembly.
- **`subject` is optional and falls back to [Email.metadata](svc/builder/email.py)'s
  `email_subject`**, which `validate()` already requires. An explicit `subject=` always wins,
  and an explicitly blank one is still an error rather than a silent fallback — a caller who
  passed something meant it. `Email.metadata` is read-only and deliberately not a copy: the
  object was never really private (an `Email` built from an `EmailMetadata` stores the
  caller's own instance), and a copy would let a mutation silently do nothing.

### Writing a delivery consumer

Two adapters exist, and the rules below are what they have in common — the shape a third one
(a generic SMTP sender, say) should transplant rather than re-derive. **An adapter transmits;
it never rebuilds.** Concretely:

1. **Take an authorized transport, not credentials.** Define a one-method `Protocol` and let
   the caller satisfy it. This is why pyHermes has no provider SDK in its dependency tree —
   `svc/gmail` and `svc/outlook` import nothing from Google or Microsoft, and a test in each
   parses the module's **AST** to keep it that way. Token acquisition, refresh and revocation
   stay with the caller, where an application's secret handling already lives.
2. **Serialise with [to_wire_bytes()](svc/delivery/message.py)**, never `message.as_bytes()`
   directly. One path means the bytes you transmit equal the bytes `save_eml()` writes, which
   is the only reason the dry run is a preview rather than an approximation. Each adapter
   asserts that equality in its own suite.
3. **Reuse [retry_with_backoff()](svc/delivery/retry.py); supply your own `is_transient`.**
   The policy is shared because it is transport-neutral; the classification is not, because
   only you know what your provider's rate-limit error looks like. If your provider sends a
   `Retry-After`, pass a `delay_hint` too. Leave the numeric arguments alone unless your
   provider genuinely needs a different ladder — omitted, they come from
   [Config](svc/config.py), so a deployment can retune every adapter at once.
4. **Never retry an unrecognised failure.** On a send path an unknown error may already have
   delivered, and a blind retry risks a duplicate. Retry only what you positively identify.
5. **Map every failure to `TransportError`, chaining the provider's exception** with
   `raise ... from exc`. Callers catch `DeliveryError` for "the email was fine, sending it
   was not".
6. **Name where your provider differs, in the module docstring.** The adapters look alike
   enough that a real difference can be "harmonised" away by mistake — Graph needing standard
   base64 where Gmail needs URL-safe, and returning no message id, are both pinned by tests
   for exactly that reason.
7. **Test against a fake transport.** No adapter test may require a live mailbox, a network,
   or recorded HTTP fixtures — fixtures drift, and a suite nobody can run locally stops being
   run. A fake is a class with one method.

**If the builder's contract turns out to be insufficient, file it against the builder** — do
not reach into private state from delivery code. That rule produced two findings (#72, #73),
both since fixed in the builder rather than worked around in delivery: `Email.metadata` is now
a read-only accessor, and `images.py` no longer claims delivery qualifies a Content-ID.

### Deliberate non-features

Recorded as decisions, so they are not re-litigated as oversights:

| Not done | Why |
|---|---|
| `Date` / `Message-ID` in assembly | Transport's job; omitting them keeps assembly pure and its output comparable |
| `Bcc` header | It travels with the message and leaks the blind-copy list — an envelope concern for adapters |
| Size re-check in assembly | `render()` already applied the 102 KB limit, and CID bytes cost *message* size, not HTML size |
| OAuth flows in adapters | Deliberately the caller's; see rule 1 above |
| Campaign management | No scheduling, recipient lists, batching or send-time analytics — this layer delivers one message to addressees the caller supplies |
| Open tracking / link rewriting | A product decision far beyond transport |
| **Any compliance policy** | pyHermes does not decide what an email must *say*. Disclaimer language, unsubscribe links and every other compliance question are the caller's judgement: the library cannot know whether an email is a commercial newsletter, an internal note or a receipt, and each answers differently — a library that guessed would be wrong for two of the three. What it guarantees instead is narrower and checkable: a region *variant* will not silently drop content the caller supplied (`REQUIRED_SLOTS`), and what renders is shape- and safety-valid (hex colours, URL schemes). `LinkRow(links=[])` and an empty `disclaimer` are both valid |
| `Retry-After` as an HTTP-date | Legal but rare; degrades to the computed backoff instead of crashing |


## Architecture — `svc/gmail`

Delivery assembles bytes; an adapter transmits them. `svc/gmail` owns Gmail's **wire
contract** — the base64url `raw` encoding, the `users.messages.send` shape, which failures
are worth retrying — and deliberately does **not** own authentication.

```python
from googleapiclient.discovery import build      # the caller's dependency, not ours
from svc.delivery import build_message
from svc.gmail import GoogleApiTransport, send_message

service = build("gmail", "v1", credentials=creds)          # caller authenticates
message = build_message(email, subject=..., sender=..., to=[...])
message_id = send_message(message, transport=GoogleApiTransport(service))
```

- **The adapter takes an authorized transport, not credentials.** `GmailTransport` is a
  `Protocol` with one method, so a real `googleapiclient` service, a stub, or anything else
  with `send_raw` satisfies it. Consequences, all deliberate: pyHermes imports nothing from
  Google and gains **no dependency** (a test asserts this by parsing the module's AST); no
  credential ever touches this package; and the whole send path is testable with **no
  mailbox, no network, and no recorded fixtures to drift**. Token acquisition, refresh and
  revocation stay with the caller, where an application's secret handling already lives.
  `GoogleApiTransport` is a duck-typed three-line shim so callers needn't rewrite it.
- **Retry policy is shared, classification is not.** [retry_with_backoff()](svc/delivery/retry.py)
  is transport-neutral and lives in `svc/delivery`, so the Outlook adapter (#70) reuses it
  rather than growing a second copy. Each adapter supplies its own `is_transient`, because
  only it knows what its provider's rate-limit error looks like. Gmail retries 429 and the
  5xx family plus network interruptions; **an unrecognised failure is not retried**, because
  on a send path it may already have delivered and a blind retry risks a duplicate.
- **`sleep` is injected**, so tests exercise the real backoff ladder without spending it.
- **The bytes sent are the bytes `save_eml()` writes** — both go through
  [to_wire_bytes()](svc/delivery/message.py), and a test asserts the equality. That is what
  makes the dry run a faithful preview rather than an approximation.
- **`TransportError`** (a `DeliveryError`) covers every send failure, always chaining the
  provider's own exception. It is distinct from `MessageError` on purpose: an unbuildable
  message is the caller's data problem, while an unsendable one may be worth retrying later
  with the exact same bytes.


## Architecture — `svc/outlook`

The second adapter, and the proof the seam generalises: it transplants
[svc/gmail](svc/gmail/sender.py)'s shape — injected transport, `TransportError` mapping,
shared retry — and differs only where Microsoft Graph genuinely differs from Gmail.

```python
import requests                                # the caller's dependency, not ours
from svc.delivery import build_message
from svc.outlook import GraphApiTransport, send_message

session = requests.Session()                   # caller authenticates
session.headers["Authorization"] = f"Bearer {token}"
send_message(build_message(email, ...), transport=GraphApiTransport(session))
```

**Transport chosen: Microsoft Graph**, over the two alternatives. SMTP needs no SDK but is
not *Outlook* — it is a generic protocol that happens to reach Microsoft 365, and Microsoft
has been retiring basic auth for it; a generic SMTP adapter would be a fine thing to add
later and could reuse `retry_with_backoff` unchanged. `win32com` is Windows-only and needs a
running Outlook install — wrong for a library. Graph won decisively because **`sendMail`
accepts a whole RFC 822 message as base64**, so the bytes sent stay identical to what
`save_eml()` writes; decomposing into Graph's JSON `message` schema would put that equality,
and the dry run's usefulness, at risk.

**Where Graph differs from Gmail** — named in the module docstring rather than quietly
diverged from, because the adapters otherwise look alike:

| | Gmail | Graph |
|---|---|---|
| base64 alphabet | URL-safe | **standard** (URL-safe is rejected) |
| success response | message id | **`202 Accepted`, empty body** |
| `send_message` returns | the id | **`None`** — there is nothing to return |
| meaning of success | message created | **accepted for processing, not delivered** |

**`Retry-After` is honoured, and that is not politeness.** Microsoft's guidance is that
throttled requests keep accruing against the quota, so a client that guesses a shorter delay
stays throttled *longer*. `retry_with_backoff()` therefore takes an optional `delay_hint`;
Outlook supplies one that reads the header, Gmail passes none and keeps the computed ladder.
An `HTTP-date` form of the header degrades to the ladder rather than crashing.


## Gotchas

- **Wheel installs work** (since #10). `templates/` lives inside the package at
  `svc/builder/templates/` and ships with the wheel; the engine resolves it via
  `importlib.resources`, which gives the same answer for an editable install and a
  site-packages install. A CI job builds the wheel and renders an email from a clean
  venv to keep it that way. Use `pip install -e ".[dev]"` for development regardless.
- **Import path.** Use `from svc.builder import …` / `from svc.builder.models import …`.
  `svc/__init__.py` re-exports nothing, and there is no `svc.models`.
- **The rendered skeleton is `svc/builder/templates/base.html`.** The engine's
  `FileSystemLoader` root is that directory and it loads `"base.html"`.

## Working in this repo — the `.claude/` tooling

This repo carries a curated `.claude/` asset library (installed from the `claudeBrain`
factory). Full inventory: [.claude/CATALOG.md](.claude/CATALOG.md) (regenerate with `/reindex`).
Reach for these rather than improvising:

- **Python work** → the `python-development` / `-review` / `-maintenance` / `-deployment`
  skills + `coding-standards` auto-load. For isolated, summary-returning implementation,
  delegate to the **`python-developer`** agent (already scoped to `svc/` and this repo's
  `pytest` verification).
- **GitHub** (PRs, issues, releases, review comments) → the `github-*` skills, or the
  **`github-operator`** agent. Note: that agent expects a GitHub **MCP server**; with only the
  `gh` CLI it is degraded — the skills work regardless.
- **Shipping a unit of work** → `/version-set` writes `.meta/version` (semver + goals), then
  `/version-ship` (or the `ship-version` workflow) branches/commits/PRs from those goals.
- **Verbose output** (test runs, large files, doc fetches) → delegate to the **`token-manager`**
  agent to keep the main context lean.
- **Acceptance check** before shipping → the `goal-auditor` agent (judges the diff against
  `.meta/version` goals). **Fact-checking an asset's claims** → the `verify-claims` workflow /
  `claim-grounding` skill.
- **Cross-session memory is active.** SessionStart hooks auto-load
  [.claude/memory/INDEX.md](.claude/memory/INDEX.md) — read it before starting; the session
  is logged at the end. Full detail lives in `.claude/memory/sessions/`.
- **Available but speculative** (no matching code yet): the `finance-quantitative-developer`
  agent + `quantitative-finance` / `financial-timeseries-analysis` / `backtesting-validation`
  skills (for a future analytics layer); `branding` / `presentation-design` / `report-builder`
  (for newsletter content and aesthetic).
- **Hooks are active and non-mutating**: catalog + `settings.json` auto-rebuild on edits,
  advisory git guards on commit/push, session-memory lifecycle. To change hooks, edit the
  `*.json` **fragments** in `.claude/hooks/` then run `python .claude/hooks/build-hooks.py` —
  never hand-edit the generated `hooks` block in `settings.json`.

## Open work

- Tracked in [GitHub issues](https://github.com/RorySullivan1/pyHermes/issues), organised as
  epics with sub-issues. **Every filed epic is now complete**: #38 (header region), #45 (size
  themes), #46 (colour themes), #52 (delivery), #53 (plain text), #54 (QA harness), #55
  (footer region), #56 (typography), #87 (the `Header` region), #88 (banner region) and #98
  (the footer box).
- **The plain-text epic (#53) is complete** — #108 the degrader, #109 the projections, #110 the
  text goldens, #111 the `multipart/alternative` assembly. Four things it leaves:
  - **A second projection beats a degradation, and the test is what says so.** Stripping the
    render was the obvious approach and produces garbage for exactly the components that
    matter most. `TemplateEngine.render` is monkeypatched to raise while every fixture
    projects, so "structure, never the rendered HTML" is asserted rather than intended.
  - **The reserved seam worked.** `message.py`'s docstring had said for two epics that the HTML
    part would become half of an alternative and the related subtree would nest inside
    unchanged. It did, byte for byte, one level deeper, and **the adapters changed by zero
    lines** — both serialise through `to_wire_bytes()`. A seam named in prose and left alone is
    worth more than one discovered late.
  - **An orthogonal epic is one that shares no surface.** #53 touched no template and #56
    touched only templates, which is why the same email projects identically at every colour,
    density and font theme — a test asserts it, and it is what makes "one house format" a
    property rather than a coincidence.
  - **The `&copy;` question inverts between the two parts, and one method answers both.** The
    HTML needs the entity against latin-1 mojibake; the charset-declared MIME part needs the
    character. The footer degrades `resolved_copyright_html()` rather than branching, so the
    two spellings cannot drift.
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
- **The QA harness (#54) is complete**, and it changes how the visual epics discharge their
  own acceptance criteria:
  - **A visual epic gets its eyeball artifacts from the screenshot runner**, not from ad-hoc
    `.save()` calls. `python -m qa.preview <fixture> --screenshot` locally; CI uploads the
    whole gallery on every PR. Side-by-side theme review is two runs of one command, and
    #43's density claim is legible straight off the image heights: 2516 / 3030 / 3731 px for
    the same email at compact / standard / spacious.
  - **Migration PRs cite gallery-wide goldens, not a single email.** "Byte-identical" means
    every gallery fixture plus its asset manifest — a container-template edit that one
    email's ratios never exercise no longer slips through. Both theme epics discharged their
    claim this way: #46 moved one comment and nothing else; #45 moved nothing at all.
  - **A theme lands with a fixture.** Epic #54 anticipated "one per theme as themes land",
    and all five now exist — `slate_theme` for the palette, `compact_size` / `spacious_size`
    for the two densities, `modern_fonts` for the faces, with `minimal_banner` the worked
    example of a fixture that pins one region variant. #88 added the other kind: `custom_banner` pins a *combination* rather than
    a variant, because each of its four axes has its own tests and none of them can see an
    interaction.
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
- **The golden characterization test (#32/#58) has landed** — the gate every template
  migration waited on is now in the suite. Everything touching `base.html` or `EmailMetadata`
  still sequences rather than interleaves (several epics contend on those two surfaces), but
  each of them now inherits byte-identity proof for free: change a template, and the gallery
  tells you which email moved and where. The delivery epic (#52) is complete and contends
  with none of them.
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
- **The two findings the harness surfaced are closed** (#76, #78) — the first work in a
  while whose *point* was a golden diff rather than its absence. Both had been deferred by
  every epic for the same reason: each changes rendered output, and every epic claimed the
  gallery stays byte-identical at each step. What they leave behind:
  - **Only a browser could have caught #76.** The HTML was byte-identical to its golden the
    whole time the mobile KPI strip overflowed its viewport, the size gate passed, and no
    unit test measures layout. The regression test therefore lives with the screenshots, and
    it asserts *equality* with the viewport where the old one asserted `>=`.
  - **Measure the fix, do not reason about it.** #76's issue recommended dropping
    `width:100%` on the grounds that a `display:block` element fills its container. In
    Chromium a `<td>` re-displayed as block inside a table shrink-wraps instead, collapsing
    the cell to a ~120px stub. `box-sizing:border-box` was the fix; the measurement is in the
    commit.
  - **A rule can be satisfied by scope, not only by value.** #78's `rgba()` scrim could not
    be made opaque — it exists to darken a photograph, and an opaque colour would paint over
    it. Outlook already draws that scrim from `v:fill`, so the CSS copy is now
    downlevel-revealed, and the linter learned to model `<!--[if !mso]><!-->` rather than
    the rule being weakened.
  - **The size epic made #78's biggest finding small.** 107 unitless `line-height`
    occurrences would have been a template-wide sweep before #45; afterwards leading is a
    token, so it was one `percent` filter at the boundary. The care was all in *inheritance*
    — a unitless value is inherited as a number and recomputed per element, a percentage as
    the computed px — which is why the nine elements that inherited their leading now state
    it explicitly, and why the change is pixel-neutral rather than merely legal.
- [README.md](README.md) is the human-facing entry point (what it is, install, build, send,
  the constraints it enforces). CLAUDE.md stays the *rationale* document — the README says
  what the library does, this file says why each constraint exists. Keep the split; do not
  let the README grow into a second copy of the reasoning below.
- Current project state and decisions: [.claude/memory/INDEX.md](.claude/memory/INDEX.md).
