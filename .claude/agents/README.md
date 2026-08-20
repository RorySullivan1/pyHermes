# agents/

**Isolated parallel workers.** Subagents spawned with a clean context that do
focused work and return only a summary — so they don't bleed context into the main
session. Good for noisy, error-prone, or narrowly-scoped jobs.

## Format

- One markdown file per agent: `<name>.md`.
- Frontmatter defines the agent: `name`, `description` (when to use it), and
  optionally `tools` (a restricted allowlist) and `model`.
- The body is the agent's system prompt — its focused mandate.

## Typical uses

- A data/fetcher agent that owns one external API and its quirks.
- An auth/worker agent that isolates token errors from the main session.
- A runner agent that executes a task and returns just the result summary.

## Status

**Defined:**
- `finance-quantitative-developer` — a senior Python quant engineer for the `tools/`
  analytics layer (pricing, risk, signals, time-series) that writes and verifies
  quantitative code.
- `data-analyst` — the **objective** analysis brain (read-only, `plan`): frames the
  question, plans exploration, specifies purpose-driven visualizations, and reasons to
  defensible conclusions with their uncertainty — deliberately language/tool-agnostic. It
  produces the objective spec and defers the subjective *how* (language, library, code) to
  a developer agent or a language skill. The conceptual counterpart to a hands-on executor
  like `finance-quantitative-developer`.
- `software-architect` — the **objective** structure brain (read-only, `plan`): designs a
  project's architecture to fit its objective and sets the conventions — module/component
  boundaries, where each kind of element lives, naming, and file organization. Stack-
  agnostic: it produces the blueprint + conventions and defers the implementation (the
  code, the framework idiom) to a developer agent or a language skill. The structural
  sibling of `data-analyst` in the family of objective, defer-the-*how* agents.
- `presentation-architect` — the **objective** presentation-flow brain (read-only, `plan`):
  designs how a communication artifact is structured to land its message — audience + goal,
  the narrative arc, the message hierarchy, what each unit (slide/panel/section) does and in
  what order, the reader's path, and CTA placement. Format-agnostic across decks, brochures,
  one-pagers, and reports: it produces the flow blueprint + per-unit content spec and defers
  the subjective *how* (visual design, final copy, the authoring tool) to a design/content
  executor or skill. The communication-artifact sibling of `data-analyst` and
  `software-architect` in the family of objective, defer-the-*how* agents.
- `token-manager` — a context-economy worker: runs verbose/high-volume tasks (test suites,
  log processing, large-file analysis, fetches) in isolation and returns only a capped
  summary. The delegation target of the `token-optimizer` skill.

Add more with a `<name>.md` + frontmatter.
