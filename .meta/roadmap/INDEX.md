# Development Map — pyHermes

> Auto-surfaced at session start. Keep to ~one screen; detail lives in `stages/`.
> The cursor (`←`) is the next version to build. Statuses: planned · in-progress · shipped.
> Mapped from the owner's roadmap doc of 2026-10-27
> (https://claude.ai/artifact/G7rihH9sgV3snQ4Fk4aMCu). This copy is the one agents trust;
> when the two disagree, reconcile with `/roadmap-set`, never by editing a shipped card.

## Objective
A research-report generation framework: quantitative research (data, exhibits, findings,
disclosures) goes in once and comes out as a compliance-ready email, report or brochure,
switching medium in one change, through a library, an API, or a model as the author.

## Stages
0. **Reset** — fix what the project is for and what it is judged against. *Milestone: charter merged, three reference reports named, installable from PyPI.*
1. **Email mastery and repeatable reports** — a report you re-run; the best email a Python library produces. *Milestone: an outside user runs a weekly note unchanged for four weeks.*
2. **The research content model** — say what the research is; a layout per medium decides where it goes. *Milestone: each reference report is one `Note`, rendered to email, report and brochure with no rebuilt tree.*
3. **The access point: schema, API and AI** — a note and its data in, checked documents out; every number from data. *Milestone: a model-authored note passes with every number traced; one outside client.*
4. **Application** (conditional) — hosted API and authoring app. *Starts only when an outside team uses the Stage 3 API weekly.*

## Versions
One version is one roadmap epic and ships as one PR; the epic number from the doc leads each goal.

| Version | Stage | Goal (one line) | Status |
|---------|-------|-----------------|--------|
| v0.2.0  | 00 | 0.1 Scope charter: positioning, the freeze rule | planned ← cursor |
| v0.3.0  | 00 | 0.2 Reference reports and the speed benchmark | planned |
| v0.4.0  | 00 | 0.3 First public release on PyPI | planned |
| v0.5.0  | 01 | 1.1 Report definition and the run CLI | planned |
| v0.6.0  | 01 | 1.2 Data binding and provenance | planned |
| v0.7.0  | 01 | 1.3 Three house email templates | planned |
| v0.8.0  | 01 | 1.4 Real-client verification | planned |
| v0.9.0  | 01 | 1.5 Distribution | planned |
| v0.10.0 | 01 | 1.6 Run archive | planned |
| v0.11.0 | 01 | 1.7 Docs for outsiders | planned |
| v0.12.0–v0.20.0 | 02 | 2.1–2.9 Research content model (9 epics, see STAGE.md) | planned (sketch) |
| v0.21.0–v0.27.0 | 03 | 3.1–3.7 Schema, render API, MCP, number grounding (7 epics) | planned (sketch) |
| separate product | 04 | 4.1–4.5 Hosted API, authoring app, approvals (5 epics) | conditional |

## Open decisions (before Stage 1 starts)
- Who owns each reference report, and who is the first outside user?
- Open source, open core or commercial? Decides v0.4.0's licence (MIT today) and whether 3.2 is public.
- The deck stays as a layout (2.8), frozen until then? Recommended: yes.
- DOCX and PPTX stay closed (#219, #300)? Recommended: revisit at 2.5 only if a reference report needs Word.
- The content model in the core package? Recommended: yes, it is Python-only and needs no extra.
- The 2.1 design spike may overlap the end of Stage 1? Recommended: yes.
