---
name: branding
description: >
  Expert at defining and applying a brand identity — the durable, reusable system that every
  artifact and channel draws from. Use this skill whenever the user wants to create, refine,
  document, or apply a brand: positioning and personality, name and tagline, voice and tone,
  the color palette, the typography system, logo usage rules, imagery/iconography style, and the
  brand-guidelines (style-guide) document itself. Trigger on phrases like "define our brand",
  "create a brand identity", "brand guidelines / style guide", "what's our voice and tone",
  "pick brand colors / fonts", "logo usage rules", "is this on-brand", "make this consistent with
  our brand", "rebrand", "brand kit", "design system for the company", or any request about the
  identity that spans deliverables rather than the design of one specific piece. This is the
  org/product-level identity layer that sits *upstream* of any single artifact: it is reused across
  decks, print, web, social, email, and signage. Defer the design of one specific artifact (laying
  out a given slide/page, choosing its composition and final copy) to `presentation-design`, and
  building the actual file to the format builders (`deck-builder`, `one-pager-builder`,
  `brochure-builder`, `pamphlet-builder`) — those consume the brand; they don't define it.
---

# Branding

Expert at the **durable identity** an organization or product presents everywhere — the system that
every artifact inherits rather than reinvents. Where `presentation-design` decides how *one* deck or
page looks and reads, this skill decides the reusable identity those decisions draw from: the
positioning, the voice, the color and type systems, the logo rules, and the guidelines document that
keeps it all consistent across decks, print, web, social, email, and signage.

## Where this sits

```
            ┌──────────────────────────────────────────────────────────┐
 branding   │  presentation-architect → presentation-design → builders  │  (and: web, social,
(identity:  │  (flow)                   (apply brand to one  (build file)│   email, signage…)
 reused     │                            artifact)                      │
 everywhere)└──────────────────────────────────────────────────────────┘
   feeds ──────────────^ every channel and artifact draws on the brand
```

- **This skill owns (decide once, reuse everywhere):** brand strategy, verbal identity, visual
  identity, and the governance/guidelines that hold them together (the four pillars below).
- **Defer downstream:** the design of a *specific* artifact (a given slide/page's composition, its
  layout and final copy) → `presentation-design`; producing the file → the format builders. They
  *apply* the brand; this skill *defines* it.
- **Brand vs. artifact design-system.** `presentation-design` has a per-artifact "design system"
  step. When a brand exists, that step **inherits** from the brand (palette, type, logo, voice) and
  only adds artifact-specific choices (e.g. slide grid). When no brand exists, `presentation-design`
  may set an ad-hoc system for the one piece — but a recurring need is the signal to define a brand
  here instead.

## Core principles

1. **Consistency compounds.** A brand's power is repetition — the same colors, type, logo, and voice
   across every touchpoint build recognition and trust. Each one-off inconsistency spends that equity.
2. **Distinct, not just nice.** The job is to be recognizably *this* brand, not generically tasteful.
   Differentiation from competitors beats decoration.
3. **Identity follows strategy.** Colors, type, and voice are expressions of positioning and
   personality — not arbitrary taste. Decide who the brand is *for* and *like* before what it looks
   like.
4. **A system, not a logo.** A brand is the whole reusable kit (palette, type scale, logo lockups,
   imagery rules, voice), governed by clear usage rules — not a single mark.
5. **Built to be applied by others.** The deliverable must be usable by people who weren't in the
   room: explicit tokens, rules, and do/don't examples, so any artifact can be made on-brand without
   guessing.
6. **Accessible by default.** Color contrast, legible type, and inclusive imagery are part of the
   identity, not an afterthought.

## The four pillars

A complete brand covers all four. Smaller brands get shorter versions of each, not fewer pillars.

### 1. Strategy (the *why* — drives everything else)
- **Positioning** — what the brand is, who it's for, and what makes it different.
- **Personality** — a few adjectives the brand embodies (e.g. "precise, confident, approachable"),
  plus what it is *not*. These adjectives become the test for every later choice.
- **Audience** — who must recognize and trust it; sets the register for voice and visuals.

### 2. Verbal identity (how it sounds)
- **Name & tagline** — and how they're written (capitalization, never-abbreviate rules).
- **Voice** — the constant personality in words (the adjectives above, made concrete).
- **Tone range** — how voice flexes by context (a celebratory launch vs. an error message), with
  examples.
