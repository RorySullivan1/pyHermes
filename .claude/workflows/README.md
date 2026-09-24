# workflows/

**Multi-step autonomous orchestration.** Claude executes a scripted sequence that
can loop, branch, and spawn agents — designed to run largely unattended. Where a
command is one shot, a workflow is a whole pipeline.

## Format

- One markdown file per workflow: `<name>.md`.
- The body lays out the ordered steps, the agents/commands each step invokes, the
  inputs and outputs, and the success/stop conditions.
- Reference `../agents/` and `../commands/` rather than re-describing them.

## Typical uses

- A scheduled report: gather data → score/analyze → draft → deliver.
- A triage pipeline: read items → prioritize → assign → post a digest.
- A refresh job: fetch source data → recompute → write outputs → flag anomalies.

## Defined here

- `ship-version` — label a unit of work with its goals in `.meta/version`, then name and
  ship the PR from those goals (`/version-set` + `/version-ship`).
- `verify-claims` — the **truth gate** for assets that assert facts about an external
  system (engine: the `claim-grounding` skill; independent of `skill-creator`'s
  performance evals).
- `establish-verification` — answer per surface whether the agent can confirm it or a human
  must, prove each candidate check can fail, and write `../context/verification-surface.md`.

To add one, create a `<name>.md` describing the sequence (see Format above); the
auto-generated `../CATALOG.md` is the always-current inventory.
