# 2026-10-10 17:25 · codebase-review-issues

**Goal:** Turn two `/code-review` passes over the whole package into grounded issues: epics where findings cluster, bugs standalone.

Planning only; no source changed. The reviews (owner's local runs, 10 and 9 findings, 4 overlapping) were re-run
as probes against `main` @ `ac0a8a4` before filing; every one reproduced. Filed through the `github-issues`
pipeline (render, check, create, fill-self, check, update), REST through `gh api` for the bodies, `issue_write`
for the types, because the REST `type` field is ignored on create and on PATCH.

| Issue | What |
|---|---|
| #418 | Epic: every send keeps the delivery error contract and every message is measured |
| #420 | Outlook `send_message` re-raises any `ValueError` bare; requests' `MissingSchema` escapes `TransportError` |
| #421 | A negative `Retry-After` reaches `time.sleep`, bare `ValueError` after one attempt |
| #422 | `EmailImage.attached(filename=)` unvalidated: CR/LF gives a bare `ValueError`, `../` reaches the desktop draft's path |
| #423 | `desktop._recipients` splits a quoted display name on its comma |
| #424 | The 20 MB budget runs only `if attachments:`; CID-only messages are never measured |
| #425 | Task: `SSLError` is an `OSError`, so a certificate failure is retried as transient (depends on #420, #421) |
| #419 | Epic: the render path does each expensive step once |
| #426 | `render_pdf` re-implements `layout()`; `page_count`/`anchor_tops` lay out and warn again (WeasyPrint 70 merges `DEFAULT_OPTIONS` itself) |
| #427 | `_inline_image_hint()` walks every image on every render of every medium |
| #428 | `_check_attachment_budget` and each adapter serialise the message separately (depends on #424) |
| #429 | `_validate_url` reads everything before the first colon as a scheme; `/view?at=10:30` is refused |
| #430 | `dedupe_assets` collapses two different images sharing a `content_id`, silently |
| #431 | `kept_sections()` runs outside `@_under_own_config`; a hidden `OnlySections` is numbered |
| #432 | A second `EmailBuilder.metadata()` discards every section, no error |
| #433 | `wrap()` breaks a long URL in the plain-text part (`research.py` already passes the two flags) |
| #434 | `table_from_frame` accepts duplicate column names; both lose numeric kind |
| #435 | The default copyright row prints `&copy;  Firm` when `current_year` is unset |

## Decisions and why
- **Delivery findings are one epic** because they share a contract (`delivery.md`: catch `DeliveryError`) and
  one test shape; #425 depends on #420 and #421 because it changes the same classification code.
- **Efficiency findings are one epic**, no bug among them: nothing is wrong, only repeated.
- **The seven builder and data bugs stay standalone**: each is one PR with its own `Fixes`, no shared code.
- **A5 (OSError transient) is a task, not a bug**: the retry is wasteful, not wrong.

## Gotchas
- The tracker had **zero open issues** on 2026-10-10 (the owner closed the rest), so the dedupe was by closed titles.
- `search_issues` returned nothing for every query, `is:open` included; `gh api repos/.../issues` is the reliable list.
- `python3 -I` drops the project's site-packages here; run probes with plain `python3`.
- Evidence fences had `->` arrows; replaced with "yields" to keep every body free of angle brackets.
- The breakdown's `(depends on #...)` once rendered `##420`; the fix was a `sed` and a second PATCH.

## State at end
- 18 issues open: #418 (6 children), #419 (3 children), #429–#435 standalone. Nothing implemented.
