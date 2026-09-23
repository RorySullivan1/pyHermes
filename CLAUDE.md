# CLAUDE.md

Guidance for Claude Code when working in this repository. This file is a **router**: it
holds what is true for every task, and points at the topic file for everything else.

## What this project is

pyHermes builds **documents for academic / financial research** from one section tree, and
renders each onto the medium it will be read on. Python composes Jinja2 templates into a
single inline-CSS document; the hard parts are per-medium — surviving Gmail's clipping limit
and Outlook's Word engine for an email, laying out sheets and margin boxes for a page.

**Scope = build, then send *or* print.** `svc/builder/` is the shared kit — the section tree,
the three design axes, the two projections. A **medium** decides the rest: `svc/email/` the
four-slot skeleton and the 102 KB check, `svc/document/` the paged one with its cover,
contents sheet, running boxes and page breaks, `svc/brochure/` a sheet folded into panels,
imposed for the press with bleed and crop marks. The apparatus a reader navigates by —
exhibit numbers, footnotes, contents, cross-references — is numbered in Python, once, so
every projection agrees; only the page number is the print engine's. Three exporters sit
on one contract — `svc/delivery/` + `svc/gmail/` + `svc/outlook/` for MIME, `svc/pdf/` for
PDF. Each owns its wire format and **never** authentication, so the core still depends on
Jinja2 alone. Figures arrive as numbers:
`svc/builder/formats.py` formats them and `svc/data/` adapts a DataFrame or a Figure, each
adapter behind an optional extra.

## Commands

```bash
pip install -e ".[dev]"       # editable install + pytest/ruff/mypy (see Gotchas)
pytest                        # unit suite — validation, error paths, size limits
ruff check . && ruff format --check .
mypy                          # config in pyproject: files = ["svc", "qa"]

pip install -e ".[qa]"        # optional: Playwright + pypdfium2 for screenshots
pip install -e ".[pdf]"       # optional: WeasyPrint, for PDF (needs Pango/Cairo)
pip install -e ".[data]"      # optional: pandas, for DataFrame -> DataTable
pip install -e ".[charts]"    # optional: matplotlib, for Figure -> chart image
python -m qa.screenshots      # gallery → output/screenshots/ (gitignored)
pytest --update-goldens       # the ONLY way to regenerate a golden (#58)
python -m qa.preview kitchen_sink --lint --screenshot --open   # an email
python -m qa.preview a4_portrait --lint --screenshot --open    # a paged document + its PDF
python -m qa.preview tri_fold_letter --lint --screenshot       # a brochure, one image a side
```

CI runs the first four on every PR, plus `screenshots`, `pdf`, `data` and `wheel` jobs. `[dev]`
alone must stay free of every extra: each extra's tests skip rather than fail, and that is what
proves each is optional.

**To eyeball a change, run `preview`.** A screenshot is the only thing that catches a
layout regression; see standing rule 3.

## Where the detail lives

Topic files are **path-scoped rules** in `.claude/rules/`. Each declares the paths it
applies to and loads **only when a matching file is read** — so a session that never opens
`qa/` never pays for the QA harness. Open one directly when you want it before touching code.

| File | Loads when you touch | Holds |
|---|---|---|
| `working-in-the-code.md` | any of `svc/`, `qa/`, `tests/` | The annotated repo map, and the ten standing rules in full |
| `builder-architecture.md` | `svc/builder/**` | The four-layer model, the facts-flow-down ownership rule, the public API, images and the asset manifest, parameters, validation, exceptions, the hard constraints in full |
| `design-axes.md` | theming / sizing / typography / enums / containers / `templates/**` | Colour, density, typeface and alignment — the three themes plus the axis that deliberately is not one |
| `data-table.md` | `models.py`, `components.py`, `templates/analysis/**` | Columns, cells, row kinds, caption and row headers |
| `disclosure.md` | `components.py`, `templates/analysis/**` + `media/**`, the shared partial | An exhibit's two kinds of fine print: attribution, and the compliance copy beneath it |
| `data-layer.md` | `formats.py`, `svc/data/**` | Figures as numbers: the formatters, the two adapters, why the dependency runs one way |
| `plain-text.md` | `textgen.py`, `email.py` | The second projection of the section tree |
| `apparatus.md` | `apparatus.py`, `document.py`, the notes / contents / running-box templates | Exhibit numbers, footnotes, contents, cross-references, the running section — Python numbers all but the page |
| `media.md` | `svc/email/`, `svc/document/`, `svc/pdf/`, `medium.py`, `document.py`, `templates/document/**` | The medium model, the page, the template fork rule, each medium's regions, the exporter's resource policy |
| `brochure.md` | `svc/brochure/**`, `templates/brochure/**`, the editorial partial | Folds, the panel, imposition, bleed and marks, the editorial primitives and each one's email degradation |
| `delivery.md` | `svc/delivery/`, `svc/gmail/`, `svc/outlook/` | MIME assembly, the adapter contract, the deliberate non-features |
| `qa-harness.md` | `qa/**`, `tests/**` | Gallery, goldens, screenshots, lint, the preview CLI |
| `config.md` | `svc/config.py` | The one frozen dataclass of tunable numbers |

