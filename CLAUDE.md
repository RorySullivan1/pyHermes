# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

The project is declared in [pyproject.toml](pyproject.toml) as an installable package (`pyhermes`). Python `>=3.11`. The only runtime dependency is `jinja2` (pinned `>=3.1,<4`); everything else is standard library.

Install once in editable mode and `svc` becomes importable from anywhere — no `sys.path` hack required:

```bash
pip install -e .
# or, with uv:
uv pip install -e .
```

The `[build-system]` block uses `hatchling`. The wheel target is `packages = ["svc"]`. `templates/` is **not** packaged into the wheel — the engine resolves it via `Path(__file__).resolve().parent.parent.parent / "templates"`, which works for editable installs (where `__file__` lives in the source tree) but would break for non-editable installs from a wheel. Stick with editable for local development.

## Running and testing

There is no test framework configured. The de facto integration test is:

```bash
python test_builder.py
```

This regenerates `weekly_market_wrap_v2.html` end-to-end through the full builder pipeline (metadata → containers → components → skeleton → size check). Open the output in a browser to verify visually. The script also prints the rendered email size and warns if it exceeds 90 KB.

## Architecture

The repo is an HTML-email-builder for academic financial newsletters. There are **two parallel implementations** of the same core idea, and they are not interchangeable:

- **`svc/builder/`** — the current object-oriented API (use this for new work). Public surface re-exported from `svc/builder/__init__.py`.
- **`svc/assembler.py`** — a legacy flat string-replace assembler kept around for reference. Marked as "Legacy flat assembler" in [`svc/__init__.py`](svc/__init__.py). Do not extend it; port to the OO builder instead.

### The three-layer composition model (svc/builder)

Every email is `skeleton ← containers ← components`:

1. **Skeleton** — [templates/base.html](templates/base.html). The full HTML page (head, header, footer, palette comment) with one variable hole: `{{ sections_html }}`. Rendered last by [Email.render()](svc/builder/email.py).
2. **Containers** — layout geometry only. Live in [templates/common/containers/](templates/common/containers/) (`full-width`, `highlight`, `col-50-50`, `col-30-70`, `col-70-30`). Each container produces a `<tr>` block sized to the 680px outer email table. Python wrappers in [svc/builder/containers.py](svc/builder/containers.py).
3. **Components** — content blocks (KPI strip, data table, chart, text block, numbered list, author block). Templates in [templates/analysis/](templates/analysis/) and [templates/text/](templates/text/). Python wrappers in [svc/builder/components.py](svc/builder/components.py).

A `Container` holds one or more `Component` instances, calls `component.render(engine)` to get an HTML fragment, and embeds the fragment into its own template. The `Email` then concatenates all section HTML and injects it into the skeleton's `sections_html` slot. Any new content type means: new template file + new `Component` subclass that sets `template_path` and implements `context()`.

`templates/common/skeletons/base.html` exists but is **not** the one rendered — the engine loads `"base.html"` from the templates root (FileSystemLoader root is `templates/`).

### Hard constraints baked into the engine

- **102 KB Gmail clipping limit** — [Email._validate_size()](svc/builder/email.py) raises `SizeError` if the rendered HTML exceeds 102 KB and prints a warning above 90 KB. This is the single most important runtime check; never disable it without confirming the email is being sent through a non-Gmail channel.
- **Jinja2 `StrictUndefined`** — [TemplateEngine](svc/builder/engine.py) fails fast on missing template variables instead of rendering empty strings. New template variables require a matching key in the component's `context()` dict, or the render will raise.
- **Autoescape is OFF** — HTML emails need raw output. Any user-supplied text in component data must be pre-escaped by the caller (see `&amp;` in [test_builder.py](test_builder.py) for the convention).
- **Hex-color enforcement** — colors use the `#RRGGBB` form everywhere. Validated by [models._validate_color()](svc/builder/models.py) at construction time and by the `validate_hex_color` Jinja filter ([svc/builder/filters.py](svc/builder/filters.py)) inside templates. `DataTable` cells get colored via the `TableRow.colors` parallel list — index-aligned with `cells`.

### Validation philosophy

Validation runs at **construction time**, not at render time. Models (`KpiItem`, `TableRow`, `NumberedItem`, `EmailMetadata`) and components both raise `ValidationError` from their constructors. By the time you call `.render()`, the data shape is already known good. Preserve this pattern when adding components — validate in `__init__`, not in `context()`.

### Builder fluent API

[EmailBuilder](svc/builder/email.py) is a thin fluent wrapper: `metadata()` initializes the underlying `Email`, `section()` appends a container, `build()`/`render()`/`save()` are terminal. `metadata()` must be called before `section()` or you get a `RuntimeError`. The non-fluent `Email` class works identically and is fine to use directly.

### Exception hierarchy

All errors inherit from [EmailBuilderError](svc/builder/exceptions.py): `TemplateError` (Jinja loading/rendering), `ValidationError` (data shape), `SizeError` (102 KB limit). Catch the base class for "anything the builder rejected."

## Open work

[dev/TODO.md](dev/TODO.md) tracks active fixes — currently a section-title padding bug in `full-width.html` and `highlight.html` (titles appear clipped at the top because both title and content `<td>` rows use 2px top padding).
