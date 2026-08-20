---
name: presentation-design
description: >
  Expert visual-design and copy craft for communication artifacts — the subjective *how* that
  turns a flow blueprint into something people can read and look at. Use this skill whenever the
  user wants to design the look and wording of a deck, brochure, one-pager, report, or poster:
  visual hierarchy, layout and grid, typography, color, imagery and iconography, data-visualization
  styling, slide/panel composition, and the final headline and body copy. Trigger on phrases like
  "design this slide/deck", "make this slide look good", "lay out this one-pager/brochure", "what
  layout for this", "fix the visual hierarchy", "choose fonts/colors for this", "style this chart",
  "tighten this headline/copy", "how should this page look", "make this less cluttered", or any
  request about how a presentation *looks and reads* rather than how it is sequenced or which tool
  builds it. Format-spanning (decks, brochures, one-pagers, reports) and tool-agnostic — it produces
  concrete design and copy decisions, not a file. Defer the narrative flow, message hierarchy, and
  section order to `presentation-architect` (that is an input here, not a call this skill makes); and
  defer actually assembling the artifact in a tool (PowerPoint, Google Slides, Beamer, Markdown) to
  `deck-builder`. Inherit the reusable identity (palette, type, logo, voice) from `branding` when a
  brand exists, rather than re-choosing it per artifact.
---

# Presentation Design

Expert at the **subjective craft** of a communication artifact: how it looks and how it reads. This
skill takes a flow blueprint and per-unit content spec — ideally from `presentation-architect`, or
from the user — and turns each unit into concrete visual and copy decisions: the layout, the visual
hierarchy, the type and color, the imagery, the chart styling, and the final wording. It is
**format-spanning** (slides, brochure panels, one-pagers, reports) and **tool-agnostic**: it decides
*what the design should be*, not which application renders it.

## Where this sits

```
presentation-architect   →   presentation-design   →   format-specific builder
(objective flow:               (subjective how:           (tool execution: assemble
 arc, hierarchy, order,         visual design + final      the real file — deck- /
 per-unit content spec)         copy for each unit)        one-pager- / brochure- /
                                                           pamphlet- / report-builder)
```

- **Input (not this skill's call):** the audience, goal, narrative flow, message hierarchy, and the
  per-unit content spec. If they're missing or vague, get them from `presentation-architect` or ask
  — don't silently invent the storyline. Also inherit the **brand** (palette, type, logo, voice) from
  `branding` when one exists — apply it here, don't redefine it.
- **This skill owns:** visual hierarchy, layout/grid, typography, color, imagery/iconography,
  data-viz styling, per-unit composition, and the final copy (headlines + body).
- **Defer downstream:** producing the actual file → the format-specific builder: `deck-builder`
  (slides), `one-pager-builder` (flat page), `brochure-builder` (folded), `pamphlet-builder` (booklet),
  `report-builder` (long-form document).

## Core principles

1. **One message per unit, made obvious in one second.** Every slide, panel, or page has a single
   point (from the content spec). The design's first job is to make that point land before anything
   else is read. If a viewer can't tell what the unit is *about* at a glance, the hierarchy is wrong.
2. **Hierarchy is the whole game.** Guide the eye deliberately: one dominant element, then secondary,
   then supporting. Establish it with size, weight, color, and position — not with everything shouting
   at once.
3. **Subtract relentlessly.** Maximize the data-ink / signal ratio. Every element that isn't carrying
   meaning (decorative chrome, redundant labels, boxes, gradients, clip-art) is noise that dilutes the
   one that is. When in doubt, remove it.
4. **Contrast creates clarity.** Use contrast (size, weight, color, space) to separate the important
   from the incidental. Low contrast reads as "everything is equally unimportant."
5. **Whitespace is structure, not waste.** Generous, intentional spacing groups related things and
   separates unrelated ones (proximity), and it makes the dominant element breathe.
6. **Consistency = professionalism.** A repeated grid, type scale, color set, and spacing rhythm makes
   a set of units feel like one designed object rather than a pile of pages.

## The design system (inherit the brand, then add what's artifact-specific)

Before designing individual units, settle the system the whole artifact obeys. **If a brand exists,
inherit it** — pull the palette, typography, logo rules, and voice from `branding` rather than
re-choosing them; only add the artifact-specific pieces (e.g. the slide grid). **If no brand exists,**
set an ad-hoc system for this one piece — but a recurring need for one is the signal to define a brand
(via the `branding` skill) instead of re-inventing it each time.

- **Grid & margins.** Pick a layout grid (e.g. 12-column for slides, a columned grid for print) and
  consistent margins/safe-area. Everything aligns to it. Alignment is the cheapest way to look
  intentional. *(Artifact-specific — set here.)*
- **Type scale.** From the brand's typefaces (or, absent a brand, choose at most two: one display/
  heading, one body). Define a small scale: title / heading / body / caption. Body text large enough
  for the medium (presented slides need far larger type than a read-alone report).
- **Color palette.** Use the brand's color tokens and their roles. Absent a brand: one primary, one or
  two accents, a neutral range for text/backgrounds. Reserve a saturated accent for *emphasis only* —
  if everything is colored, nothing is emphasized. Check contrast for legibility (mind colorblind-safe
  pairings).
