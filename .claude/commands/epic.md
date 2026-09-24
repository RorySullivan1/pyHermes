---
description: Plan a body of work WITHOUT writing code and file it on the git remote as an epic with ordered, templated sub-issues that auto-close from their PRs.
argument-hint: <goal, problem statement, or pasted plan>
---

You are turning a body of work into a **GitHub epic**: one parent issue plus ordered
sub-issues, filed on this repo's remote. **This is planning only. Write no code and edit
no source files.** The only outputs are issues. Use the `github-issues` skill as the
standard. Its `references/mechanics.md` gives the exact calls and traps, and its
`references/templates/` hold the bodies.

The request: $ARGUMENTS

## 1. Resolve the target and read the ground
- `git remote get-url origin` gives owner/repo. If there's no remote or GitHub access,
  stop and say so.
- Read what the plan is about: `CLAUDE.md`, the files and docs named in the request, and
  anything a claim in the epic will rest on. **Verify every factual claim in the Problem
  section against the tree or the docs**, and say in the body that you did. An epic built on
  a wrong premise files a whole tree of wrong work.
- Don't touch `.meta/roadmap/` or `.meta/version`. Epics are kept separate from the roadmap.

## 2. Dedupe and taxonomy
- Search open **and** closed issues on the key terms (`search_issues`). If an open epic
  already covers this, stop and propose extending it (`/issue --parent #N`) instead.
- Read the taxonomy: labels (is there an `epic` label?), issue types
  (`list_issue_types`; empty or an error means none), milestones, and
  `.github/ISSUE_TEMPLATE/`. Installed copies of this skill's templates are the same form. A
  template that isn't ours wins, so map this content onto its headings.
- **Epic marker:** use an `Epic` issue type if one exists, otherwise an `epic` label. If
  neither exists, title it `Epic: …` and ask once whether to create the label. Never invent
  labels silently.

## 3. Plan the breakdown
- Slice the work into **independently shippable** children (usually 3–8; GitHub caps a
  parent at 100). Each one is a PR-sized unit someone can pick up cold.
- Order them by dependency and risk: foundations and de-risking first. Record each
  child's `Depends on`.
- Choose each child's kind: `task` by default, `bug` or `feature` where that fits better.
- Write epic-level **Acceptance** (what holds across the children together) and
  **Non-goals**. Anything worth doing later goes in Non-goals as "file it then, not now".

## 4. Render and gate every body
For the epic and each child, write the values as JSON and run
`python3 .claude/skills/github-issues/scripts/issue_body.py render <kind> <values.json>`
then `check --allow-self`. The epic's `breakdown` holds titles only at this point, and its
`dedupe` says what you searched. No numbers exist yet, so render the children without
`parent` and cite sibling dependencies by title. At filing (step 6), re-render each child
with `parent` and the real `#m` numbers, and re-check it. **Nothing is filed until every
body passes the check.**

## 5. Preview and STOP for approval
Show, in one message:
- the epic's title, marker, labels, and full body;
- a table of the children in order: title, kind, labels, and depends-on;
- one child body in full, as a sample;
- whether `.github/workflows/epic-autoclose.yml` exists in the repo.

**Filing is public and notifies people. Do not file anything until the user explicitly
approves.** Apply requested edits and re-preview.

## 6. File (after approval), in this order
1. Create the epic (`issue_write` create) and note its number E.
2. Create the children **in dependency order**, each with `parent_issue_number: E`, using
   the step-4 re-render (parent E, dependencies as the real numbers of siblings filed earlier).
3. For each child: `fill-self <n>`, then `check` with no flags, then update its body.
4. Rewrite the epic's **Sub-issues** section as numbered lines
   `1. #n — <title> (depends on #m)`, then update the epic.
5. Read back: the epic's `sub_issues_summary.total` must equal the number of children
   filed, and one child's parent must be E.

If any write fails, **stop and report exactly what was filed**, with numbers. Don't retry
blind, because a retried create makes a duplicate.

## 7. Auto-close
If the repo lacks `.github/workflows/epic-autoclose.yml`, offer to install it from
`.claude/skills/github-issues/assets/epic-autoclose.yml`. It closes the epic when its last
sub-issue closes. It is a CI change, so it needs its own yes and goes through the normal
branch/PR flow. It goes live only after it merges into the default branch. Remind the user that each child's PR must carry that child's `Closes #n`
line and **never the epic's number**.

## Report
Give the epic URL, the children as `#n title` in order, what was verified, and whether
auto-close is installed.
