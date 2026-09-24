---
paths:
  - "svc/config.py"
---

# Configuration — the tunable numbers

**One field is a string, not a number: `exhibit_separator` (#181).** The " · " between an
exhibit's number and its caption is house style — a judgment call, like the rest — and it is
read at render, so a `config_override` moves both projections at once. `from_env` takes a
string field verbatim, surrounding spaces included, and a blank one is refused.

## Configuration — `svc/config`

Every judgment-call number in the package is a field on one frozen
[Config](../../svc/config.py) dataclass, so a caller can retune it without editing the library.

```python
from svc.config import Config, get_config, set_config, config_override

get_config().inline_image_limit_kb              # what is actually in force
set_config(Config(inline_image_limit_kb=64))    # install process-wide
set_config(Config.from_env())                   # or read PYHERMES_*
with config_override(retry_max_attempts=1):     # scoped, restores on exit (tests)
    ...
```

**The line the module draws — and the reason it exists — is between a judgment call and a
fact about the world.** The inline-image cap, the retry ladder, the request timeout and the
error-excerpt length were all *picked by someone*; a picked number that cannot be revisited
without editing the library is a bad default wearing a constant's clothes. Graph's
`ACCEPTED = 202`, the transient status families, and the Content-ID character set describe
what a provider *does* — changing them does not tune behaviour, it makes the code wrong
about its environment, so they stay literals in the modules that own them.

`size_limit_kb` sits across that line deliberately: 102 KB is a real Gmail limit, not taste,
but an email bound for a non-Gmail channel is legitimately not subject to it. It is
configurable *and* documented as a fact, so raising it stays a conscious act.

Rules the module holds to, each for a specific reason:

- **Nothing reads the environment on import.** `from_env()` is explicit, because a library
  whose behaviour changes with ambient state is one you cannot reason about locally — and
  `svc/delivery`'s purity, which the byte-for-byte dry run depends on, would be the first
  casualty.
- **Consumers call `get_config()` at use time, never at import time.** An override installed
  after import must still be seen. Where a module keeps a public constant
  (`INLINE_LIMIT_KB`, `DEFAULT_TIMEOUT_SECONDS`, `_SIZE_LIMIT_KB`) it is the *shipped
  default*, mirrored from `Config()`; the enforced value comes from the active config.
- **An explicit argument always beats the config.** `retry_with_backoff()`'s numeric
  parameters default to `None`, meaning "ask the config" — passing one still wins, which is
  what the adapters and their tests rely on.
- **Validated at construction, like every model here** — including the cross-field rules
  (`size_warn_kb <= size_limit_kb`, `inline_image_limit_kb <= size_limit_kb`, a backoff
  factor of at least 1). These raise plain `ValueError`, **not** `EmailBuilderError` or
  `DeliveryError`: a bad limit is a programming error in setup, not rejected email data.
- **`None` means no timeout**, so it cannot double as "unspecified" —
  `GraphApiTransport(timeout=...)` uses a private sentinel for the latter.

**Adding a tunable**: add the field (with today's literal as its default, so nothing
re-renders or re-retries differently), validate it in `__post_init__`, read it via
`get_config()` at the use site, and add a case to `TestTheWiringIsLive` in
[tests/test_config.py](../../tests/test_config.py) — that class exists to prove each knob is
actually *reached*, because a config nobody reads is decoration.

## Where the judgment-call line was drawn, and why each rule exists

Moved out of `svc/config.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Tunable limits and policy for pyHermes, in one place.

Every number here was once a literal buried in the module that used it.
Most were judgment calls — a cap chosen as "about half the budget", a
timeout chosen as "long enough for a slow upload" — and a judgment call
that cannot be revisited without editing the library is a bad default
wearing a constant's clothes. They are gathered here so a caller can
change them, see them all at once, and tell which ones are actually
negotiable.

Two kinds of number live in this codebase, and only one kind is here:

- **Judgment calls** — the inline-image cap, the retry ladder, the request
  timeout. Someone picked them. They are configurable.
- **Facts about the world** — Gmail's 102 KB clipping limit, Graph's
  ``202 Accepted``, the transient HTTP status families. Changing those does
  not tune behaviour, it makes the code wrong about its environment.

``size_limit_kb`` sits awkwardly across that line and is included
deliberately: 102 KB is a real Gmail limit, not taste, but an email bound
for a non-Gmail channel is legitimately not subject to it. It is
configurable *and* documented as a fact, so raising it stays a conscious
act rather than a knob someone turns to make a test pass.

Usage::

    from svc.config import Config, get_config, set_config

    get_config().inline_image_limit_kb          # read the active value
    set_config(Config(inline_image_limit_kb=64))  # process-wide override
    set_config(Config.from_env())                 # or take it from the env

**Nothing here reads the environment on import.** ``from_env()`` is
explicit because a library whose behaviour changes with ambient state is a
library you cannot reason about — and the delivery layer's purity, which
its byte-for-byte dry-run guarantee depends on, would be the first
casualty.

### Deliberately not configurable

Recorded so they are not re-litigated as oversights:

- **The 680 px frame and every column width derived from it.** That is the
  design system, and it belongs to the size-themes epic (#45), which makes
  it a *theme* rather than a free-form number.
- **``ACCEPTED = 202``, ``TRANSIENT_STATUSES``.** These describe what a
  provider does, not what this library prefers.
- **The Content-ID character set and length bound.** Loosening it produces
  ids that break the ``cid:`` reference they exist to serve.
```

**`print_dpi` (#188) is the resolution a brochure's images must reach, 300 by default.** The
offset norm, and a judgement call rather than a fact: a proof printer is content with less, a
fine-art press wants more. Below it, a brochure prints a warning at construction; below half
of it, construction raises. `PYHERMES_PRINT_DPI` sets it, like every other field.

**`allow_custom_email_density` (#212) is a switch, off by default, and the first `bool` field.**
An email refuses a custom `SizeScheme` and the print density `dense` until the caller has
rendered theirs in the clients they send to; this is how they say so. It is a judgement call
about one's own audience, which is what puts it here rather than in a constant.
`PYHERMES_ALLOW_CUSTOM_EMAIL_DENSITY` takes `1`/`true`/`yes`/`on` or their opposites, and
`from_env` refuses anything else by name, since a misspelt switch that silently reads as off is
the failure `from_env` exists to prevent.

**`attachment_limit_kb` and `attachment_warn_kb` (#198) are the whole message's budget once it
carries a file**, 20 480 and 15 360 KB by default. Gmail refuses a message over 25 MB, and
Microsoft 365 defaults to about 20 MB. The default is the lower of the two, because a sender
rarely knows which server each recipient sits behind, and a refusal lands after the send.
Both count the encoded wire bytes, so the check runs over `to_wire_bytes()` of the finished
message, not over the file: base64 makes a 16 MB PDF a 22 MB message.

- **It is a second threshold, not a wider `size_limit_kb`.** 102 KB is about the HTML part and
  Gmail's clipping. This is about the whole message and a server's refusal. Two facts get two
  names, and the 102 KB check is untouched.
- **It runs only when there is an attachment.** A message without one has only the HTML to
  budget, and the 102 KB check already owns that.
- **It hints and never acts.** Over the limit, `MessageError` names the total, the limit, each
  file with its size, and each file's `size_hint`. `pdf_attachment` fills that hint when the
  PDF was rendered at full resolution, naming the `SCREEN` profile. The message never
  downsamples a file on its own.
