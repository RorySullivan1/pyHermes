# establish-verification

Answer, once per project and in writing, **who can confirm each surface worked** — the agent
with a command, or a human with a reason — and write the answers to
`../context/verification-surface.md`. Run it at adoption, and again whenever a surface is added
or its reach changes. Use it for "can we actually check this?", "set up verification for this
project", or "why is there a human gate here?".

**Inputs:** a project with its `CLAUDE.md` architecture and constraints filled in (the stacks
and the environment are what make a surface checkable or not).
**Output:** a populated `../context/verification-surface.md` — every surface on exactly one of
`agent-runnable` / `human-gated` / `unverified`, each with its command or its blocker — and a
`CLAUDE.md` that points at it.

## Steps

1. **Enumerate the surfaces.** Read `CLAUDE.md` § Architecture and § Constraints and walk the
   tree. A surface is anywhere work *lands and could be wrong*: each source tree, each build
   output, each deployed target, each external system the project writes into, and the
   `.claude/` assets themselves. Split by *property checked*, not by folder — "renders
   correctly" and "parses" are two surfaces even in one file. → hand-off: the surface list.

2. **Classify each surface — the loop.** For each surface, in order, produce **one** of:
   - a **command** you can paste into a shell here (test runner, validator, probe kit, script),
     or
   - a **blocker** naming what the agent cannot reach (an OS, a licence, a tenant, a signed
     cert, a physical device, an air gap) **plus the report contract** — what the human is asked
     to return, which under a one-way gap may be no more than "worked / didn't"
     (`../context/air-gap.md`), or
   - **neither**, which is `unverified` and needs an owner and a next action.

   Do not write a tier yet. → hand-off: a candidate row per surface.

3. **Prove each candidate check can fail.** For every row headed for `agent-runnable`, run the
   command against deliberately broken input and confirm it reports failure, then against the
   real input. This is `claim-grounding`'s controls discipline applied to the project's own
   checks, and it is the step that stops this workflow producing the very defect it exists to
   prevent. A command that passes on broken input is **not** a check — demote the row to
   `unverified` and say so. → hand-off: confirmed tiers + the observation date.

4. **Write the doc.** Fill `../context/verification-surface.md` — the tier rules live in that
   file's model section; this step only supplies rows (surface · check · tier · reason ·
   last-run). Replace the table wholesale; keep the model section as shipped. → hand-off: the
   written file.

5. **Wire it up.** Add the doc to `CLAUDE.md` § Reference Docs and to `../context/README.md`'s
   manifest so something points at it — an unreferenced brief is dead weight
   (`../context/README.md`). Then check the consumers: any workflow or agent that describes what
   it can verify should cite its row instead of re-deriving it. → hand-off: the reference edits.

6. **Record.** Log the run via **`session-memory`**, and record any surface that moved tier as a
   Decision with its reason. A surface that moved from `human-gated` to `agent-runnable` is a
   capability change worth keeping. → done.

## Control flow / stop conditions

- **Loop (step 2–3):** repeat per surface until the surface list is empty. Terminal state: every
  enumerated surface carries exactly one tier.
- **Bail (unclassifiable surface):** a surface where nobody present can say what would confirm it
  → **stop** and ask the project's owner. Do not guess a tier, and do not quietly drop the
  surface from the list — an omitted surface reads as "covered".
- **Demote (failed control):** step 3's command passes on broken input → the row becomes
  `unverified` with that finding as its reason. Never keep a check that cannot fail.
- **Bail (no `CLAUDE.md` architecture):** step 1 has nothing to enumerate from → **stop**; the
  project's contract has to name its stacks and constraints first. Never infer a stack from file
  extensions alone.
- **Re-run:** safe and expected. Re-running replaces the table and refreshes *last-run*; rows
  whose command still fails-on-broken keep their tier. Treat a row with no *last-run* as
  unproven, not as passing.
- **Success:** every surface has a tier, every `agent-runnable` row has a command observed to
  fail, and `CLAUDE.md` points at the doc → done; report the tier counts and any `unverified`
  rows as the standing debt.

## Invokes

- Skills: `claim-grounding` (the controls discipline behind step 3), `context-vs-skill` (if a
  classification turns out to be behavior that belongs in a skill, not a row), `session-memory`
  (step 6).
- Context: `../context/verification-surface.md` (the output and the tier rules),
  `../context/air-gap.md` (the worked `human-gated` case), `../context/README.md` (why step 5's
  reference matters).
- Hooks: `../hooks/asset_integrity.py` (itself one of the enumerated surfaces).
- State: `CLAUDE.md` (§ Architecture, § Constraints, § Reference Docs).
