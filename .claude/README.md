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
- **context/** — the reference-notes tier (the brief tier is empty; see its README for
  the skill-wins precedence rule); **memory/** is live.

Not brought in: the factory's asset-authoring meta-toolkit (`skill-authoring`,
`agent-authoring`, …), the `.meta/roadmap` development-mapping system, and all
VBA/VSTO/PowerApps/SharePoint/Power-Platform assets.

For the full, current list of any layer, read **`CATALOG.md`** (regenerate with `/reindex`)
— this README describes the layers; the catalog enumerates them.

## For the factory — what epic #140 produced that is portable

Everything below was built to be lifted upstream unchanged. It names no project, no
repo-specific path, and no threshold that only makes sense here.

| Take | What it is |
|---|---|
| `skills/coding-standards` — *How much, by scope* | The prose standard: file purpose, verbose class, limited function, inline-for-traps, and a higher bar for anything the build **emits** rather than compiles away. Deliberately carries no line counts — a cap that fits one codebase is wrong for the next |
| `hooks/prose_budget.py` + its fragment | The measurer. Two entry points over one implementation: an advisory `PostToolUse` note, and `scan_source`/`scan_tree` for a project's own CI gate. Opt in by presence, fail safe, never blocks, output capped. Python via `ast`/`tokenize`; `_SCANNERS` is the extension point |
| `skills/session-memory` — `BUDGETS` + `memory.py check` | A cap that enforces itself, plus the width cap without which a line count means nothing |
| `skills/knowledge-router` — *Choosing between homes* | The code as a fifth destination, the first anti-destination, the reach discriminator, and the two-homes rule |
| `context/README.md` — *the skill wins* | Precedence between a task-scoped skill and a whole-stack brief, and the reachability test that decides it |

**What stays here**: the caps in `.claude/prose-budget.json`, the 110 entries in
`qa/prose_baseline.json`, the compacted `memory/INDEX.md`. Numbers and content, not
mechanism.

**Four rules the epic held itself to**, and the reason each is worth inheriting:

- **A check ships green, with a named baseline that may only shrink.** One arriving red
  teaches everyone to switch it off.
- **Advisory beats blocking, for prose specifically.** The failure mode of a prose check
  is a false positive on correct code, and one that blocks is deleted within a week. That
  is *why* the measurer has a library half: an advisory hook cannot be a gate, so the gate
  needs the same code rather than a second copy.
- **Perturb every guard and watch it fail.** Three defects surfaced this way, two of them
  in guards that looked correct: `prose_budget.py` failed its own default by 7 lines on
  the first draft, and `memory.py`'s SessionStart path crashed on an unreadable index —
  a pre-existing bug that would have taken the session's first turn with it.
- **Measure per-session cost, not repo lines.** This epic added +465 lines to `.claude/`
  and made every session **215 lines cheaper**, because the growth is scripts and an
  archive that never load while the shrink is the always-loaded index. The three skills
  cost +76 more, and only when the matching task arrives.
