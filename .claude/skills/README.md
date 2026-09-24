# skills/

**Triggered expertise.** A skill teaches Claude *how to think and behave* for a recurring
task type. The harness loads one automatically when its `description:` matches the work —
you don't invoke it by hand, and it applies **in** the main session rather than in an
isolated context (that's an agent).

## Format

- One folder per skill: `<name>/SKILL.md`. **The folder name must equal the `name:`
  frontmatter** — `asset_integrity.py` checks this on every commit.
- Frontmatter: `name` and `description`. The description is the whole trigger surface:
  lead with the use case, then name concrete phrases someone would actually say.
- The body is the behavior — procedures, judgment, do-this/not-that. Facts and specs
  belong in `../context/` instead; `context-vs-skill` owns that call.
- Bulky reference material goes in `<name>/references/` next to the `SKILL.md`, cited by
  path so it travels with the folder when the skill is copied elsewhere.

## What's here

This project's skills span its stacks (VSTO/.NET, Python, VBA, Power Platform, quant,
docs, branding → presentation) plus the cross-cutting operational set (`session-memory`,
`agent-finder`, `knowledge-router`, `token-optimizer`, `skill-distiller`,
`claim-grounding`, `coding-standards`).

Don't enumerate them here — `../CATALOG.md` is the generated, always-current inventory,
and the harness already surfaces each skill by its `description:`. Regenerate the catalog
with `/reindex`.

## Adding one

Scaffold with `/add-skill`, which applies the `skill-authoring` conventions. A skill that
asserts facts about an external system goes through the `verify-claims` truth gate before
it ships.
