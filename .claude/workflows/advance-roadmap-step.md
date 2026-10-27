# advance-roadmap-step

Drive **one version** of the development map from "planned" to a ready-to-ship PR — the
reiterative engine. Picks the cursor version off `.meta/roadmap/`, implements it, reviews
and re-works until it's clean, audits it against the version's acceptance, then **stops for
the user's approval before opening the PR** and stepping the cursor.

**Inputs:** a current `.meta/roadmap/` with a cursor (next `planned`/`in-progress` version)
and that version's card; the repo's developer agents, review skills, and `goal-auditor`.
**Output:** committed, reviewed, acceptance-passed work on the version branch, paused at an
approval gate; on approval, an open PR (via `ship-version`) and an advanced cursor.

## Steps

1. **Pick the step.** Read `.meta/roadmap/INDEX.md` and select the cursor version (the one
   marked in-progress, else the next `planned`). Read its card
   (`stages/NN-…/vX.Y.Z.md`) — its **Goals** and **Objectives / acceptance** are the
   contract for this step. If there is no cursor, **stop**: the map is complete or needs
   `/roadmap-set`.

2. **Graduate it into the cursor.** Run **`/version-set`** with the card's label, goals, and
   objectives so `.meta/version` becomes this version (status `in-progress`, branch
   `claude/<version>-<slug>`). Mark the INDEX row `in-progress`.

3. **Implement.** Delegate to the right executor for the work — pick via `agent-finder`
   (e.g. `@agent-vba-developer`, `@agent-finance-quantitative-developer`, or a
   `*-development` skill). Hand it the card's Goals as the spec and the acceptance as the
   bar. Keep the diff scoped to this version.

4. **Review & reiterate (the loop).** Run review on the commits — the `code-review` skill or
   the stack's `*-review` skill. Read `../context/verification-surface.md` first for which of
   this version's surfaces the loop can actually close: an `agent-runnable` row is a check to
   run, a `human-gated` row is a gate to raise at step 6, and neither may be reported as passed
   on the strength of the other. If it finds must-fix issues, send them back to the executor
   and re-review. **Repeat until review is clean** or no progress is being made (then stop
   and report the blocker). This loop is the "reiterative" core — don't skip it.

5. **Assess goal achievement.** Invoke **`@agent-goal-auditor`** with the version card and
   the diff. It judges whether the change actually satisfies the version's *acceptance
   criteria* (not line-level quality — that was step 4). If it returns gaps, route them back
   to step 3/4. Proceed only on a pass.

6. **Approval gate — STOP here.** Present a concise step summary: what was built, the review
   outcome, the goal-auditor verdict, and the proposed PR title/body. **Do not open the PR or
   bump anything yet.** Wait for the user's go-ahead. (This pause is intentional — opening a
   PR is outward-facing.)

7. **Ship (on approval).** Run **`/version-ship`** to branch/commit/push and open the PR from
   `.meta/version`; it writes the PR URL back. (If the project provides a `github-operator`
   agent, you may delegate the PR formatting to it.)

8. **Step the cursor.** Mark the version's INDEX row `in-progress` (PR open) and move the
   cursor to the next `planned` version. On merge, flip the row to `shipped` and set
   `.meta/version` `status: shipped`. Then **record the step via `session-memory`** (a one-line
   Log entry + any decision worth keeping) so the retrospective (memory) and prospective
   (roadmap) layers stay coupled — this is the step's hand-off, not an optional extra. The
   `roadmap_guard` hook will warn on the next push if the INDEX status and `.meta/version`
   have drifted out of sync.

## Control flow / stop conditions

- No cursor / map missing → **stop**; the roadmap is done or needs `/roadmap-set`.
- Review can't reach clean, or the goal-auditor keeps failing, after a couple of passes →
  **stop and report** the specific blocker; don't ship work that fails its own acceptance.
- Step built, reviewed, acceptance-passed → **stop at the approval gate** (step 6) — this is
  the normal terminal state for one invocation until the user approves.
- A scope question (does this still belong in this version? should the map be re-sliced?) is
  the caller's → ask; re-slice via `/roadmap-set`, don't silently change the plan.

## Invokes

- Skills: `development-mapping` (the map's meaning), `code-review` / `*-review` (step 4),
  `agent-finder` (pick the executor).
- Agents: a developer agent (step 3), `../agents/goal-auditor.md` (step 5); optionally a
  `github-operator` agent for PR formatting in step 7, if the project provides one.
- Commands: `../commands/version-set.md` (step 2), `../commands/version-ship.md` (step 7).
- Workflow: `ship-version` is the shipping spine this reuses.
- Hooks: `../hooks/roadmap_status.py` (SessionStart "you are here"), `../hooks/roadmap_guard.py`
  (PreToolUse·Bash; advisory at push time when the cursor drifts from the map).
- Context: `../context/verification-surface.md` (what step 4 can close and what step 6 must gate).
- State: `.meta/roadmap/` (the map), `.meta/version` (the cursor).