- **Messaging** — the core value proposition and key phrases; words to use and to avoid.
- *Boundary:* this sets the voice *principles*; `presentation-design`'s copy craft *applies* them to a
  given artifact's headlines and body. Define here, apply there — don't duplicate.

### 3. Visual identity (how it looks)
- **Logo** — primary mark, variants (horizontal/stacked/icon), clear-space and minimum size, the
  approved color treatments, and explicit misuse rules (don't stretch/recolor/add effects).
- **Color** — a defined palette as reusable **tokens**: primary, secondary, accents, and neutrals,
  each with exact values (HEX/RGB; CMYK + Pantone for print) and a stated role (when to use which).
  Verify contrast pairings for accessibility.
- **Typography** — the type system: heading and body typefaces (with web/system fallbacks), the
  weights in use, and a scale with roles — reused across artifacts rather than re-chosen each time.
- **Imagery & iconography** — the photography/illustration style, the icon style, and treatment rules
  (filters, framing) so visuals read as one family.
- **Layout motifs** — recurring devices (grid feel, a signature shape/line, spacing rhythm) that make
  any piece feel like the brand.

### 4. Governance (keeping it coherent)
- **Brand guidelines / style guide** — the single document that captures all of the above with rules
  and **do/don't examples**, so others apply it correctly.
- **Asset kit** — where the logo files, fonts, color swatches/tokens, and templates live.
- **On-brand review** — how to check a given artifact against the identity (the audit below).

## Workflow

1. **Anchor in strategy.** Establish (or read) positioning, personality adjectives, and audience.
   If a brand already exists, inventory it first and match it before proposing anything new.
2. **Define the pillars.** Work top-down: strategy → verbal → visual → governance. Each visual/verbal
   choice must trace back to a personality adjective ("bold reds because the brand is *confident*").
3. **Express as reusable tokens & rules.** Capture color/type/spacing as named tokens and logo/voice
   as explicit rules — concrete enough to apply without the author present.
4. **Check accessibility & distinctiveness.** Validate contrast and legibility; sanity-check that the
   identity is recognizably distinct, not generic or look-alike to a competitor.
5. **Document & hand off.** Produce the brand-guidelines artifact + asset kit. Then it's *applied*:
   `presentation-design` inherits the tokens/voice for a specific piece; the builders render it.
6. **Audit on demand ("is this on-brand?").** Compare an existing artifact against the guidelines —
   color/type/logo usage, voice, imagery — and prescribe specific fixes.

## Output

A **brand system**, not a single artifact:
- **Strategy** — positioning, personality adjectives (and anti-adjectives), audience.
- **Verbal identity** — voice, tone range with examples, messaging, name/tagline rules.
- **Visual identity** — logo rules, the color tokens (with values + roles), the type system, imagery
  & iconography style, layout motifs.
- **Governance** — the guidelines document outline + do/don't examples, and the asset kit location.
- **Hand-off / audit** — how `presentation-design` and the builders consume it; or, for an audit, the
  specific on-brand fixes and the open decisions left for the owner.

## What this skill does *not* do

- **Design a specific artifact** — laying out a given slide/page, its composition and final copy is
  `presentation-design`; this skill sets the system it draws from.
- **Build a file** — that's the format builders.
- **Set product/communication strategy beyond identity** — business goals are an input; this skill
  expresses identity in service of them, it doesn't decide them.
- **Invent facts about the company** — capture the real positioning/values; flag gaps, don't fabricate.

## Anti-patterns

- **Logo-only "branding"** — a mark with no system (color/type/voice/rules) behind it.
- **Taste without strategy** — choices that don't trace to positioning or personality.
- **Inconsistent application** — different colors/fonts/voice per artifact, spending brand equity.
- **Un-appliable guidelines** — vibes instead of tokens, rules, and do/don't examples; others can't
  reproduce it.
- **Generic or look-alike identity** — indistinguishable from competitors or from a default template.
- **Ignoring accessibility** — low-contrast palettes or illegible type baked into the identity.
- **Duplicating artifact design** — re-specifying one deck's layout here instead of deferring to
  `presentation-design`.
</content>
