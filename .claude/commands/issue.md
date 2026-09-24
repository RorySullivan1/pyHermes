---
description: File one templated GitHub issue (task, bug, or feature) on the git remote, optionally as a sub-issue of an epic, with a ready-to-paste closing line.
argument-hint: <what the issue is about> [--parent #N] [--kind task|bug|feature]
---

You are filing **one GitHub issue** on this repo's remote. **This is planning only. Write no
code.** Use the `github-issues` skill as the standard. Its `references/mechanics.md` gives
the calls and traps, and `references/templates/` holds the bodies.

The request: $ARGUMENTS

## 1. Parse and resolve
- `--parent #N` makes this a sub-issue of epic N. `--kind` picks the template: `bug` for
  broken behaviour, `feature` for new capability framed as a user problem, `task` for
  anything else. If `--kind` is absent, infer it from the request and say which you chose.
- `git remote get-url origin` gives owner/repo. If there's no remote or GitHub access,
  stop and say so.
- With `--parent`: read the parent (`issue_read`). It must be open and have fewer than 100
  sub-issues. Read its body, because the new issue's Context and Scope must fit the epic's
  Outcome and Non-goals. Say so if the request conflicts with them.

## 2. Ground, dedupe, and taxonomy
- Check every factual claim the body will make (file paths, behaviour, error text)
  against the tree. For a `bug`, reproduce it if you can. Never invent reproduction steps.
- Search open **and** closed issues on the key terms and error text. If a duplicate is
  open, stop and point to it. If it's closed, propose reopening it rather than filing again.
- Read labels, issue types, and `.github/ISSUE_TEMPLATE/`. Installed copies of this skill's
  templates are the same form. A template that isn't ours wins.
  Pick labels from the existing set only.

## 3. Render and gate
Write the values JSON (`parent` set to N, or omitted) and run
`python3 .claude/skills/github-issues/scripts/issue_body.py render <kind> <values.json>`
then `check --allow-self`. Fix every defect it reports. Nothing is filed until the check
is clean.

## 4. Preview and STOP for approval
Show the title, kind, labels, the parent if any, and the full body. **Filing is public.
Do not file until the user explicitly approves.**

## 5. File (after approval)
1. `issue_write` create, with `parent_issue_number: N` when there's a parent. This creates
   and links in one call, so the id-versus-number trap never arises.
2. `fill-self <n>`, then `check` with no flags, then update the body so the Done-when line
   reads `Closes #n` (or `Fixes #n` for a bug).
3. With a parent: append `k. #n — <title>` (plus `(depends on #m)` if it applies) to the
   epic's **Sub-issues** section and update the epic body.
4. Read back: the issue exists, and with a parent, the parent's sub-issue count went up
   by one.

If a write fails, report exactly what landed and stop. Don't retry blind.

## Report
Give the issue URL and number, the closing line to paste into its PR, and the parent link
if there is one.
