# Probes — github-issues

## `probe_epic_autoclose.py`: the auto-close workflow, run for real

```
python3 probe_epic_autoclose.py      # needs bash, curl, jq, PyYAML
```

The probe pulls the `run:` script out of `../assets/epic-autoclose.yml`, so it tests what
ships rather than a copy. It runs that script under real bash, curl, and jq against a local
HTTP server that fakes GitHub's sub-issue endpoints (`/parent`, `/sub_issues`, issue
`PATCH`, `/comments`). Each case sets an issue table, fires one `closed` or `reopened`
event, and asserts the exit code and the **exact list of writes**.

| Covers | Cases |
|---|---|
| Close the parent on its last child: completed, mixed, all not-planned | 3 |
| Cascade through nested epics in one run, and stop at an open uncle | 2 |
| Reopen cascades upward | 1 |
| Controls that must NOT write: open sibling, open parent on reopen, no parent, parent closed by hand | 4 |
| Cross-repo parent is left alone. Repo names compare case-insensitively | 2 |
| Faults fail loudly: a 500 on the parent lookup or the sub-issue list exits non-zero with `::error::` and closes nothing | 2 |

**The probe was checked against five deliberate breaks, and every one turned at least one
case red:** errors read as "no parent", no cascade, open siblings ignored, the close
reason always "completed", and a case-sensitive repo compare. First recorded run:
14/14 passed (2026-09-22).

**Not covered:** GitHub itself. The fake serves the documented shapes: the `/parent`
endpoint, `sub_issues` capped at 100 per parent, and `repository_url` on issue objects.
Whether live GitHub fires `issues.closed` for a sub-issue closed by a merged PR's keyword
is not in doubt. What has never been seen is a live run, so the first real epic that closes
is the confirming event. Check the Actions log for the "Closed #N as …" line.

**Installed-copy drift** is not this probe's job. `../installs.json` declares the install
target, and the `asset_integrity` hook compares the two on every `git commit`/`push`.

## `../scripts/issue_body.py`: template render and gate

```
python3 probe_issue_body.py      # stdlib only
```

38 cases. Every kind renders, passes the pre-filing check, **fails** the post-filing check
until `fill-self` numbers its closing line (a control), then passes. Optional slots drop the
right thing: "Part of" drops as a line, and Risks drops as a section while Closing is kept.
`lint-templates` confirms each template is a valid GitHub markdown issue template (`name:`
over 3 characters, `about:`, slots, no `{{`).

Negatives, each injected and caught: a missing field, a misspelled field, an unknown
template, a leftover slot, an empty section, frontmatter left in a body, and a broken
template (both kinds of lint failure). The closing check reads only the fenced line under
**Done when**, because the footnote's example keywords (`Closes #1, closes #2`) would
otherwise satisfy it vacuously. That failure mode was found by testing the check.

**The probe was checked against four deliberate breaks**, and every one turned cases red:
leftover slots ignored, an optional slot dropping its line instead of its section, the
closing check reading the whole section, and frontmatter not stripped. First recorded run:
38/38 passed (2026-09-23).
