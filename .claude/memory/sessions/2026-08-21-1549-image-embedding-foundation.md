# 2026-08-21 15:49 · image-embedding-foundation

**Goal:** Foundational image handling/embedding in svc/builder: EmailImage strategies + asset manifest

User framing that shaped the whole design: **the builder dir is the uniform,
generic layer; individual services (gmail/outlook) expand on it.** So the
question was never "how do we embed an image" but "what is the generic half,
and what is the seam the service layers plug into".

## What happened

- **Found the structural gap.** Images were bare URL strings in three places
  (`EmailMetadata.logo_url`, `EmailMetadata.header_bg_image_url`,
  `ChartBlock.image_url`), checked only for a safe scheme. `cid:` was already
  *allowed* by `_validate_url`, so a CID reference would render — but nothing
  produced the other half of the embed, and `Email.render()` returned only
  HTML, so there was nowhere for it to live.

- **Asked two scoping questions** (AskUserQuestion) before writing code, both
  answered with the recommended option: full manifest plumbing (not just a
  model), and data-URI support guarded + opt-in (not omitted).

- **Shipped `svc/builder/images.py`** — `EmailImage` with three factories
  (`hosted` / `attached` / `inline`) mapping to `EmbedStrategy.REMOTE / CID /
  DATA_URI`, plus `ImageAsset` (the manifest entry), magic-byte format
  sniffing, and `dedupe_assets`.

- **Wired the aggregation path**: new `Component.images()` hook →
  `Container.components()` → `Email.assets()`, plus `EmailMetadata.images()` /
  `.assets()` and `to_dict()` coercion of `EmailImage` → resolved `src`.

- **Added `ImageBlock`** (generic image: caption, link, alignment) in a new
  `templates/media/` category; **widened `ChartBlock`** to accept an
  `EmailImage`. Both still take a bare URL string — every existing call site
  unchanged.

- 68 new tests in `tests/test_images.py` + image fixtures in `conftest.py`.
  349 pass; ruff/format/mypy clean. Built the wheel to confirm
  `templates/media/` actually ships.

- Commit `6169dcf`, pushed to `claude/review-open-issues-rr8quq`. **No PR
  opened** (not requested).

## Gotchas & dead ends

- **The designated branch was already merged into `main`.** Restarted it from
  `origin/main` per the branch rules. Critically, **`main` had moved far past
  what `CLAUDE.md` described at session start** — `enums.py`, `ThreeColumn`,
  and the `CardGroup`/`highlight` rework are all merged, and `test_builder.py`
  + the committed `weekly_market_wrap_v2.html` **no longer exist** (CI is now
  ruff/mypy/pytest + a separate wheel job). An early `git diff` against a stale
  `origin/main` sent me down the wrong path for a few minutes. **Fetch and
  re-read before trusting CLAUDE.md's description of the tree.**

- **Broke two things by not reading the tests first**, both caught by pytest:
  1. `Email._validate_size` is a `@staticmethod` **on purpose** —
     `tests/test_email.py` drives the size edges by calling it directly and
     says so in its module docstring. I made it an instance method to add an
     inlined-image hint. Fix: keep it static and pure, take the hint as an
     optional `hint: str = ""` param that `render()` supplies.
  2. Error messages are asserted on by field name. Routing
     `ChartBlock(image_url=...)` through `EmailImage.hosted()` changed
     `'chart.image_url'` to the generic `'image.url'`. Fix: `coerce_image()`
     calls `_validate_url(value, field_name)` itself before delegating, so the
     message names the field the caller actually passed.

- **Import cycle**, avoided not hit: `models` ↔ `images`. `images.py` imports
  `_validate_url` from `models` *lazily inside functions*; `models.py` imports
  `EmailImage` lazily in methods + under `TYPE_CHECKING` for annotations
  (which are string-quoted). Module-level imports either way would cycle.

- **A test I wrote asserted the wrong thing**: empty `content_id` is not
  invalid, it means "derive one from the bytes". Removed `""` from the bad
  parametrize list rather than changing the code.

- `EmailMetadata.IMAGE_FIELDS` is deliberately **un-annotated** so
  `@dataclass` skips it as a field.

## State at end

- Branch `claude/review-open-issues-rr8quq` @ `6169dcf`, based on `main`
  (`44899cb`), pushed. All checks green. No PR.
- Image handling is complete as a *builder* capability. Nothing consumes
  `Email.assets()` yet — `svc/gmail` and `svc/outlook` still do not exist.

## Open threads

- **`svc/gmail` / `svc/outlook` are the natural next step**, and the manifest
  is now the contract they implement: for every `src="cid:X"` in the HTML,
  `assets()` has the `ImageAsset` to attach as `X`. `ImageAsset.content_id` is
  **bare** — the `cid:` prefix (HTML) and the `<>` (MIME header) are each added
  by whichever consumer needs them.
- **Known wart, left alone deliberately**: `base.html` renders the logo with
  `alt="{{ firm_name }}"`, so an `EmailImage`'s own `alt` is ignored for the
  logo specifically. Fixing it changes rendered output for every existing
  email, so it wants to be its own decision.
- `claude/card-component-and-highlight-property` is pushed with no PR and
  appears superseded by what landed on `main`. Probably deletable.
- `INLINE_LIMIT_KB = 48` is a judgment call (roughly half the 102 KB budget),
  not a spec number — tune it if real newsletters push against it.
