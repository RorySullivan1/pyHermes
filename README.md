# pyHermes

Build HTML emails that survive the clients people actually read them in — then send them.

An HTML email is not a web page. Gmail clips the message body past ~102 KB and shows a
"View entire message" link; Outlook on Windows renders through Microsoft Word's layout
engine, which ignores `max-width`, drops most modern CSS, and will not display a `data:`
URI at all. The usual answers — a CSS framework, a `<div>` grid, an external stylesheet —
all fail there.

pyHermes composes Jinja2 templates into a single inline-CSS, table-based document
engineered for those constraints, and enforces the ones that break silently. It depends on
**Jinja2 and nothing else**, including on the send path.

```python
from svc.builder import EmailBuilder, FullWidth, CardGroup, TextBlock
from svc.builder.models import KpiItem

email = (
    EmailBuilder()
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
        content=TextBlock("<p>Equity markets advanced on softer inflation data.</p>"),
        title="Week in Review",
    ))
    .build()
)

email.save("output/weekly-wrap.html")   # prints the rendered size, or raises above 102 KB
```

## Install

Requires Python 3.11+. Not published to PyPI — install from a clone:

```bash
pip install -e ".[dev]"     # editable, plus pytest / ruff / mypy
```

The `dev` extra also pulls `requests` and `httplib2`. Those are the HTTP transports the send
adapters *document*, not ones they use: the adapters import neither, and an AST-parsing test
in each keeps it that way. They exist so retry classification can be tested against the real
exception hierarchies — a bug once shipped precisely because the tests only ever injected
builtins.

## Sending

Building is the bulk of the product, but the chain is complete. Assembly is transport-neutral
and pure; the adapters transmit.

```python
from svc.delivery import build_message, save_eml

message = build_message(
    email,
    sender="research@example.com",
    to=["reader@example.com"],       # subject defaults from the email's metadata
)

save_eml(message, "output/preview.eml")   # dry run: no credentials, no network
```

That `.eml` is a faithful preview, not an approximation — `save_eml()` and both adapters
serialise through the same `to_wire_bytes()`, and each adapter asserts the bytes it transmits
equal the bytes written to disk.

To actually send, bring an authorized transport:

```python
from googleapiclient.discovery import build       # your dependency, not pyHermes'
from svc.gmail import GoogleApiTransport, send_message

service = build("gmail", "v1", credentials=creds)  # you authenticate
message_id = send_message(message, transport=GoogleApiTransport(service))
```

```python
import requests                                    # your dependency, not pyHermes'
from svc.outlook import GraphApiTransport, send_message

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
`header | body | footer`:

| Layer | What it owns | Where |
|---|---|---|
| **Skeleton** | the whole page — head, preheader, wrapper — with four holes: `{{ header_bar_html }}`, `{{ banner_html }}`, `{{ sections_html }}`, `{{ footer_html }}` | `svc/builder/templates/base.html` |
| **Regions** | the masthead (`Header`, `MinimalHeader`) and the close (`Footer`). (The *body* region is the ordered section list — not a class) | `svc/builder/regions.py` |
| **Containers** | layout geometry only: `FullWidth`, `TwoColumn`, `ThreeColumn` | `svc/builder/containers.py` |
| **Components** | content: `CardGroup`, `DataTable`, `ChartBlock`, `ImageBlock`, `TextBlock`, `NumberedList`, `AuthorBlock`, `ContactBlock` | `svc/builder/components.py` |

A container holds components, renders each, and embeds the fragments into its own `<tr>`
block sized to the 680px outer table. Each region renders into its slot — both the header
and the footer fill one slot each — and `Email` drops all of it into the skeleton.

**Facts about the email live on `EmailMetadata`; how a region presents them lives on the
region.** The firm name, campaign name, dates and outbound URLs are handed *down* at render
time — a region presents them, it cannot contradict them. Swapping the header region is one
argument, not a template fork:

```python
from svc.builder import EmailBuilder, MinimalHeader

(EmailBuilder()
    .metadata({...})
    .header(MinimalHeader(logo_url=logo))
    .section(...))
```

The footer's copyright, Unsubscribe and View-in-browser line always renders. The
`Footer.disclaimer` field is optional free-form HTML for legal copy. For a contact
call-to-action, add a `ContactBlock` body section instead of putting it in the footer:

```python
from svc.builder import EmailBuilder, FullWidth, ContactBlock

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

## Colour

