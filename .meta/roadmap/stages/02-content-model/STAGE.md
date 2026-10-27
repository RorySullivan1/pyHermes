# Stage 02 — The research content model  (sketch)

**Goal:** a layer above the section tree that says what the research *is*, not where it goes,
so switching from email to report to brochure is one change. The largest stage and the one
with the most design risk.

Today the tree describes layout (`FullWidth`, `Page`, `Panel`, `Slide`); a `Brochure` takes
panels and a `Deck` takes slides, so changing medium rebuilds the tree, and `Only` /
`OnlySections` can hide sections but not convert them. The content model holds the note
(thesis, key figures, exhibits, findings, disclosures, sources). A **layout** per medium
selects, condenses and places it, and compiles to today's section tree, which stays as the
lower-level escape hatch.

**Versions (sketch; cards are written when this stage is next):**

| Version | Epic | One line | Needs |
|---------|------|----------|-------|
| v0.12.0 | 2.1 | Design spike and decision record: types, tiers (lead, core, detail), how a layout compiles | 1.1 |
| v0.13.0 | 2.2 | Content model: `Note`, `Finding`, `Exhibit`, `KeyFigure`, `Narrative`, `DisclosureSet`, with a JSON round trip | 2.1 |
| v0.14.0 | 2.3 | Layout system: selection by tier, author-supplied short and long variants, placement | 2.2 |
| v0.15.0 | 2.4 | Fit and overflow: drop or condense the lowest tier first and say what was dropped | 2.3 |
| v0.16.0 | 2.5 | Standard format catalogue: research report, factsheet, tri-fold, daily email, weekly wrap | 2.3 |
| v0.17.0 | 2.6 | Custom formats and brand packs: theme, typeface, logo, disclosure library in one object | 2.3 |
| v0.18.0 | 2.7 | Compliance layer: disclosure rules by product, jurisdiction and rating; analyst certification; a draft/approved state | 2.2 |
| v0.19.0 | 2.8 | The deck re-homed as a layout of the same note | 2.3 |
| v0.20.0 | 2.9 | Migration: examples, drafts and the manual ported to notes | 2.5 |

**Milestone (stage exit):** each Stage 00 reference report is one `Note` that renders to email,
report and brochure with per-medium choices only, no rebuilt tree.

**Risk:** a model too generic (every report is "sections" again) or too opinionated (only
sell-side notes fit). Test 2.1 against all three reference reports before 2.2 starts; 2.1 may
begin during the end of Stage 01.
