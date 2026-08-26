# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this project is

pyHermes builds **HTML emails for academic / financial newsletters**. Python composes
Jinja2 templates into a single, inline-CSS HTML document engineered to survive email
clients (Gmail, Outlook) — the hard part is staying under Gmail's clipping limit while
keeping the layout table-based and portable.

**Scope today = build *and* send.** Composing the HTML is still the bulk of the product,
but the chain is complete: `svc/builder/` renders and declares, `svc/delivery/` assembles a
sendable `EmailMessage`, and `svc/gmail/` + `svc/outlook/` transmit it. Adapters own their
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
│   ├── engine.py       — TemplateEngine (Jinja2, StrictUndefined, autoescape OFF)
│   ├── email.py        — Email + EmailBuilder (fluent), _validate_size()
│   ├── regions.py      — Region base + Header/MinimalHeader, Footer/MinimalFooter
│                         (body = the section list, deliberately not a class)
│   ├── containers.py   — Container, FullWidth, TwoColumn, ThreeColumn (+ `highlight=` property)
│   ├── components.py   — Component, CardGroup, DataTable, ChartBlock, ImageBlock, TextBlock, NumberedList, AuthorBlock
│   ├── models.py       — EmailMetadata (the email's facts), Card, KpiItem, TableRow, NumberedItem, SectionConfig
│   ├── images.py       — EmailImage (hosted/attached/inline), ImageAsset manifest, format sniffing
│   ├── enums.py        — StrEnum vocab: TwoColumnRatio, ThreeColumnRatio, CardOrientation, EmbedStrategy, ImageAlign
│   ├── filters.py      — Jinja filters (e.g. validate_hex_color)
│   ├── exceptions.py   — EmailBuilderError hierarchy
│   └── templates/      ← packaged with the wheel (moved here in #10)
│       ├── base.html                — the rendered skeleton (four slots: header_html,
│                                      sections_html, footer_contact_html, footer_legal_html)
│       ├── regions/*.html           — header.html, header-minimal.html,
│                                      footer-contact.html, footer-legal.html
│       ├── common/containers/*.html — layout geometry (full-width, col-50-50/30-70/70-30, col-33-33-33/50-25-25/25-50-25/25-25-50)
│       ├── analysis/*.html          — data components (card-group, data-table, chart-block)
│       ├── media/*.html             — image components (image-block)
│       └── text/*.html              — text components (text-block, numbered-list, author-block)
├── delivery/           ← transport-neutral MIME assembly (consumes the builder)
│   ├── __init__.py     — public API: build_message, save_eml, collect_cid_references
│   ├── message.py      — build_message() → multipart/related; to_wire_bytes(); save_eml()
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
└── fixtures/          — the gallery: minimal, kitchen_sink, image_matrix, minimal_header,
                        minimal_footer,
                        + all_fixtures()
    └── goldens/       — the checked-in snapshots: <name>.html + <name>.assets.txt
output/                 — generated email HTML (gitignored; not committed)
tests/                  — pytest unit suite (validation, error paths, size limits)
.github/workflows/      — CI: ruff, mypy, pytest
.claude/                — curated tooling library (skills, agents, commands, hooks, memory)
```

## The fixture gallery — `qa/fixtures`

The shared set of representative emails every later QA tool consumes (#57, the first step of
epic #54). Four fixtures, each a `build()` returning a built `Email`, enumerated through
`all_fixtures()` so a consumer never imports them one by one:

| Fixture | What it is for |
|---|---|
| `minimal` | The smallest valid email. Its value is negative space — it renders the skeleton with every optional region empty, so it catches a change to `base.html`'s defaults that a richer fixture masks by supplying the value itself |
| `kitchen_sink` | Every public component in every container ratio, `highlight=True` included, **and every `EmailMetadata`, `Header` and `Footer` field set to a distinctive non-default value**. The fixture the golden is worth the most on, and #32's characterization email |
| `image_matrix` | All three embed strategies, plus the same attached image referenced twice — the shortest proof that `assets()` reports exactly the `cid:` references the HTML contains |
| `minimal_header` | The `MinimalHeader` variant (#36). Differs from the others in one argument, so its golden pins that a region swap changes the masthead and nothing else — no VML, no `background-image`, every email-level fact still present, and a CID logo attached exactly once through the region's own `images()` |
| `minimal_footer` | The `MinimalFooter` variant (#66), the same argument at the other end. Its golden pins that the contact card and its `v:roundrect` are *absent* while the legal block is byte-identical to the default footer's — because the variant composes that template rather than forking it. Paired with the **default** header on purpose: the two region choices are independent, and swapping both at once could not say which one moved a byte |

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
`Header` or `Footer` field.** Four completeness tests introspect rather than hand-list: one
over every public `Component` subclass exported from `svc.builder`, one over
`dataclasses.fields(EmailMetadata)`, a third asserting each metadata value *differs from its
own default*, and a fourth doing both at once over each **region** — parametrized across
header and footer, and read off the *built* region, so it holds however the fixture chooses
to supply it. A field set to its
default is one the golden cannot pin, because the render would not move if the default changed
underneath it. Only exemptions are named, in `DEPRECATED_COMPONENTS` (today: `KpiStrip`, whose
markup duplicates a section already in the gallery and which warns on construction), plus
`EmailMetadata.header` and `EmailMetadata.footer` themselves — `kitchen_sink` supplies both
the flat, pre-split way on purpose, which is how the golden pins the back-compatible path.

Each `build()` also takes an optional `template_dir`, threaded to `EmailBuilder`, so the whole
gallery can be rendered against a *candidate* template set — which is the question a template
migration actually asks ("does this edit move any email?"), and how the golden harness's
detection test perturbs a real template instead of only the compared text. It stays out of the
`FixtureBuilder` alias deliberately: consumers must be able to call a builder with no arguments.

## Golden snapshots — `qa/goldens.py` + `qa/fixtures/goldens/`

The byte-identity bar the migration epics (#33, #41, #42, #49) all promise to hold, made
mechanical (#58). Two artifacts per fixture, because a render and its attachments drift
independently:

| File | What it pins |
|---|---|
| `goldens/<name>.html` | The rendered HTML, byte for byte, no normalization |
| `goldens/<name>.assets.txt` | One tab-separated record per `ImageAsset`, **in manifest order** — content-id, MIME type, byte length, filename |

Four decisions worth not re-litigating:

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
| `size-budget` | warn/error | The 90/102 KB thresholds, **attributing the bytes to section-marker regions** |

Five decisions worth not re-litigating:

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
- **`DEFERRED_RULES` is a recorded decision, not an oversight.** Three real, sourced findings
  (unitless `line-height`, an `rgba()` background, an empty `url()`) are filed as #78 rather
  than shipped, because the templates violate them today and the fix moves surfaces several
  epics contend on. A linter that arrives red teaches everyone to ignore it. A test asserts
  each deferred entry names its filed issue and is not also in `SOURCES`.
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

**It composes; it never reimplements.** Fixtures come from `all_fixtures()`, findings from
`lint_html()`, images from `capture_emails()`. A test asserts the HTML it writes equals
`Email.render()` byte for byte, because the one thing that would make this tool worse than
useless is being a second rendering path.

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

Every email is `skeleton ← regions (header | body | footer) ← containers ← components`:

1. **Skeleton** — [svc/builder/templates/base.html](svc/builder/templates/base.html). The full HTML page (head,
   preheader, palette comment) with four variable holes: `{{ header_html }}`,
   `{{ sections_html }}`, `{{ footer_contact_html }}` and `{{ footer_legal_html }}`.
   Rendered last by [Email.render()](svc/builder/email.py).
2. **Regions** — the named areas of the email. Templates in
   [svc/builder/templates/regions/](svc/builder/templates/regions/); Python wrappers in
   [svc/builder/regions.py](svc/builder/regions.py), all sharing a `Region` base that owns
   validation, the image walk, the facts-over-presentation layering and `render_slots()`.
   Two of them: `Header`/`MinimalHeader` and `Footer`/`MinimalFooter`. The **body region is
   the ordered section list** — deliberately not a class, since wrapping it would add a
   layer with no behaviour.
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

**A region fills one or more named slots** — the third rule of the layer, and the epic's one
genuine divergence from the header's shape. The header fills one; the footer fills **two**,
because its contact card is a `<tr>` inside the body table while its legal block is a
sibling table below it. One fragment spanning both would have to close a `</table>` the
skeleton opened — a fragment that is unbalanced on its own and valid at exactly one
insertion point. So a region declares `SLOTS` (the skeleton's contract, fixed) and
`TEMPLATE_PATHS` (what this variant fills), and `Region.render_slots()` returns one HTML
string per slot. **A slot a variant leaves unfilled renders empty**, which is how
`MinimalFooter` *omits* the contact card rather than the template growing a conditional to
express its absence. `Header.render()` survives as the single-slot convenience and
delegates to `render_slots()` — one rendering path, not two.

**The preheader stays skeleton plumbing.** Header, body and footer are the complete set;
a fourth region is a decision to reopen, not a gap to fill.

### The ownership rule — facts flow down

**Facts about the email live on `EmailMetadata`; how a region presents them lives on the
region.** Stated once, for both regions: a region presents facts, it cannot own or contradict
them.

| Stays on `EmailMetadata` (facts / constraints) | Lives on the region (presentation) |
|---|---|
| `email_subject`, `preheader_text` | `Header.background_image_url` |
| `firm_name`, `campaign_name` | `Header.logo_url`, `logo_alt`, `logo_width` |
| `date_range`, `issue_label`, `header_disclaimer` | `Header.resolved_logo_alt()`, `resolved_logo_width()`, `DEFAULT_LOGO_WIDTH` |
| `footer_disclaimer`, `current_year` | `Footer.contact_heading`, `contact_description`, `contact_cta_label` |
| `contact_url`, `unsubscribe_url`, `view_in_browser_url` | `Footer.unsubscribe_label`, `view_in_browser_label` |

Two boundary calls, each made for a reason rather than by shape:

- **`header_disclaimer` is a fact**, though it is *displayed* in the masthead: it is legal
  copy pairing with `footer_disclaimer`, and legal copy is a fact about the email.
- **The footer's three URLs are facts**, though the header's `logo_url` is presentation. A
  logo is an image the *region* chose; an unsubscribe address is a property of the mailing,
  and `EmailMetadata.validate()` already checks all three schemes. What the footer owns is
  the wording *around* them — the headings, the button label, the link labels.

`EmailMetadata.HEADER_FACTS` and `FOOTER_FACTS` name what is handed down at render time.

The rule is **mechanical, not remembered**: `Region.context()` layers the email's facts *over*
its own keys rather than under them, so a region cannot shadow a fact even by accident — and a
test per region asserts the two key sets stay disjoint.

**The flat region keywords still work.** `EmailMetadata(logo_url=…, logo_alt=…, logo_width=…,
header_bg_image_url=…)` builds the header for you and `EmailMetadata(contact_heading=…,
contact_description=…, contact_cta_label=…, unsubscribe_label=…, view_in_browser_label=…)`
builds the footer, so an email written before either split renders byte-identically. They are
`InitVar`s — constructor arguments only, never attributes, absent from `fields()`, `repr` and
`==` — so the region stays the single owner. Passing them *and* the explicit region raises
rather than silently picking one.

Two consequences worth knowing: a bad masthead URL now raises at `EmailMetadata` construction
rather than at `.validate()`, and the message names `header.logo_url` /
`header.background_image_url` — where the field actually lives.

**An explicit region replaces the one the flat keywords built.** `Email(footer=…)`,
`set_footer()` and `EmailBuilder.footer()` are swaps, not merges, so a flat
`unsubscribe_label` alongside an explicit `footer=` is silently discarded — the conflict
check only fires inside `EmailMetadata`, where both spellings are visible at once. Put
presentation on whichever region actually renders; `qa/fixtures/minimal_footer.py` is the
worked example.

**Legal content is not optional — and that is enforced, not conventional.** A footer variant
may drop the contact card; it may not drop the disclaimer or the unsubscribe link.
`Footer.REQUIRED_SLOTS` makes an unfilled legal slot a `ValidationError` at construction, and
a parametrized test walks **every** `Footer` the package exports — found by introspection, so
a variant added later is covered without anyone remembering — and asserts both survive its
render. A golden could not do this job: a variant that dropped the unsubscribe link would
have a golden of its own, and it would pin the omission as faithfully as it pins anything
else.

### Three standing rules the harness enforces

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
4. **A region that carries images must declare them.** Same rule components already have,
   and the same failure if you skip it: the bytes never reach `Email.assets()` and the
   `cid:` reference renders as a broken image. Declaring means listing the field in
   `IMAGE_FIELDS` — `Region.images()` walks it — or overriding `images()` if the bytes come
   from somewhere else. `Email.images()` is header + sections + footer, so the region is the
   only owner of its own images. The footer participates even though no shipped variant
   carries an image: a test builds one that does, because the slot has to work *before*
   someone writes that variant for real.

### Public API (import from `svc.builder`)

```python
from svc.builder import EmailBuilder, Email, \
    Region, Header, MinimalHeader, Footer, MinimalFooter, \
    FullWidth, TwoColumn, ThreeColumn, \
    CardGroup, DataTable, ChartBlock, ImageBlock, TextBlock, NumberedList, AuthorBlock
from svc.builder.models import Card, KpiItem, TableRow, NumberedItem, EmailMetadata, SectionConfig
from svc.builder.enums import TwoColumnRatio, ThreeColumnRatio, CardOrientation, EmbedStrategy, ImageAlign
from svc.builder.images import EmailImage, ImageAsset
```

Choosing a region is an argument, never a template fork — and there is no selection
mechanism beyond passing the object. Both regions work identically:

```python
Email(metadata, header=MinimalHeader(logo_url=logo), footer=MinimalFooter())   # non-fluent
EmailBuilder().metadata({...}).header(MinimalHeader()).footer(MinimalFooter()).section(...)
```

`EmailBuilder.header()` / `.footer()` follow the same sequencing rule as `section()`: calling
one before `metadata()` raises `RuntimeError` — a programming error in the call sequence, not
rejected data. Omit them and the regions come from the metadata, which the flat keywords
built. `Email.header` and `Email.footer` are read-only accessors for the same reasons as
`Email.metadata`; use `Email.set_header()` / `Email.set_footer()` to swap them.

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
    `TextBlock.content`, `NumberedItem.body`, and the metadata disclaimers. **Escaping
    untrusted text in these is the caller's job** — use
    [escape_html()](svc/builder/filters.py) (`from svc.builder.filters import escape_html`).
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
`Container.components()` → `Email.assets()`. `Email.images()` is **header + sections +
footer**: the masthead's `logo_url` and `background_image_url` reach the manifest through
`Header.images()`, not through the metadata, and both accept an `EmailImage` as well as a
bare URL string. No shipped footer carries an image, and the footer is walked anyway — the
slot has to exist before a variant with a signature block or social icons is written, or its
bytes drop silently. **A new image-bearing component — or region — must override `images()`** or
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
  logo takes `Header.logo_alt`, which resolves **explicit header value → the `EmailImage`'s
  own `alt` → `firm_name`**. `logo_width` resolves the same way, ending at
  `Header.DEFAULT_LOGO_WIDTH` (90). The chains live on the region, and `firm_name` is a
  *parameter* to `resolved_logo_alt()` rather than a field — the header is handed the fact,
  it does not hold it. Defaults still reproduce the pre-split output.
  `Header.background_image_url` is a CSS background, and a CSS background cannot carry alt
  text — it is decorative by construction.
- **Footer copy is parameterised**, and since #64 it lives on the `Footer` region:
  `contact_heading`, `contact_description`, `contact_cta_label`, `unsubscribe_label`,
  `view_in_browser_label`. Defaults are the strings `base.html` used to hardcode, so a
  newsletter in another language no longer needs a template fork, and the flat
  `EmailMetadata(...)` spelling still builds the region. The CTA is emitted twice (VML for
  Outlook, an anchor for everyone else) — both read the same parameter, and a test asserts
  the label appears in both under `Footer` and **zero** times under `MinimalFooter`, where
  the block it lived in is not rendered at all.
- **Not parameters, deliberately**: fonts, colours, padding, and the 680px table geometry.
  That is the design system, and letting callers vary it per email is how a template stops
  surviving Outlook.

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

## Architecture — `svc/delivery`

The builder **declares** a CID embed; delivery **performs** it. `Email.render()` gives the
HTML and `Email.assets()` gives the manifest; [build_message()](svc/delivery/message.py)
turns that pair into a sendable `EmailMessage`.

```python
from svc.delivery import build_message, save_eml

message = build_message(email, sender="research@example.com",
                        to=["reader@example.com"])   # subject defaults from the email
save_eml(message, "output/preview.eml")     # dry run — no transport, no credentials
```

- **Structure**: `text/html` when the email has no CID images; `multipart/related` when it
  does, one inline part per asset. When plain-text lands (#53) the HTML part becomes half of
  a `multipart/alternative` and this nests inside unchanged.
- **The consumer adds the decorations.** `ImageAsset.content_id` is bare, so assembly emits
  `Content-ID: <id>` — Python's `add_related()` stores whatever it is given, and a bare id is
  an RFC-invalid header. It also passes `disposition="inline"` explicitly, because supplying
  a `filename` alone yields `attachment` and shows inline art as a paperclip.
- **The seam is now checked, not just documented** — and the two directions are deliberately
  asymmetric. Assembly cross-checks the HTML's `cid:` references against the manifest: a
  referenced-but-unattached id is a broken image the reader sees, so it raises `MessageError`;
  an attached-but-unreferenced asset only costs message weight, so it warns. Making the second
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
| Plain-text alternative | Its own epic (#53); the `multipart/alternative` slot is left open for it |
| Size re-check in assembly | `render()` already applied the 102 KB limit, and CID bytes cost *message* size, not HTML size |
| OAuth flows in adapters | Deliberately the caller's; see rule 1 above |
| Campaign management | No scheduling, recipient lists, batching or send-time analytics — this layer delivers one message to addressees the caller supplies |
| Open tracking / link rewriting | A product decision far beyond transport |
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
  epics with sub-issues: #45 size themes, #46 color themes, plus #53 plain-text and #56
  typography as parents. #38 (header region), #52 (delivery), #54 (QA harness) and #55
  (footer region) are complete.
- **The QA harness (#54) is complete**, and it changes how the visual epics discharge their
  own acceptance criteria:
  - **#43 (size themes) and #50 (color presets) get their eyeball artifacts from the
    screenshot runner**, not from ad-hoc `.save()` calls. `python -m qa.preview <fixture>
    --screenshot` locally; CI uploads the whole gallery on every PR. Side-by-side theme
    review is two runs of one command.
  - **Migration PRs under #38, #45 and #46 cite gallery-wide goldens, not a single email.**
    "Byte-identical" now means every gallery fixture plus its asset manifest — a
    container-template edit that one email's ratios never exercise no longer slips through.
  - **A theme lands with a fixture.** Epic #54 anticipated "one per theme as themes land";
    the completeness tests make that concrete for components, metadata fields and both
    regions' fields already — and `minimal_header` / `minimal_footer` are the worked
    examples of a fixture that exists to pin one variant.
- **The region model is complete (#38 header, #55 footer)**, and between them `base.html`
  went from 277 lines to 116. What the remaining epics inherit:
  - **The mechanism is generalised, not duplicated.** `Region` owns validation, the image
    walk, the facts-over-presentation layering and `render_slots()`; a region declares its
    slots, its templates and its fields. A future region-like idea should start there —
    though "no third region" is a decision, not a gap: the preheader stays skeleton
    plumbing.
  - **`EmailMetadata` is facts only.** A new field belongs there if it is *true of the
    email* and on a region if it is *how something looks*. The flat-keyword `InitVar` pattern
    is how a field moves off the metadata without breaking an existing call site.
  - **`base.html` is down to the head, the skeleton and the preheader** — so the theme epics (#45, #46)
    now contend on far less of one file than they did, and on almost none of the markup that
    made it fragile.
  - **A variant is what proves a seam.** `MinimalHeader` and `MinimalFooter` each differ from
    their default in exactly which slots they fill; each has a gallery fixture and a golden.
    A seam with one implementation is a refactor.
- **The golden characterization test (#32/#58) has landed** — the gate every template
  migration waited on is now in the suite. Everything touching `base.html` or `EmailMetadata`
  still sequences rather than interleaves (several epics contend on those two surfaces), but
  each of them now inherits byte-identity proof for free: change a template, and the gallery
  tells you which email moved and where. The delivery epic (#52) is complete and contends
  with none of them.
- **Two findings the harness surfaced are still open**: #76 (the mobile `.kpi-cell` collapse
  overflows its viewport by its own padding — `base.html`'s CSS, still there) and #78 (three
  sourced Outlook findings the lint pass defers rather than shipping red; one of the three,
  the `rgba()` scrim, now lives in `templates/regions/header.html`). They were deliberately
  **not** folded into #38 or #55: each changes rendered output, and both epics' whole claim
  was that every step leaves the gallery byte-identical. They are their own PR, and the
  golden diff they produce is the point rather than the problem.
- [README.md](README.md) is the human-facing entry point (what it is, install, build, send,
  the constraints it enforces). CLAUDE.md stays the *rationale* document — the README says
  what the library does, this file says why each constraint exists. Keep the split; do not
  let the README grow into a second copy of the reasoning below.
- Current project state and decisions: [.claude/memory/INDEX.md](.claude/memory/INDEX.md).
