# CLAUDE.md

Guidance for Claude Code when working in this repository. This file is a **router**: it
holds what is true for every task, and points at the topic file for everything else.

## What this project is

pyHermes builds **HTML emails for academic / financial newsletters**. Python composes
Jinja2 templates into a single, inline-CSS HTML document engineered to survive email
clients (Gmail, Outlook) — the hard part is staying under Gmail's clipping limit while
keeping the layout table-based and portable.

**Scope today = build *and* send.** `svc/builder/` renders the HTML, projects the
`text/plain` part and declares the images; `svc/delivery/` assembles the
`multipart/alternative`; `svc/gmail/` + `svc/outlook/` transmit it. Adapters own their
provider's wire contract and **never** authentication, so pyHermes depends on nothing but
Jinja2.

## Commands

```bash
pip install -e ".[dev]"       # editable install + pytest/ruff/mypy (see Gotchas)
pytest                        # unit suite — validation, error paths, size limits
ruff check . && ruff format --check .
mypy                          # config in pyproject: files = ["svc", "qa"]

pip install -e ".[qa]"        # optional: adds Playwright for screenshots (#59)
python -m qa.screenshots      # gallery → output/screenshots/ (gitignored)
pytest --update-goldens       # the ONLY way to regenerate a golden (#58)
python -m qa.preview kitchen_sink --lint --screenshot --open   # the review loop (#61)
```

CI runs the first four on every PR, plus a `screenshots` job and a `wheel` job. `[dev]`
alone must stay browser-free: the screenshot tests skip rather than fail, and that is what
proves `[qa]` is optional.

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
| `plain-text.md` | `textgen.py`, `email.py` | The second projection of the section tree |
| `delivery.md` | `svc/delivery/`, `svc/gmail/`, `svc/outlook/` | MIME assembly, the adapter contract, the deliberate non-features |
| `qa-harness.md` | `qa/**`, `tests/**` | Gallery, goldens, screenshots, lint, the preview CLI |
| `config.md` | `svc/config.py` | The one frozen dataclass of tunable numbers |

Each also carries the post-mortem of the epic that built its area — the reasoning is what
stops a settled question being reopened, and it belongs beside the code it settled.

## Hard constraints

The rules themselves. `builder-architecture.md` carries why each exists.

- **102 KB Gmail clipping limit.** `Email._validate_size()` raises `SizeError` above it and
  warns above 90 KB. The single most important runtime check; never disable it without
  confirming a non-Gmail channel. Both thresholds come from `Config` at check time.
- **Jinja2 `StrictUndefined`.** A missing template variable raises. A new template var needs
  a matching key in the component's `context()`.
- **Autoescape is OFF, and escaping is split by field kind.** Plain-text fields are escaped
  by the templates — pass them raw. Five HTML fields are emitted raw and escaping them is
  the *caller's* job: `TextBlock.content`, `Card.body`, `NumberedItem.body`,
  `Footer.disclaimer`, `header_disclaimer`. Attributes are always escaped.
- **A raw-HTML field is emitted inside a `div`, never a `p`.** A `p` is auto-closed the
  moment caller markup opens, and the copy escapes the styling it should inherit (#130).
- **URL schemes are validated** at construction: `http`, `https`, `mailto`, `cid` and
  relative only. `javascript:`, `data:`, `vbscript:`, `file:` raise `ValidationError`.
- **Colours are `#RRGGBB`**, validated at construction and again in the templates.
- **Validation runs at construction time, never at render time.** By the time `.render()`
  is called the data shape is already known good. Preserve this when adding a component.

## Standing rules

Each has teeth — a named test, not a convention to remember. Full reasoning, and the test
that enforces each, is in `working-in-the-code.md`.

1. **A new component joins `kitchen_sink()`.** So does a new `EmailMetadata` field, at a
   **non-default** value — a field at its default is one the golden cannot pin.
2. **A golden diff in a PR is a claim that the visual change is intended.**
   `pytest --update-goldens` is the only regeneration path; a missing golden fails rather
   than being created. Never regenerate to silence a failure.
3. **Screenshots approximate Gmail-in-a-browser; the lint pass owns Outlook.** "The
   screenshot looks fine" never closes a compatibility question, and a clean lint never
   says the layout reads well. **A byte-verified diff is not a verified render** — the
   alignment epic shipped three defects no golden could see.
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
- **The rendered skeleton is `svc/builder/templates/base.html`.** The engine's
  `FileSystemLoader` root is that directory and it loads `"base.html"`.

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
  with sub-issues. Every epic filed before 2026-08-29 is complete and every issue up to
  #133 is closed. Open: **#134** (prose discipline) and its remaining sub-issues.
- Current state, decisions and open threads:
  [.claude/memory/INDEX.md](.claude/memory/INDEX.md).
- [README.md](README.md) is the human-facing entry point (what it is, install, build, send,
  the constraints it enforces). The router and its rules files stay the *rationale*: the
  README says what the library does, these say why each constraint exists. Keep the split.
