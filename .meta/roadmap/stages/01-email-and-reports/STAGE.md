# Stage 01 — Email mastery and repeatable reports

**Goal:** turn pyHermes from a renderer you write a script against into a report you re-run,
and make its email the best a Python library produces. Seven epics; 1.4 and 1.5 are the
largest.

**Versions:** v0.5.0 (1.1 report definition), v0.6.0 (1.2 data binding and provenance),
v0.7.0 (1.3 house email templates), v0.8.0 (1.4 real-client verification), v0.9.0
(1.5 distribution), v0.10.0 (1.6 run archive), v0.11.0 (1.7 docs for outsiders).

**Order:** 1.1 first, since 1.2, 1.3 and 1.5 stand on it. 1.4 depends on nothing and may run
alongside. 1.6 needs 1.2 and 1.5; 1.7 closes the stage.

**Milestone (stage exit):** someone other than the owner runs a weekly note from a house
template, unchanged, for four consecutive weeks, and the v0.3.0 benchmark beats its baseline.

**Risk:** v0.5.0 bakes in layout-only assumptions. `build()` must be able to return a Stage 02
`Note` later, not only a section tree; start the 2.1 design spike before v0.7.0 lands.
