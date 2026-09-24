# Filing mechanics: MCP first, `gh` as the fallback

This is the exact call sequence `/epic` and `/issue` use. The skill body says *what* a good
issue is. This page says *which call* makes it, including the traps.

## Repo and taxonomy (read, never write)

| Need | GitHub MCP | `gh` fallback |
|---|---|---|
| owner/repo | `git remote get-url origin` | same |
| Duplicates | `search_issues` (`repo:O/R is:issue <terms>`) | `gh issue list --search "<terms>" --state all` |
| Labels | `get_label` for each candidate | `gh label list` |
| Issue types | `list_issue_types` (owner, repo). If the result is empty or an error, the repo has none. Use a label instead. | `gh api orgs/O/issue-types`. This endpoint is organization-scoped. For a personal account's repo, use a label. |
| Repo's own templates | `.github/ISSUE_TEMPLATE/` on disk | same |

If `.github/ISSUE_TEMPLATE/` holds this skill's installed copies (listed in `../installs.json`
and kept identical by `asset_integrity`), they're the same form. Render as usual. A
template that **isn't ours** wins over the skill's, so map the content onto its headings.

## Creating, parented in one call

`issue_write` with `method: create` takes `parent_issue_number` and attaches the new issue
as a sub-issue **in the same call**. Prefer it. It sidesteps the trap below.

**Trap: a sub-issue's *id* is not its *number*.** The standalone link call
(`sub_issue_write`, or REST `POST /repos/O/R/issues/{parent}/sub_issues`) takes
`sub_issue_id`, which is the issue's database **id**, not the `#N` you see. Passing the
number either fails or links the wrong issue. With `gh`:

```bash
id=$(gh api repos/O/R/issues/$CHILD --jq .id)
gh api repos/O/R/issues/$PARENT/sub_issues -F sub_issue_id="$id"
```

Limits (GitHub docs): **100 sub-issues per parent, 8 levels of nesting.** A sub-issue must
belong to the same repository owner as its parent.

## Body pipeline (deterministic, run for every issue)

```bash
S=.claude/skills/github-issues/scripts/issue_body.py
python3 $S render <kind> values.json --out body.md   # fails on any missing value
python3 $S check body.md --allow-self                # pre-filing gate
# create the issue with body.md, then take its number N:
python3 $S fill-self body.md N --out body.md
python3 $S check body.md                              # post-filing gate: closing line numbered
# update the issue body with the numbered version
```

The **Done when** line is `Closes #N` until `fill-self` replaces the N. An issue's own number
is only known after creation, and the line must be copy-paste ready for whoever opens the
PR. `values.json` keys are the slot names in the template (`<!-- goal: … -->` → `"goal"`).
A misspelled key is refused, not ignored.
The epic template has no Done-when section, because an epic is closed by its children (below).

## Order of writes for an epic

1. Create the **epic**. Its breakdown lists titles only.
2. Create the **children in dependency order**, each with `parent_issue_number`, so every
   `Depends on #M` they cite already exists.
3. `fill-self` each child, then run the post-filing check and update its body.
4. Rewrite the epic's **Sub-issues** section with the real numbers, then update the epic.
5. Read back: `issue_read` on the epic (`sub_issues_summary.total` must equal the count
   filed), and one child (its parent must be the epic).

Writes are not atomic. If a step fails part-way, **report exactly what was filed**, with
numbers, and stop. Don't retry blind: a retried create is a duplicate issue.

## Auto-close

- **Child closes from its PR.** Put `Closes #N` (or `Fixes`/`Resolves`) in the PR
  *description*. Keywords are `close(s|d)`, `fix(es|ed)`, `resolve(s|d)`, one per issue,
  and they fire **only when the PR targets the default branch**. A commit message works too,
  but then the PR isn't listed as the linked PR. Cross-repo form: `Closes owner/repo#N`.
- **Epic closes from its children.** GitHub's docs don't say that a parent closes when its
  sub-issues do, so don't rely on it. Install `../assets/epic-autoclose.yml` as
  `.github/workflows/epic-autoclose.yml`. It closes the parent when the last child closes,
  reopens it when a child reopens, and cascades through nested epics in one run (events
  caused by `GITHUB_TOKEN` don't start new runs). Probed: `../probes/PROBES.md`.
  **It goes live only once it is on the default branch.** `issues` events run only workflow
  files that exist there, so a copy sitting on a feature branch does nothing yet. Install it as a
  byte-identical copy. `../installs.json` declares the target, and the `asset_integrity` hook
  flags drift at every commit.
- Never put the epic's number in a child's closing line. That would close the epic on the
  first child's merge.