- **Spacing rhythm.** A consistent spacing unit (e.g. multiples of 8px) for gaps and padding so
  rhythm is even across units.
- **Element styles.** Consistent treatment for bullets, captions, callouts, quotes, and especially
  charts (see below) — aligned with the brand where one exists.

## Composition by format

The principles are constant; the canvas changes.

- **Slides (deck).** One idea per slide. Assertion-style title that states the takeaway as a sentence
  ("Revenue doubled after launch"), not a topic label ("Revenue"). Big visual or a few words — never
  a wall of bullets; if you have paragraphs, they belong in a doc, not a slide. Built for viewing at
  distance: large type, high contrast, minimal text.
- **One-pager.** A single eye-path: dominant headline/hero, then a scannable hierarchy down/across the
  page. Designed to be grasped in ~30 seconds and to stand alone. Use sections, not a stream. The most
  important takeaway is the largest thing on the page.
- **Brochure.** Respect the fold/panel order — design for what's revealed at each fold, with a cover
  panel that earns the open and a clear panel-to-panel reading sequence. Each panel is a self-contained
  unit with its own focal point.
- **Report.** Read-alone and denser: a clear document hierarchy (headings, subheads), comfortable body
  measure (line length), figures captioned and placed near their reference, and consistent running
  structure. Skim-able via headings and pull-quotes.

## Data visualization

Charts are where design most often lies by accident — hold them to a high bar:

- **The chart answers one question; its title states the takeaway.** "Q4 churn fell to 2%" beats
  "Churn rate".
- **Pick the encoding for the data type:** trend → line; comparison → bar; part-to-whole → stacked/
  100% bar (avoid pie for >3 slices); relationship → scatter; distribution → histogram/box.
- **Be honest:** include a zero baseline for bar charts, label axes/units, don't truncate to
  exaggerate, don't use 3-D or dual axes to mislead.
- **Strip chartjunk:** drop gridlines, borders, and backgrounds that don't aid reading; label series
  directly instead of a legend when feasible; highlight the one series that matters and mute the rest.

## Copy craft

This skill writes the **final wording**, working from the content spec's key messages:

- **Assertion titles.** State the point as a complete thought, not a category.
- **Parallelism & brevity.** Bullets share grammatical structure; cut filler ("In order to" → "To").
  Aim for phrases, not sentences, on slides; tighter prose in print.
- **Front-load.** Put the takeaway first in every block; readers skim the start of lines.
- **Concrete over vague.** Numbers, specifics, and verbs beat adjectives and hedging.
- **Match register to audience.** Set the formality from the audience the architect named.

## Workflow

1. **Get the brief.** Confirm audience, goal, format/medium, and the per-unit content spec (from
   `presentation-architect` or the user). If the flow is missing, ask for it — don't design blind.
2. **Set the system.** Define grid, type scale, palette, spacing, and element styles once.
3. **Design each unit.** For each slide/panel/page: identify its one message → choose a layout that
   makes that message dominant → place content into the hierarchy → write the final copy → style any
   chart. Note what asset is needed (image, icon, data) where it's missing.
4. **Pass for consistency & honesty.** Check alignment, repeated styles, contrast/legibility, and that
   no chart misleads. Cut anything that isn't earning its place.
5. **Hand off to build.** Emit the design spec — system + per-unit layout/copy/asset notes — for the
   format-specific builder (`deck-builder` / `one-pager-builder` / `brochure-builder` /
   `pamphlet-builder` / `report-builder`) or the user to assemble in a tool. Flag missing assets and
   unresolved choices.

## Output

A **design spec**, not a file:
- **Design system** — grid/margins, type scale, palette, spacing, element styles.
- **Per-unit design** — for each slide/panel/page: its one message, the chosen layout, the visual
  hierarchy (what's dominant), the final copy, chart styling, and the assets it needs.
- **Consistency & honesty notes** — what was unified; any chart/encoding fixes made.
- **Hand-off** — the spec for the format-specific builder (`deck-builder` / `one-pager-builder` /
  `brochure-builder` / `pamphlet-builder` / `report-builder`), the missing assets to source, and the
  open choices for the user.

## What this skill does *not* do

- **Set the narrative or section order** — that's `presentation-architect`; it's an input here.
- **Build the actual file** — that's the format-specific builder (`deck-builder`, `one-pager-builder`,
  `brochure-builder`, `pamphlet-builder`, `report-builder`).
- **Invent the facts, data, or message** — design and word what's given; flag gaps, don't fabricate.

## Anti-patterns

- **Wall-of-bullets slides** — paragraphs masquerading as a slide; move detail to a doc, keep the
  point.
- **No focal point** — everything the same size; the eye has nowhere to land.
- **Decoration as content** — gradients, shadows, clip-art, and boxes that add noise, not meaning.
- **Rainbow emphasis** — so many colors that none signals importance.
- **Misleading charts** — truncated axes, pie soup, chartjunk, missing units.
- **Designing without the flow** — inventing the storyline instead of getting it from the architect.
</content>