Each also carries the post-mortem of the epic that built its area — the reasoning is what
stops a settled question being reopened, and it belongs beside the code it settled.

## Hard constraints

The rules themselves. `builder-architecture.md` carries why each exists.

- **102 KB Gmail clipping limit — the *email medium's* constraint.**
  `svc.email.validate_gmail_size` raises `SizeError` above it and warns above 90 KB, and the
  email medium lists it in `constraints`. The most important runtime check there is; never
  disable it without confirming a non-Gmail channel. Both thresholds come from `Config` at
  check time. A paged document runs no size constraint, because nothing clips a PDF.
- **Jinja2 `StrictUndefined`.** A missing template variable raises. A new template var needs
  a matching key in the component's `context()`.
- **Autoescape is OFF, and escaping is split by field kind.** Plain-text fields are escaped
  by the templates — pass them raw. Five HTML fields are emitted raw and escaping them is
  the *caller's* job: `TextBlock.content`, `Card.body`, `NumberedItem.body`,
  `Footer.disclaimer`, `header_disclaimer`. Attributes are always escaped. **The set is
  closed at five** — `disclosure` (#154) is the sixth candidate and is deliberately plain
  text, because widening later is additive and narrowing is not (`disclosure.md`).
- **A raw-HTML field is emitted inside a `div`, never a `p`.** A `p` is auto-closed the
  moment caller markup opens, and the copy escapes the styling it should inherit (#130).
- **URL schemes are validated** at construction: `http`, `https`, `mailto`, `cid` and
  relative only. `javascript:`, `data:`, `vbscript:`, `file:` raise `ValidationError`.
- **The PDF exporter makes no network requests.** It serves `cid:` from the document's own
  manifest and refuses every other URL by name, so a hosted image is not slow — it is a
  `PdfError`. A printable document carries its own images.
- **A brochure is checked for print at construction.** A panel inset inside the fold's safe
  distance raises; an image below half its 300 dpi pixel count raises, and below the full
  count warns. Its PDF is RGB, by decision (`brochure.md`).
- **Colours are `#RRGGBB`**, validated at construction and again in the templates.
- **Validation runs at construction time, never at render time.** By the time `.render()`
  is called the data shape is already known good. Preserve this when adding a component.
  The one exception is `Document.validate()`'s dangling-reference check: a `#fragment` may name
  a section not yet added, so it runs before any template loads (`apparatus.md`).

## Standing rules

Each has teeth — a named test, not a convention to remember. Full reasoning, and the test
that enforces each, is in `working-in-the-code.md`.

1. **A new component joins `kitchen_sink()`.** So does a new `EmailMetadata` field, at a
   **non-default** value — a field at its default is one the golden cannot pin.
2. **A golden diff in a PR is a claim that the visual change is intended.**
   `pytest --update-goldens` is the only regeneration path; a missing golden fails rather
   than being created. Never regenerate to silence a failure.
3. **Screenshots approximate Gmail-in-a-browser; the lint pass owns Outlook; the PDF
   rasterisation owns pagination.** "The screenshot looks fine" never closes a
   compatibility question, a clean lint never says the layout reads well, and a browser
   renders a paged document as one long scroll — so a paged fixture is photographed from
   its PDF, one image per sheet. **A byte-verified diff is not a verified render** — the
   alignment epic shipped three defects no golden could see, and #164 two more.
4. **A new template takes its colours from the `theme` namespace.** A hardcoded hex or
   `rgba()` is a bug. No documented exceptions.
5. **A new template takes its sizes from the `size` namespace.** Four named structural
   exceptions, each of which a test requires to stay in use.
6. **A new template takes its faces from the `font` namespace.** No exception list. The
   watch-site is the `[if mso]` block.
7. **A region or component that carries images must declare them** in `IMAGE_FIELDS` or by
   overriding `images()`, or the bytes never reach `Email.assets()`.
8. **A new template's tables declare what kind they are** — `role="presentation"` for
   layout, none plus `scope` for data. Enforced both ways by the `table-role` lint rule.
9. **A new property on a component or container joins the gallery at a non-default value.**
10. **A new component must implement `text()`**, and absence fails loudly — the mirror of
    rule 7 with the opposite default.
11. **Prose is bounded, and the bound is checked.** A file states its purpose; a class may
    argue its design; a function states its contract; a comment marks a trap. The check
    ships with a baseline that **may only shrink**, and a decision is *moved* to the docs
    rather than deleted.

## Prose discipline

Commentary is budgeted: caps in `.claude/prose-budget.json`, the measurer in
`.claude/hooks/prose_budget.py`, the gate in `tests/test_prose_budget.py`, and today's
exemptions in `qa/prose_baseline.json`. **The baseline may only shrink.** The standard
itself — file purpose, verbose class, limited function, inline-for-traps — is in the
`coding-standards` skill; where displaced reasoning goes is `knowledge-router`'s call.

## Gotchas

- **Wheel installs work** (since #10). `templates/` lives inside the package at
  `svc/builder/templates/` and ships with the wheel; the engine resolves it via
  `importlib.resources`, so an editable install and a site-packages install agree. A CI job
  builds the wheel and renders an email from a clean venv to keep it that way.
- **Import path.** `from svc.builder import …` / `from svc.builder.models import …`.
  `svc/__init__.py` re-exports nothing, and there is no `svc.models`.
- **The skeleton is the medium's, and the email one is `templates/base.html`.** The engine
  loads it through a `ChoiceLoader`: each of the medium's `template_search_path` directories
  first, that root last — so a medium can fork one template without forking the tree, and a
  declared directory that does not exist is the normal, unforked case.

## Working in this repo — the `.claude/` tooling

A curated `.claude/` asset library, installed from the `claudeBrain` factory. Full
inventory: [.claude/CATALOG.md](.claude/CATALOG.md) (regenerate with `/reindex`). Reach for
these rather than improvising:

- **Python work** → `python-development` / `-review` / `-maintenance` / `-deployment` plus
  `coding-standards`. For isolated, summary-returning implementation, the `python-developer`
  agent is already scoped to `svc/` and this repo's `pytest`.
- **GitHub** → the `github-*` skills, or the `github-operator` agent.
- **Verbose output** (test runs, large files, doc fetches) → the `token-manager` agent.
- **Shipping** → `/version-set` then `/version-ship`. **Acceptance** → the `goal-auditor`
  agent. **Fact-checking a claim** → `claim-grounding`.
- **Cross-session memory is active.** A SessionStart hook loads
  [.claude/memory/INDEX.md](.claude/memory/INDEX.md) — read it before starting.
- **Hooks are active and non-mutating.** To change one, edit the `*.json` **fragment** in
  `.claude/hooks/` then run `python .claude/hooks/build-hooks.py` — never hand-edit the
  generated `hooks` block in `settings.json`.

## Open work and state

- Tracked in [GitHub issues](https://github.com/RorySullivan1/pyHermes/issues), as epics
  with sub-issues. Complete: **#157** (rescope to media), **#153** (per-exhibit disclosure),
  **#169** (pagination hardening), **#170** (the data layer, #177–#180), **#171** (document
  apparatus, #181–#185) and **#172** (the brochure medium, #186–#189). Open: **#150** (banner
  VML `src`, needs a real Outlook host).
- Current state, decisions and open threads:
  [.claude/memory/INDEX.md](.claude/memory/INDEX.md).
- [README.md](README.md) is the human-facing entry point (what it is, install, build, send or
  print, the constraints it enforces). The router and its rules files stay the *rationale*:
  the README says what the library does, these say why each constraint exists. Keep the split.
