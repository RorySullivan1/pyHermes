---
name: Task
about: One PR-sized unit of work, usually a sub-issue of an epic.
---

Part of #<!-- parent?: The epic's number. Delete this line for a standalone task. -->

## Goal

<!-- goal: One or two sentences on what this issue delivers and why it matters. The title should be an imperative, specific unit of work ("Add the verification-surface context doc"), never a topic ("Verification"). -->

## Context

<!-- context: What someone picking this up cold needs: the relevant files or docs, the current behaviour, and what has already been decided. Link rather than paste. -->

## Scope

<!-- scope: Two short lists, "In:" and "Out:". "Out" is what stops a sub-issue from quietly absorbing its siblings' work. -->

## Acceptance

<!-- acceptance: Checkable `- [ ]` lines. Each one names a test to run, a file or behaviour to inspect, or a decision recorded in a named place. "Works well" is not checkable. -->

## Depends on

<!-- depends_on: `#N` references to issues that must land first, or "None". -->

## Done when

A PR into the default branch merges with this line in its description, where N is this issue's number:

```
Closes #N
```

<sub>GitHub closing keywords work only from a PR description or a commit message, and only when the PR targets the default branch. Use one keyword per issue, e.g. `Closes #1, closes #2`.</sub>
