# context/

Reference docs Claude can deep-read when a task needs them, so the main session
stays lean — Claude only opens what's relevant.

## When a skill and a brief cover the same ground, the skill wins

**Project-instruction briefs** (flat `*.md` here) are whole-stack operating
prompts; **skills** in `../skills/` are task-scoped. That distinction is real, but
it does not license the same guidance in both places — and left unstated it
produces exactly that. Two rules settle it:

- **A skill is loaded by its own description when the task matches; a brief is
  loaded only if something points at it.** Reachability, not scope, is what makes
  a home canonical. Where both cover a topic, **the skill is canonical** and the
  brief must not restate it.
- **A brief earns its place only by what no skill carries** — a whole-stack stance
  a task-scoped skill cannot express — and it must be reachable: referenced from
  the project's `CLAUDE.md`, or it is dead weight. A brief nothing points at is
  not a fallback; it is a second copy that cannot be corrected because nobody
  reads it.

This tier is empty today. `python-project-instructions.md` was removed in #145
after measurement: 71% of its substantive lines echoed `python-development`,
`python-review`, `python-deployment` or `coding-standards` outright, every
remaining line was carried by one of them, and nothing referenced the file — this
README's own claim that `CLAUDE.md` pointed here was false. Its testing section
was a strict subset of the skill's, which is the shape to expect: the unreachable
copy is also the stale one.

**Reference notes** (`notes/*.md` + auto-generated `INDEX.md`) are small, declarative,
   read-on-demand reference cards (a concept, an external-system fact, a schema, a system
   map). `INDEX.md` is the always-loaded catalog (surfaced at SessionStart); each note is
   read only when its topic is relevant. The `knowledge-router` skill decides what earns a
   note, and its `context.py` engine creates notes and regenerates the catalog so it can't
   drift. Run `python ../skills/knowledge-router/scripts/context.py list` to see them.

Reference notes are catalogued automatically in `INDEX.md` (created on demand by
`knowledge-router`) — not listed here.
