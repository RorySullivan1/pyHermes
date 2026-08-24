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
mypy                          # config in pyproject: files = ["svc"]
```

CI runs all four on every PR ([.github/workflows/ci.yml](.github/workflows/ci.yml)).

The `tests/` pytest suite is the automated safety net (validation, error paths, size
limits). There is no in-repo end-to-end smoke test — to eyeball a full render after a change
to `svc/builder/` (including its `templates/`), build an email and `.save()` it into `output/`
(gitignored, not committed), then open it in a browser.

Slash commands (from the `.claude/` library): `/version-set`, `/version-ship`, `/reindex`.

## Directory map

```
svc/
├── builder/            ← current OO email builder (use this for new work)
│   ├── __init__.py     — public API surface (re-exports everything below)
│   ├── engine.py       — TemplateEngine (Jinja2, StrictUndefined, autoescape OFF)
│   ├── email.py        — Email + EmailBuilder (fluent), _validate_size()
│   ├── containers.py   — Container, FullWidth, TwoColumn, ThreeColumn (+ `highlight=` property)
│   ├── components.py   — Component, CardGroup, DataTable, ChartBlock, ImageBlock, TextBlock, NumberedList, AuthorBlock
│   ├── models.py       — EmailMetadata, Card, KpiItem, TableRow, NumberedItem, SectionConfig
│   ├── images.py       — EmailImage (hosted/attached/inline), ImageAsset manifest, format sniffing
│   ├── enums.py        — StrEnum vocab: TwoColumnRatio, ThreeColumnRatio, CardOrientation, EmbedStrategy, ImageAlign
│   ├── filters.py      — Jinja filters (e.g. validate_hex_color)
│   ├── exceptions.py   — EmailBuilderError hierarchy
│   └── templates/      ← packaged with the wheel (moved here in #10)
│       ├── base.html                — the rendered skeleton (one hole: {{ sections_html }})
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
output/                 — generated email HTML (gitignored; not committed)
tests/                  — pytest unit suite (validation, error paths, size limits)
.github/workflows/      — CI: ruff, mypy, pytest
.claude/                — curated tooling library (skills, agents, commands, hooks, memory)
```

## Architecture — `svc/builder`

`svc/builder/` is the only implementation. Its public surface is re-exported from
[svc/builder/__init__.py](svc/builder/__init__.py).

(A legacy flat string-replace assembler, `svc/assembler.py`, was removed in #14. It is
recoverable from git history if ever needed for reference.)

### The three-layer composition model

Every email is `skeleton ← containers ← components`:

1. **Skeleton** — [svc/builder/templates/base.html](svc/builder/templates/base.html). The full HTML page (head,
   header, footer, palette comment) with one variable hole: `{{ sections_html }}`. Rendered
   last by [Email.render()](svc/builder/email.py).
2. **Containers** — layout geometry only. In [svc/builder/templates/common/containers/](svc/builder/templates/common/containers/).
   Each produces a `<tr>` block sized to the 680px outer email table. Python wrappers in
   [svc/builder/containers.py](svc/builder/containers.py).
3. **Components** — content blocks. Templates in
   [svc/builder/templates/analysis/](svc/builder/templates/analysis/) and
   [svc/builder/templates/text/](svc/builder/templates/text/); Python wrappers in
   [svc/builder/components.py](svc/builder/components.py).

A `Container` holds one or more `Component`s, calls `component.render(engine)`, and embeds
the fragment into its own template. `Email` concatenates all section HTML into the skeleton's
`sections_html` slot. **Adding a content type = new template file + new `Component` subclass**
that sets `template_path` and implements `context()`.

### Public API (import from `svc.builder`)

```python
from svc.builder import EmailBuilder, Email, FullWidth, TwoColumn, ThreeColumn, \
    CardGroup, DataTable, ChartBlock, ImageBlock, TextBlock, NumberedList, AuthorBlock
from svc.builder.models import Card, KpiItem, TableRow, NumberedItem, EmailMetadata, SectionConfig
from svc.builder.enums import TwoColumnRatio, ThreeColumnRatio, CardOrientation, EmbedStrategy, ImageAlign
from svc.builder.images import EmailImage, ImageAsset
```

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
  never disable it without confirming a non-Gmail channel.
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
`Container.components()` → `Email.assets()`, plus the `EmailMetadata` image fields
(`logo_url`, `header_bg_image_url`), which accept an `EmailImage` as well as a bare URL
string. **A new image-bearing component must override `images()`** or its bytes never reach
the manifest, and its `cid:` reference will render as a broken image.

Rules the module enforces at construction, per the validation philosophy below:

- **Format is sniffed from magic bytes, not the file extension** — PNG, JPEG and GIF only.
  WebP and SVG are detected specifically so the rejection can say why (Outlook's Word engine
  renders neither, and SVG can carry script).
- **`alt` is required.** It is what the reader sees whenever images are blocked, which for
  Outlook desktop is the default state.
- **Content-IDs are content-addressed** — `sha256(bytes)[:16]` by default, so the same image
  used in two sections is attached once, and the same input always yields the same output.
  An explicit `content_id` is checked against `[A-Za-z0-9._+-]{1,128}`.
- **Inline images are capped** at `INLINE_LIMIT_KB` (48 KB of base64) so one image cannot eat
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

- **Alt text is always a parameter.** `ImageBlock`/`ChartBlock` take `alt`; the skeleton
  logo takes `logo_alt`, which resolves **explicit metadata → the `EmailImage`'s own `alt`
  → `firm_name`**. `logo_width` resolves the same way, ending at
  `EmailMetadata.DEFAULT_LOGO_WIDTH` (90). `header_bg_image_url` is a CSS background, and
  a CSS background cannot carry alt text — it is decorative by construction.
- **Skeleton copy is parameterised**: `contact_heading`, `contact_cta_label`,
  `unsubscribe_label`, `view_in_browser_label`. Defaults are the strings `base.html` used
  to hardcode, so a newsletter in another language no longer needs a template fork. The CTA
  is emitted twice (VML for Outlook, an anchor for everyone else) — both read the same
  parameter, and a test asserts the label appears in both.
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

message = build_message(email, subject="Weekly Market Wrap",
                        sender="research@example.com", to=["reader@example.com"])
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
   `Retry-After`, pass a `delay_hint` too.
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
not reach into private state from delivery code. That rule has already produced two findings
(#72, #73), which is the point of having it.

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
  epics with sub-issues: #38 header region, #45 size themes, #46 color themes, #52 delivery,
  #54 QA harness, #55 footer region, plus #53 plain-text and #56 typography as parents.
- **The golden characterization test (#32/#58) gates all template migration**, and everything
  touching `base.html` or `EmailMetadata` sequences rather than interleaving — several epics
  contend on those two surfaces. The delivery epic (#52) is complete and contends with none
  of them.
- Two builder-contract findings await a decision, neither blocking: **#72** (`Email` publishes
  `render()`/`assets()` but no way to read its own metadata) and **#73** (`images.py` promises
  delivery adds `@` to a Content-ID, which RFC 2392 and its own regex both rule out).
- Current project state and decisions: [.claude/memory/INDEX.md](.claude/memory/INDEX.md).
