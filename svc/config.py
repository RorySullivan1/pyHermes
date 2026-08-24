"""
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
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields, replace

__all__ = ["Config", "get_config", "set_config", "config_override"]

#: Prefix for the environment variables :meth:`Config.from_env` reads, so
#: ``inline_image_limit_kb`` comes from ``PYHERMES_INLINE_IMAGE_LIMIT_KB``.
ENV_PREFIX = "PYHERMES_"


@dataclass(frozen=True)
class Config:
    """
    The tunable numbers, validated at construction like every other model.

    Frozen, so a value cannot drift under a caller mid-run: to change one,
    build a new instance (``replace(get_config(), ...)``) and install it.

    Attributes:
        size_limit_kb: Hard ceiling on rendered HTML. **102 KB is Gmail's
            actual clipping limit**, not a preference — raise it only for a
            channel you have confirmed is not Gmail.
        size_warn_kb: Soft threshold that prints a warning. A judgment call:
            far enough below the hard limit to leave room to react.
        inline_image_limit_kb: Cap on a single ``DATA_URI`` image's base64,
            so one image cannot eat the whole HTML budget. A judgment call —
            roughly half of it.
        retry_max_attempts: Total send attempts including the first.
        retry_initial_delay: Seconds to wait after a first transient failure.
        retry_backoff_factor: Multiplier applied after each failure.
        retry_max_delay: Ceiling on a *computed* wait.
        retry_max_hint_delay: Ceiling on a *server-hinted* wait
            (``Retry-After``). Far above ``retry_max_delay`` so a real hint
            is honoured in full, but finite, because the value arrives in
            response data the caller does not control.
        request_timeout_seconds: Passed to an adapter's HTTP client.
            ``None`` means no timeout — an unbounded call that can hang
            forever, so choose it deliberately.
        error_body_excerpt_chars: How much of a provider's error body to
            quote back in an exception message.
    """

    # Sizes are whole kilobytes: sub-KB precision buys nothing, and an int
    # keeps caller arithmetic (`limit_kb * 1024`) ergonomic. Delays below are
    # genuinely fractional, so those stay floats.
    size_limit_kb: int = 102
    size_warn_kb: int = 90
    inline_image_limit_kb: int = 48

    retry_max_attempts: int = 3
    retry_initial_delay: float = 1.0
    retry_backoff_factor: float = 2.0
    retry_max_delay: float = 30.0
    retry_max_hint_delay: float = 300.0

    request_timeout_seconds: float | None = 30.0
    error_body_excerpt_chars: int = 500

    def __post_init__(self) -> None:
        # Validation at construction, as everywhere else in this codebase --
        # a bad limit should name itself here, not surface later as a
        # confusing size or timing symptom. These are programming errors in
        # setup rather than rejected email data, so they raise ValueError
        # rather than joining the EmailBuilderError/DeliveryError trees.
        for name in (
            "size_limit_kb",
            "size_warn_kb",
            "inline_image_limit_kb",
            "retry_initial_delay",
            "retry_max_delay",
            "retry_max_hint_delay",
        ):
            value = getattr(self, name)
            if value <= 0:
                raise ValueError(f"{name} must be positive, got {value!r}")

        if self.size_warn_kb > self.size_limit_kb:
            raise ValueError(
                f"size_warn_kb ({self.size_warn_kb}) must not exceed size_limit_kb "
                f"({self.size_limit_kb}) -- a warning after the hard failure never fires."
            )
        if self.inline_image_limit_kb > self.size_limit_kb:
            raise ValueError(
                f"inline_image_limit_kb ({self.inline_image_limit_kb}) must not exceed "
                f"size_limit_kb ({self.size_limit_kb}) -- one image cannot be allowed to "
                "exceed the budget for the whole email."
            )
        if self.retry_max_attempts < 1:
            raise ValueError(
                f"retry_max_attempts must be at least 1, got {self.retry_max_attempts}"
            )
        if self.retry_backoff_factor < 1:
            raise ValueError(
                f"retry_backoff_factor must be at least 1, got {self.retry_backoff_factor!r} "
                "-- a factor below 1 shortens each wait, which is not backoff."
            )
        if self.request_timeout_seconds is not None and self.request_timeout_seconds <= 0:
            raise ValueError(
                "request_timeout_seconds must be positive, or None for no timeout, "
                f"got {self.request_timeout_seconds!r}"
            )
        if self.error_body_excerpt_chars < 0:
            raise ValueError(
                f"error_body_excerpt_chars must not be negative, "
                f"got {self.error_body_excerpt_chars}"
            )

    @classmethod
    def from_env(cls, base: Config | None = None, prefix: str = ENV_PREFIX) -> Config:
        """
        A config with any ``PYHERMES_``-prefixed overrides applied.

        Called explicitly, never on import: a library whose behaviour shifts
        with ambient environment is one you cannot reason about locally, and
        the delivery layer's purity depends on not doing that.

        Only variables that are set are read; everything else keeps its
        value from ``base`` (the current defaults when omitted). An unset
        variable and an empty one both mean "leave it alone". A value that
        will not parse raises :class:`ValueError` naming the variable,
        because silently ignoring a misspelt override is how a setting
        appears to have no effect.

        ``request_timeout_seconds`` additionally accepts ``"none"`` for "no
        timeout", since that is a meaningful setting rather than an absence.
        """
        source = base if base is not None else cls()
        overrides: dict[str, object] = {}

        for field in fields(cls):
            raw = os.environ.get(f"{prefix}{field.name.upper()}")
            if raw is None or not raw.strip():
                continue
            text = raw.strip()
            if field.name == "request_timeout_seconds" and text.lower() == "none":
                overrides[field.name] = None
                continue
            caster = int if field.type in ("int", int) else float
            try:
                overrides[field.name] = caster(text)
            except ValueError as exc:
                raise ValueError(
                    f"{prefix}{field.name.upper()}={raw!r} is not a valid "
                    f"{caster.__name__} for {field.name}"
                ) from exc

        return replace(source, **overrides)  # type: ignore[arg-type]


#: The process-wide active configuration. Read through :func:`get_config`
#: rather than imported directly, so a later :func:`set_config` is seen by
#: code that already imported this module.
_active: Config = Config()


def get_config() -> Config:
    """The active configuration.

    Consumers call this at use time, not import time, so an override
    installed after import still takes effect.
    """
    return _active


def set_config(config: Config) -> None:
    """Install ``config`` process-wide."""
    global _active
    if not isinstance(config, Config):
        raise TypeError(f"expected a Config, got {type(config).__name__}")
    _active = config


class config_override:
    """
    Temporarily apply overrides, restoring the previous config afterwards.

    Chiefly for tests, which must not leak a limit into whatever runs next::

        with config_override(inline_image_limit_kb=1):
            ...
    """

    def __init__(self, **overrides: object) -> None:
        self._overrides = overrides
        self._previous: Config | None = None

    def __enter__(self) -> Config:
        self._previous = get_config()
        set_config(replace(self._previous, **self._overrides))  # type: ignore[arg-type]
        return get_config()

    def __exit__(self, *exc_info: object) -> None:
        assert self._previous is not None
        set_config(self._previous)
