# `.claude/` — project infrastructure

This directory holds the typed building blocks Claude Code uses for a project.
Each subdirectory is a distinct *layer* with a distinct job. The layers compose.

> These assets were curated from the [`claudeBrain`](https://github.com/RorySullivan1/claudeBrain)
> factory and adapted for pyHermes (a Python + Jinja2 HTML-email builder). Only the
> layers useful to this project were brought in; the factory's authoring meta-toolkit
> and unrelated stacks (VBA/VSTO/PowerApps) were deliberately left out.

## The composability stack

```
hooks      ← enforcement, underneath everything (Claude cannot skip these)
─────────────────────────────────────────────────────────────────────────
workflows  ▸  commands  ▸  agents  ▸  skills
(orchestrate)  (one-shot)   (isolated)  (expertise)
```

- **hooks/** — Deterministic shell scripts run by the harness on lifecycle events
  (`PreToolUse`, `PostToolUse`, `SessionStart`, …). They are the enforcement layer
  *underneath* the prompt stack — the model cannot choose to skip them. Use for
  anything that must *always* happen: formatting, branch guards, write protection,
  cache warming. Configured in `settings.json`.
- **workflows/** — Multi-step autonomous orchestrations. Claude executes a scripted
  sequence that can loop, branch, and spawn agents. Each is a markdown file.
- **commands/** — Single-shot, stateless prompt templates — saved prompts you'd
  otherwise retype. One file per command (`/<name>`).
- **agents/** — Isolated subagents spawned with clean context. They do focused work
  and return only a summary, so they don't bleed context into the main session.
- **skills/** — Domain-expertise bundles that tell Claude *how to think and behave*
  for a task type. Applied within a session or an agent's context. One folder per
  skill containing `SKILL.md`; the folder name equals the skill's `name:` frontmatter.

## Supporting files

- **context/** — Reference docs (architecture notes, schemas, stack instructions).
  `CLAUDE.md` points here; Claude deep-reads only what's relevant to the task. See
  `context/README.md` for the manifest.
- **settings.json** — Permissions, model, and hook configuration.
- **memory/** — Cross-session state via the `session-memory` skill: an auto-loaded
  `INDEX.md` plus append-only `sessions/*.md` logs (loaded/persisted by the lifecycle
  hooks in `settings.json`). Replaces a static `DECISIONS.md` log.
- **CATALOG.md** — A generated, **on-demand** inventory of every skill, agent, command, and
  workflow with a one-line purpose. `CLAUDE.md` references it by path instead of enumerating
  assets (skills/agents already auto-load by their `description:`). Produced by
  `hooks/catalog.py` (a mechanical generator), kept fresh by a `PostToolUse` auto-rebuild +
  a `SessionStart` staleness warning, and regenerated with the `/reindex` command.

## Status in this project

Curated for pyHermes (a Python + Jinja2 HTML-email builder for financial newsletters):

- **skills/** — the **Python** family (`python-development` / `-review` / `-maintenance`
  / `-deployment`) + `coding-standards`; the **GitHub** family (`github-pull-requests`,
  `-issues`, `-comments`, `-releases`); operational skills (`session-memory`,
  `agent-finder`, `knowledge-router`, `token-optimizer`, `skill-distiller`,
  `claim-grounding`); and a **financial / content-design** set (`quantitative-finance`,
  `financial-timeseries-analysis`, `quant-code-review`, `backtesting-validation`,
  `branding`, `presentation-design`, `report-builder`).
- **agents/** — `python-developer` (adapted to `svc/`), `software-architect`,
  `goal-auditor`, `github-operator`, the context-economy `token-manager`, and the
  (speculative, for a future analytics layer) `finance-quantitative-developer`.
- **commands/** — `/version-set`, `/version-ship`, `/reindex`.
- **workflows/** — `ship-version`, `verify-claims`, `change-end-to-end`.
- **hooks/** — memory + context lifecycle hooks, context-economy guards, git guards,
  and the `build-hooks.py` / `catalog.py` generators. **Dormant until `settings.json`
  wires them** (see the note there) — no hook runs without that wiring.
- **context/** — `python-project-instructions.md` brief + the reference-notes tier;
  **memory/** is scaffolded and ready.

Not brought in: the factory's asset-authoring meta-toolkit (`skill-authoring`,
`agent-authoring`, …), the `.meta/roadmap` development-mapping system, and all
VBA/VSTO/PowerApps/SharePoint/Power-Platform assets.

For the full, current list of any layer, read **`CATALOG.md`** (regenerate with `/reindex`)
— this README describes the layers; the catalog enumerates them.
