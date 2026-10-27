---
description: Author or update the development map in .meta/roadmap/ — decompose the project objective into ordered stages, versions, and milestones.
argument-hint: [overall objective, or the stage/version to add or revise]
---

You are authoring/updating the project's **development map** at `.meta/roadmap/`. Use the
`development-mapping` skill for the how (altitudes, slicing, sequencing, acceptance).

## 1. Anchor on the objective
Read the project objective and constraints from `CLAUDE.md` / the brief. If `$ARGUMENTS`
names a fresh objective or a specific stage/version to add or revise, scope to that.
**Do not invent product scope** — if the objective is unclear, ask before mapping.

## 2. Read any existing map
If `.meta/roadmap/INDEX.md` exists, read it and the relevant stage/version files. You are
*extending or re-slicing the remaining map*, not rewriting shipped history — preserve
`shipped` versions and their cards unchanged.

## 3. Decompose (objective → stages → versions → milestones)
Per `development-mapping`: group into stages (each ending at a milestone), slice stages
into PR-sized versions sequenced by dependency and risk (walking skeleton first, de-risk
early, vertical slices), and give each version checkable acceptance. Assign monotonic
semver labels by nature of change. Detail the next 1–2 stages; keep later ones as one-liners.

## 4. Write `.meta/roadmap/`
Create `.meta/roadmap/` if absent. Write:

- **`INDEX.md`** — the dashboard (keep it to ~one screen):
  ```
  # Development Map — <project>

  ## Objective
  <one or two lines: the destination>

  ## Stages
  1. <stage> — <milestone, one line>
  2. <stage> — <milestone>

  ## Versions
  | Version | Stage | Goal (one line) | Status |
  |---------|-------|-----------------|--------|
  | v0.1.0  | 01    | …               | shipped |
  | v0.2.0  | 01    | …               | in-progress ← cursor |
  | v0.3.0  | 02    | …               | planned |
  ```
- **`stages/NN-<theme>/STAGE.md`** — stage goal, its versions, and the exit/milestone criteria.
- **`stages/NN-<theme>/vX.Y.Z.md`** — one card per version, in the exact `.meta/version`
  shape so it can graduate directly:
  ```
  # version: vX.Y.Z
  status: planned

  ## Goals
  - <goal>

  ## Objectives / acceptance
  - <checkable acceptance criterion>
  ```

## 5. Confirm — don't start work
Show the INDEX dashboard and the cards you wrote/changed. Mark exactly one version as the
**cursor** (the next to build). Note that `/version-set` graduates a card into
`.meta/version`, and the `advance-roadmap-step` workflow executes it. This command only
records the plan — it does not branch, push, or open anything.
