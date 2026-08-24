# 2026-08-23 19:54 · open-roadmap-epics

**Goal:** File parent epics for all five roadmap candidates from the "what else deserves an epic" discussion.

## What happened
- Filed five **parent-only epics** (#52–#56), each with a Problem/Goal/principles/planned-breakdown/non-goals/risks/sequencing body in the #38/#45/#46 house style, but with the breakdown as an in-body task list, *not* filed sub-issues:
  - **#52 delivery layer** — transport-neutral MIME core (`multipart/related`, cid bracketing, dry-run `.eml`) + `svc/gmail` / `svc/outlook` adapters. First true consumer of `Email.render()`/`assets()`; carries the first end-to-end CID test. `DeliveryError` sibling to (not child of) `EmailBuilderError`.
  - **#53 plain-text alternative** — `Component.text()` protocol mirroring `images()`; `Email.text()`; generated-never-authored; HTML-subset converter for the blessed tags only; assembly (`multipart/alternative`) belongs to #52's MIME core.
  - **#54 preview & QA harness** — fixture gallery (code, not checked-in HTML), screenshot runner, email-client lint pass (`width=` on imgs, Outlook-dropped CSS, alt coverage, per-section size budget), `preview` CLI. **Pull forward**: gallery overlaps #32; #43/#50 need the screenshots.
  - **#55 footer region** — the sequel #38's non-goals promised; blocked on #38; mirrors #33–#37. Two footer parts (contact CTA with VML dual emission + legal footer); legal content is a compliance floor variants cannot omit.
  - **#56 typography themes** — third theme leg; blocked on #45+#46. `FontTheme` of role-based *stacks* (atom = fallback chain ending websafe, never a bare font); orthogonal to `TypeScale` (a font swap moves zero px); no web-font infra in initial presets.
- Excluded per the discussion's own triage: chart/data generation, component-library growth, packaging — single issues when real, not epics.
- **Branch maintenance:** PR #31 had merged (`main` @ `07d5609`), so per merged-PR rules the designated branch was rebased: its one unmerged commit (memory log `bf1c1ce` → `7cf0fa0`) now sits on post-merge main. INDEX State/Threads refreshed (PR #31 thread closed, eight-epic portfolio recorded).
- No code changed; GitHub issues + memory only.

## Gotchas & dead ends
- The session resumed with the referent of "all of these" lost from context — recovered it by reading the raw session transcript (`/root/.claude/projects/.../*.jsonl`), which held the five-candidate roadmap answer verbatim. The memory log alone was not enough: it recorded what was *filed*, not what was *proposed*.

## State at end
- Eight open epics: #38 (+#32–#37), #45 (+#39–#44), #46 (+#47–#51) active with sub-issues; #52/#53/#54 independent parents; #55/#56 blocked parents.
- Branch `claude/review-open-issues-rr8quq` restarted from `origin/main`, carrying only memory commits; pushed with force-with-lease.

## Open threads
- #55/#56 sub-issues get filed only after their blocking epics merge — and after reviewing the landed mechanism against the plan.
- #54's fixture-gallery slice is the natural companion to #32 whenever golden-test work starts.
