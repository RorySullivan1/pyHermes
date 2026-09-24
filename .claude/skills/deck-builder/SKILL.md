---
name: deck-builder
description: >
  Expert at assembling a real slide deck in a concrete tool — the execution tier that turns a design
  spec into an actual file. Use this skill whenever the user wants to *build*, *generate*, or *export*
  a presentation file rather than design it: producing a .pptx (e.g. with python-pptx), a Google
  Slides deck, a LaTeX Beamer PDF, or HTML/Markdown slides (Marp, reveal.js, Quarto). Trigger on
  phrases like "build this deck", "generate the PowerPoint", "make a .pptx", "create the slides in
  Beamer/Marp/reveal.js", "export this to slides", "turn this outline into a deck", "script the deck",
  "apply our template/master to these slides", or any request to produce a presentation *file* in a
  specific format/tool. Focused on slide decks specifically (the most common buildable format). Defer
  the narrative flow and section order to `presentation-architect`, and the visual design and final
  copy to `presentation-design` — those are inputs this skill renders, not calls it makes. This skill
  picks the tool, builds reliably and reproducibly, and verifies the output opens and matches the spec.
---

# Deck Builder

Expert at the **execution tier**: taking a flow blueprint and a design spec and producing a real,
openable slide deck in a chosen tool. Where `presentation-architect` decides *what to say in what
order* and `presentation-design` decides *how it should look and read*, this skill decides *how to
actually build it* — the tool, the method (template-driven, scripted, or hand-assembled), and the
reproducible steps that yield a correct file.

## Where this sits

```
presentation-architect   →   presentation-design   →   deck-builder
(objective flow)              (subjective design + copy)  (THIS: build the file)
```

- **Inputs (not this skill's calls):** the flow/structure (from `presentation-architect`) and the
  visual + copy design spec (from `presentation-design`). If either is missing, get it from that
  skill or the user — don't improvise the storyline or invent the design while building.
- **This skill owns:** choosing the build tool, the build method, applying the template/master,
  rendering each unit faithfully to the spec, and verifying the result.

## Choosing the tool

Pick by output need, environment, and whether the build must be **reproducible/automated** or
hand-finished. Default to the format the user/organization already standardizes on.

| Tool / format | Reach for it when | Build method |
|---|---|---|
| **PowerPoint (.pptx)** | Org standard; editable hand-off; corporate template/master exists | `python-pptx` to script from data/spec, or assemble on a `.potx` template |
| **Google Slides** | Cloud collaboration, easy sharing | Slides API, or import a generated `.pptx` |
| **LaTeX Beamer (PDF)** | Academic/technical; equations; fixed, portable PDF | Beamer source → `pdflatex` |
| **Marp / reveal.js / Quarto (HTML/MD)** | Version-controlled, text-first, web or PDF export | Markdown + a theme → CLI/export |

Guidance:
- **Editable corporate deck** → `.pptx`, applied to the official template so masters/placeholders/
  fonts/colors come from the org theme.
- **Reproducible, data-driven, or version-controlled** → script it (`python-pptx`) or a Markdown
  framework (Marp/reveal.js) so the deck regenerates from source. (In this project's Python tooling,
  `python-pptx` pairs with the `python-development` skill.)
- **Portable, typeset, equation-heavy** → Beamer → PDF.

## Build principles

1. **Render the spec faithfully — don't redesign.** The layout, type, color, copy, and chart styling
   come from `presentation-design`. Your job is fidelity, not new design decisions. If the spec is
   under-specified, ask; don't fill the gap with invented styling.
2. **Use the master/template, not ad-hoc formatting.** Drive fonts, colors, and layouts from slide
   masters / theme / placeholders so the deck is consistent and re-themeable. Avoid hand-positioning
   that breaks the moment the template changes.
3. **Make it reproducible when the content will change.** If the deck is data-driven or will be
   regenerated, script the build so it rebuilds from source (data + spec) deterministically — separate
   content/data from the rendering code.
4. **One source of truth for content.** Pull text and numbers from the provided content/data, not
   retyped copies, so the deck can't drift from the source.
5. **Mind the medium's limits.** Respect aspect ratio (16:9 vs 4:3), embed or declare fonts so they
   survive on another machine, keep image resolution sensible, and watch file size.

## Workflow

1. **Gather inputs.** Confirm the flow (from `presentation-architect`) and the design spec (from
   `presentation-design`), plus assets (logo, images, data) and any org template. Missing either
   upstream input → request it; don't build blind.
2. **Choose the tool & method.** Pick from the table by output need and whether the build must be
   reproducible. State the choice and why.
3. **Set up the scaffold.** Apply the template/master/theme; define or load the layouts the design
   spec uses; wire in fonts/colors from the theme.
4. **Build unit by unit.** For each slide, instantiate the spec's layout, place title/body/visuals,
   insert charts/images, and apply styles from the master. Keep content sourced from the data, not
   retyped.
5. **Verify.** Open/render the output and check: it opens without error; slide count and order match
   the flow; each slide matches its design spec; fonts/colors/images render; charts are correct; aspect
   ratio and file size are sane. For scripted builds, re-run to confirm it's deterministic.
6. **Deliver.** Hand back the file (and, for scripted builds, the script + how to regenerate). Note any
   spec items that couldn't be rendered and why, and any missing assets.

## Output

- **The deck file** in the chosen format (and the build script, if scripted/reproducible).
- **Build notes** — tool and method chosen and why; how to regenerate (for scripted builds); aspect
  ratio/template applied.
- **Verification** — confirmation it opens, slide order/count matches the flow, and units match the
  design spec; anything that couldn't be rendered to spec, and missing assets.

## What this skill does *not* do

- **Decide the narrative or order** — that's `presentation-architect`.
- **Decide the visual design or write the final copy** — that's `presentation-design`.
- **Invent facts or data** — render what's provided; flag gaps rather than fabricating.

## Anti-patterns

- **Redesigning during the build** — making layout/color/copy calls that belong to
  `presentation-design`.
- **Ad-hoc formatting over the master** — hand-positioned text boxes and one-off colors that break
  consistency and re-theming.
- **A one-off manual build for content that will change** — should have been scripted/reproducible.
- **Retyping numbers** — copy from the data source so the deck can't silently drift.
- **Shipping unverified** — never hand over a deck you haven't opened/rendered to confirm it's correct.
- **Font/asset surprises** — non-embedded fonts or missing images that vanish on another machine.
</content>
