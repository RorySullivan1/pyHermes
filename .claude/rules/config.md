---
paths:
  - "svc/config.py"
---

# Configuration — the tunable numbers

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
