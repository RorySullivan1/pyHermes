# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this project is

pyHermes builds **HTML emails for academic / financial newsletters**. Python composes
Jinja2 templates into a single, inline-CSS HTML document engineered to survive email
clients (Gmail, Outlook) — the hard part is staying under Gmail's clipping limit while
keeping the layout table-based and portable.

**Scope today = the *builder*.** Composing the HTML is the entire current product.
**Delivery is not built yet:** `svc/__init__.py` advertises `gmail/` and `outlook/`
subpackages, but they do not exist — treat them as planned, not present. Don't import them.

## Commands

```bash
pip install -e .              # editable install — makes `svc` importable everywhere (see Gotchas)
python test_builder.py        # the de facto integration test — see below
```

There is **no test framework** (no pytest/ruff/mypy). `test_builder.py` is the de facto
integration test: it rebuilds `weekly_market_wrap_v2.html` end-to-end through the full
pipeline (metadata → containers → components → skeleton → size check), prints the rendered
size, and warns above 90 KB. Run it after any change to `svc/builder/` or `templates/`,
then open the output in a browser to verify visually.

Slash commands (from the `.claude/` library): `/version-set`, `/version-ship`, `/reindex`.

## Directory map

```
svc/
├── builder/            ← current OO email builder (use this for new work)
│   ├── __init__.py     — public API surface (re-exports everything below)
│   ├── engine.py       — TemplateEngine (Jinja2, StrictUndefined, autoescape OFF)
│   ├── email.py        — Email + EmailBuilder (fluent), _validate_size()
│   ├── containers.py   — Container, FullWidth, Highlight, TwoColumn
│   ├── components.py   — Component, KpiStrip, DataTable, ChartBlock, TextBlock, NumberedList, AuthorBlock
│   ├── models.py       — EmailMetadata, KpiItem, TableRow, NumberedItem, SectionConfig
│   ├── filters.py      — Jinja filters (e.g. validate_hex_color)
│   └── exceptions.py   — EmailBuilderError hierarchy
└── assembler.py        ← legacy flat string-replace assembler (reference only — do NOT extend)
templates/
├── base.html                    — the rendered skeleton (one hole: {{ sections_html }})
├── common/containers/*.html     — layout geometry (full-width, highlight, col-50-50/30-70/70-30)
├── analysis/*.html              — data components (kpi-strip, data-table, chart-block)
└── text/*.html                  — text components (text-block, numbered-list, author-block)
test_builder.py         — integration test; regenerates weekly_market_wrap_v2.html
dev/TODO.md             — active fixes
.claude/                — curated tooling library (skills, agents, commands, hooks, memory)
```

## Architecture — `svc/builder`

There are **two parallel implementations** and they are not interchangeable:

- **`svc/builder/`** — the current object-oriented API. Use this for all new work. Public
  surface re-exported from [svc/builder/__init__.py](svc/builder/__init__.py).
- **`svc/assembler.py`** — a legacy flat string-replace assembler kept for reference.
  Do not extend it; port to the OO builder instead.

### The three-layer composition model

Every email is `skeleton ← containers ← components`:

1. **Skeleton** — [templates/base.html](templates/base.html). The full HTML page (head,
   header, footer, palette comment) with one variable hole: `{{ sections_html }}`. Rendered
   last by [Email.render()](svc/builder/email.py).
2. **Containers** — layout geometry only. In [templates/common/containers/](templates/common/containers/).
   Each produces a `<tr>` block sized to the 680px outer email table. Python wrappers in
   [svc/builder/containers.py](svc/builder/containers.py).
3. **Components** — content blocks. Templates in [templates/analysis/](templates/analysis/)
   and [templates/text/](templates/text/); Python wrappers in
   [svc/builder/components.py](svc/builder/components.py).

A `Container` holds one or more `Component`s, calls `component.render(engine)`, and embeds
the fragment into its own template. `Email` concatenates all section HTML into the skeleton's
`sections_html` slot. **Adding a content type = new template file + new `Component` subclass**
that sets `template_path` and implements `context()`.

### Public API (import from `svc.builder`)

```python
from svc.builder import EmailBuilder, Email, FullWidth, Highlight, TwoColumn, \
    KpiStrip, DataTable, ChartBlock, TextBlock, NumberedList, AuthorBlock
from svc.builder.models import KpiItem, TableRow, NumberedItem, EmailMetadata, SectionConfig
```

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
- **Autoescape is OFF** — HTML emails need raw output. Any user-supplied text in component
  data must be **pre-escaped by the caller** (see `&amp;` in [test_builder.py](test_builder.py)).
- **Hex-color enforcement** — colors use `#RRGGBB` everywhere. Validated by
  [models._validate_color()](svc/builder/models.py) at construction time and by the
  `validate_hex_color` filter ([svc/builder/filters.py](svc/builder/filters.py)) in templates.
  `DataTable` cell colors come from the `TableRow.colors` list — index-aligned with `cells`.

### Validation philosophy

Validation runs at **construction time**, not render time. Models (`KpiItem`, `TableRow`,
`NumberedItem`, `EmailMetadata`) and components raise `ValidationError` from their
`__init__`. By the time you call `.render()`, the data shape is already known good.
**Preserve this pattern** when adding components — validate in `__init__`, not in `context()`.

### Exceptions

All errors inherit from [EmailBuilderError](svc/builder/exceptions.py): `TemplateError`
(Jinja load/render), `ValidationError` (data shape), `SizeError` (102 KB limit). Catch the
base class for "anything the builder rejected."

## Gotchas

- **Editable install only.** `[build-system]` uses `hatchling`; the wheel target is
  `packages = ["svc"]`, but `templates/` is **not** packaged. The engine resolves templates
  via `Path(__file__).resolve().parent.parent.parent / "templates"`, which works for editable
  installs (source tree) but breaks for a wheel install. Stick with `pip install -e .`.
- **Import path.** Use `from svc.builder import …` / `from svc.builder.models import …`.
  The docstring in `svc/builder/__init__.py` showing `from svc import …` / `from svc.models
  import …` is **stale and wrong** — follow `test_builder.py`, not that docstring.
- **The rendered skeleton is `templates/base.html`.** `templates/common/skeletons/base.html`
  exists but is NOT rendered — the engine's `FileSystemLoader` root is `templates/` and it
  loads `"base.html"`.

## Working in this repo — the `.claude/` tooling

This repo carries a curated `.claude/` asset library (installed from the `claudeBrain`
factory). Full inventory: [.claude/CATALOG.md](.claude/CATALOG.md) (regenerate with `/reindex`).
Reach for these rather than improvising:

- **Python work** → the `python-development` / `-review` / `-maintenance` / `-deployment`
  skills + `coding-standards` auto-load. For isolated, summary-returning implementation,
  delegate to the **`python-developer`** agent (already scoped to `svc/` and this repo's
  `python test_builder.py` verification).
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

- [dev/TODO.md](dev/TODO.md) — active fixes. Currently a section-title/content padding bug in
  `full-width.html` and `highlight.html` (only partially applied) plus an invalid comma-form
  `padding` in `highlight.html`.
- Current project state and decisions: [.claude/memory/INDEX.md](.claude/memory/INDEX.md).
