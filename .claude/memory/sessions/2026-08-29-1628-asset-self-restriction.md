# 2026-08-29 16:28 — asset-self-restriction

**Goal:** Epic #140 — bound the prose the `.claude/` library was teaching, portably
enough that claudeBrain can repackage it.

## What shipped

- **#141** — the prose standard in `coding-standards`, scope by scope, with no line
  counts (they belong in a project's check, not a cross-project standard). Paid for by
  removing a triplication: the skill stated its own scope three times.
- **#142** — `hooks/prose_budget.py` in the wired-and-unused `Edit|Write|MultiEdit`
  slot. Two entry points over one measurer: an advisory hook, and `scan_source`/
  `scan_tree` for a CI gate.
- **#135** — this repo's caps (16/28/18/4), 110 baselined locations, the suite gate.
- **#143** — `memory.py` enforces `BUDGETS`; `INDEX.md` 256 → 41 lines.
- **#144** — the router gains the code as a destination, a first anti-destination, the
  reach discriminator and the two-homes rule.
- **#145** — deleted the unreachable `python-project-instructions.md`; stated the
  skill-wins precedence rule; wrote the factory hand-off in `.claude/README.md`.

## Findings worth keeping

- **A line cap on unbounded lines is not a cap.** `INDEX.md` obeyed "≤ ~80 lines" at 256
  lines and ~22,900 tokens against a stated ~600. The width was the evasion. Fixed with a
  fourth number, `max_line_chars`, not a louder version of the three.
- **Reachability, not scope, makes a home canonical.** The brief lost to the skills
  because nothing loaded it — and `context/README.md`'s claim that `CLAUDE.md` pointed
  there was simply false. Its testing section was a strict subset of the skill's: the
  unreachable copy is also the stale one.
- **A guard verified only against correct code is not a guard.** `prose_budget.py` failed
  its own default by 7 lines on the first draft. `memory.py`'s SessionStart path crashed
  on an unreadable `INDEX.md` — pre-existing, and it would have taken the session's first
  turn with it.
- **Measure per-session cost, not repo lines.** +465 lines to `.claude/`, and every
  session is 215 lines cheaper: the growth never loads, the shrink always did.
- **Baseline keys must not be line numbers.** A docstring keyed by line moves whenever
  anything above it does, so an unrelated edit would fail the gate for a reason that has
  nothing to do with prose. Keyed by qualified name; proved stable under a line shift.

## Not done

#134 (the rewrite itself) is untouched: #136 splits CLAUDE.md, #137 stops shipping
comments in the email, #138/#139 rewrite `svc/` and `qa/` and empty the baseline.
