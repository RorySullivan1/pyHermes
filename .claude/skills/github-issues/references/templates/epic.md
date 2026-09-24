---
name: Epic
about: A parent issue for one outcome, delivered by ordered sub-issues.
title: "Epic: "
---

## Problem

<!-- problem: Who is affected, what is broken or missing, and the evidence. Check every factual claim against the code or the docs before filing, and say that you did. Numbered gaps are fine, and each one should map to at least one sub-issue. -->

## Outcome

<!-- outcome: One or two sentences on what is true once this epic is done. This is the sentence the finished work is checked against. Name the result, not the activity. -->

## Sub-issues (in dependency order)

<!-- breakdown: One numbered line per child: `1. #N — <title>`, plus `(depends on #M)` where it applies. Before the children exist, write titles only and fill in the numbers once they're filed. GitHub's sub-issue panel tracks progress. This list records ORDER and DEPENDENCIES, which the panel does not. -->

## Acceptance

<!-- acceptance: Checkable, epic-level `- [ ]` lines: what must hold across the children together. Don't restate each child's own acceptance. -->

## Non-goals

<!-- non_goals: What this epic deliberately does not do, and where that work belongs. A follow-up worth doing but not now goes here as "file it then, not now". -->

## Risks and open questions

<!-- risks?: Optional. Delete this whole section, heading included, if there are none. -->

## Closing

This epic closes when its last sub-issue closes. The `epic-autoclose` workflow does this if the repo has it installed. Otherwise close it by hand with a pointer to the last PR. Sub-issue PRs close their own issue only. None of them should carry a closing keyword for this epic.

---
<sub>Dedupe: <!-- dedupe: What you searched for before filing, and what you found. --></sub>