Every colour and shadow comes from one validated `Theme`, chosen with one metadata field:

```python
from svc.builder import DEFAULT_THEME, EmailBuilder

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

Three curated presets. `compact` fits the same letter into about 17% less height, `spacious`
gives it 23% more, and every font size, line-height, padding, gutter and column width follows
— including the mobile `@media` overrides, so an email is never desktop-themed and
mobile-standard. Column widths are computed from the frame rather than hardcoded, so they
still fill the content width to the pixel at any density.

Unlike `theme`, `size_theme` takes a preset name only. Density interacts with the clipping
limit, Outlook's Word engine and the mobile collapse all at once, so a scheme nobody has
rendered in a real client is a compatibility claim nobody has tested. There is no per-email
or per-component size override: you pick a theme, never a px.

## What it enforces

These are the failures that are invisible until a reader reports them, so they are checked
rather than documented:

- **The 102 KB Gmail clipping limit.** `render()` raises `SizeError` above it and warns above
  90 KB. Both thresholds are configurable, so a non-Gmail channel can raise them deliberately
  rather than by commenting out the check.
- **Validation at construction, not at render.** Models and components raise `ValidationError`
  from `__init__`; by the time you call `.render()`, the data shape is already known good.
- **Missing template variables fail loudly** — Jinja2 runs under `StrictUndefined`.
- **URL schemes.** `http`, `https`, `mailto`, `cid` and relative URLs are allowed;
  `javascript:`, `data:`, `vbscript:` and `file:` are rejected at construction.
- **Colors are `#RRGGBB`**, checked in Python and again in the templates.
- **Alt text is required** on every image — it is what the reader sees whenever images are
  blocked, which for Outlook desktop is the default state.

**Autoescape is off, and escaping is split by field kind.** HTML email needs raw output, so
it is explicit: plain-text fields (titles, KPI labels, table cells, author names) are escaped
by the builder — pass them as raw text, since pre-escaping now double-escapes. HTML fields
(`TextBlock.content`, `NumberedItem.body`, the metadata disclaimers) are emitted raw, so
escaping untrusted text in those is the caller's job — use
`from svc.builder.filters import escape_html`. Attributes are always escaped.

## Images

An image carries two independent facts: where the bytes live, and how they reach the reader.

```python
from svc.builder.images import EmailImage

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
from svc.config import Config, get_config, set_config, config_override

get_config().inline_image_limit_kb               # what is actually in force
set_config(Config(inline_image_limit_kb=64))     # install process-wide
set_config(Config.from_env())                    # or read PYHERMES_*
with config_override(retry_max_attempts=1):      # scoped, restores on exit
    ...
```

The line it draws is between **a judgment call and a fact about the world**. The inline-image
cap, the retry ladder and the request timeout were picked by someone, and a picked number you
cannot revisit without editing the library is a bad default wearing a constant's clothes.
Graph's `202 Accepted`, the transient status families and the Content-ID character set
describe what a provider *does* — changing them would not tune behaviour, it would make the
code wrong about its environment, so they stay literals.

Nothing reads the environment on import; `from_env()` is explicit. Consumers call
`get_config()` at use time, so an override installed after import is still seen. An explicit
argument always beats the config.

## Development

```bash
pytest                                    # 714 tests: validation, error paths, size limits
ruff check . && ruff format --check .
python -m mypy                            # config in pyproject: files = ["svc", "qa"]
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

**In:** composing the HTML, assembling the MIME message, transmitting it through Gmail or
Microsoft Graph.

**Out, deliberately:** OAuth flows (the caller's, by design); campaign management — no
scheduling, recipient lists, batching or send-time analytics; open tracking and link
rewriting. A plain-text alternative is not implemented yet — the `multipart/alternative` slot
is left open for it in [#53](https://github.com/RorySullivan1/pyHermes/issues/53).

## Layout

```
svc/
├── config.py     the tunable numbers, in one frozen dataclass
├── builder/      templates, containers, components, models, images
├── delivery/     transport-neutral MIME assembly + shared retry policy
├── gmail/        Gmail send adapter
└── outlook/      Outlook send adapter over Microsoft Graph
tests/            pytest suite
```

Design rationale, the reasoning behind each constraint, and the decisions recorded as
non-features live in [CLAUDE.md](CLAUDE.md). Open work is tracked in
[GitHub issues](https://github.com/RorySullivan1/pyHermes/issues), organised as epics.
