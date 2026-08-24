# 2026-08-23 20:30 · build-out-footer-epic

**Goal:** Build out epic #55 (footer region) into filed, linked sub-issues at the user's request.

## What happened
- Grounded the breakdown in `base.html` first: the footer is two marker-delimited blocks after `{{ sections_html }}` — the **contact CTA block** (`contact_heading` / `contact_description` / `contact_url` / `contact_cta_label`, with the `v:roundrect` VML + anchor dual emission) and the **legal footer** (`{{footer_disclaimer}}` emitted RAW — HTML field — plus `current_year`/`firm_name` and the unsubscribe / view-in-browser label+URL pairs).
- Filed and GitHub-linked five sub-issues under #55, mirroring #33–#37, **each explicitly blocked on its #38 counterpart landing**:
  - **#63 extract** (after #33) — carries the epic's first real decision: one `footer.html` vs `footer-contact.html` + `footer-legal.html`; the MinimalFooter variant argues for two. Escaping split survives the move (`footer_disclaimer` stays raw).
  - **#64 metadata split** (after #34) — proposed fact/presentation line: facts = `firm_name`, `current_year`, `footer_disclaimer`, all three URLs; presentation = the labels + `contact_heading`/`contact_description`. Explicitly marked as a proposal that defers to #34's merged precedent.
  - **#65 region API** (after #35, #63, #64) — `render()`/`images()` (the `images()` slot exists even though today's footer has no images), `Email(footer=...)`, `EmailBuilder.footer()`; one render path, no legacy inline fallback.
  - **#66 MinimalFooter** (after #65) — legal only; removes (not adapts) the VML; the compliance floor (disclaimer + unsubscribe cannot be omitted) becomes an enforced test; feeds shape-feedback to #63's decision.
  - **#67 docs** (after #63–#66) — the complete `email > header | body | footer` trilogy, written once coherently against merged code.
- Updated #55's body: header note now says execution-blocked-but-filed, sub-issue checklist replaces the planned breakdown, and a new risk records that the texts encode *today's expectation* of #38 — reconciling against the merged mechanism is #63's first task.

## Gotchas & dead ends
- This filing **supersedes the two-depth rule for #55** (deferred epics were to file sub-issues only after blockers merge) — user's explicit call. The mitigation is baked into every sub-issue: "where #38's landed convention differs, follow it, not this text." #56 (typography) still follows the original rule.

## State at end
- Five epics with sub-issues (#38, #45, #46, #54, #55-execution-blocked), two deferred parents (#52, #53), #56 waiting on #45+#46.
- Nothing in #55 is startable until #33 merges; #57 (+#32/#58 resolution) remains the recommended first implementation PR.

## Open threads
- When #38 lands: sweep #63–#67 texts against the merged mechanism before anyone starts #63.
