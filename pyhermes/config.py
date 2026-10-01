"""
Tunable limits and policy for pyHermes, in one frozen dataclass.

Each field is a **judgment call** rather than a fact about the world: a cap
chosen as "about half the budget", a timeout as "long enough for a slow
upload". Facts — Graph's ``ACCEPTED = 202``, the transient status families —
stay literals where they are used, because changing one does not tune
behaviour, it makes the code wrong.

    get_config().inline_image_limit_kb     # what is in force
    set_config(Config.from_env())          # the process-wide default
    with config_override(retry_max_attempts=1): ...   # this context only
    Document(facts, config=Config(size_limit_kb=500))  # this document only

Consumers call ``get_config()`` at use time; `.claude/rules/config.md` has the rest.
"""

from __future__ import annotations

import os
from contextvars import ContextVar, Token
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
        size_warn_kb: Soft threshold that raises a ``SizeWarning``. A judgment call:
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
        exhibit_separator: Between a numbered exhibit's number and its
            caption — ``"Exhibit 3 · Factor returns"``. House style (#181).
        appendix_heading: How an appendix's section title reads, from its
            ``{letter}`` and ``{title}``: ``"Appendix A: Data sources"`` (#309).
        citation_authors: The most authors an author-year citation names before
            it shortens to the first and "et al." (#310).
        print_dpi: The resolution a brochure's images must reach (#188). Below
            it warns and below half of it raises; 300 is the offset norm.
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

    exhibit_separator: str = " · "
    appendix_heading: str = "Appendix {letter}: {title}"
    citation_authors: int = 2

    print_dpi: int = 300

    #: The ceiling on a whole message once it carries an attachment, counted as
    #: encoded wire bytes. Microsoft 365's default, the lower of the two big
    #: providers' (Gmail refuses above 25 MB); `config.md` has why.
    attachment_limit_kb: int = 20480
    #: Where a message with an attachment starts raising a ``SizeWarning``.
    attachment_warn_kb: int = 15360

    #: Let an email take a density no client has rendered: a custom
    #: ``SizeScheme``, or a print density such as ``dense``. Off, because the
    #: shipped email densities are the ones checked against Gmail and Outlook;
    #: set it once you have rendered yours in the clients you send to (#212).
    allow_custom_email_density: bool = False

    #: The narrowest column a split may compute at the 680px email frame. Custom
    #: weights narrower than this raise at construction, naming the width (#264).
    min_column_px: int = 90

    #: How many times wider than its display width an attached or inline image may
    #: be before a ``SizeWarning`` says to export it smaller (#276). Above the 4x an
    #: equation renders at and the 3.125x print needs; `config.md` has the measurement.
    oversize_image_ratio: float = 4.5

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
            "print_dpi",
            "min_column_px",
            "citation_authors",
            "oversize_image_ratio",
            "attachment_limit_kb",
            "attachment_warn_kb",
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
        if self.attachment_warn_kb > self.attachment_limit_kb:
            raise ValueError(
                f"attachment_warn_kb ({self.attachment_warn_kb}) must not exceed "
                f"attachment_limit_kb ({self.attachment_limit_kb}) -- a warning after the "
                "hard failure never fires."
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
        if not self.exhibit_separator.strip():
            raise ValueError(
                f"exhibit_separator must show something between the number and the "
                f"caption, got {self.exhibit_separator!r}"
            )
        try:
            heading = self.appendix_heading.format(letter="\0", title="")
        except (KeyError, IndexError, ValueError) as error:
            raise ValueError(
                "appendix_heading takes {letter} and {title} and nothing else, "
                f"got {self.appendix_heading!r}"
            ) from error
        if "\0" not in heading:
            raise ValueError(
                f"appendix_heading must show the {{letter}}, got {self.appendix_heading!r}"
            )
        if not isinstance(self.allow_custom_email_density, bool):
            raise ValueError(
                "allow_custom_email_density must be a bool, "
                f"got {self.allow_custom_email_density!r}"
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
        A string field takes the variable verbatim, surrounding spaces included.
        """
        source = base if base is not None else cls()
        overrides: dict[str, object] = {}

        for field in fields(cls):
            raw = os.environ.get(f"{prefix}{field.name.upper()}")
            if raw is None or not raw.strip():
                continue
            text = raw if field.type == "str" else raw.strip()
            if field.name == "request_timeout_seconds" and text.lower() == "none":
                overrides[field.name] = None
                continue
            if field.type == "bool":
                overrides[field.name] = _parse_bool(text, f"{prefix}{field.name.upper()}")
                continue
            caster: type = {"int": int, "str": str}.get(str(field.type), float)
            try:
                overrides[field.name] = caster(text)
            except ValueError as exc:
                raise ValueError(
                    f"{prefix}{field.name.upper()}={raw!r} is not a valid "
                    f"{caster.__name__} for {field.name}"
                ) from exc

        return replace(source, **overrides)  # type: ignore[arg-type]


_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"0", "false", "no", "off"})


def _parse_bool(text: str, variable: str) -> bool:
    """A switch from its variable, refusing anything that is not plainly on or off."""
    lowered = text.lower()
    if lowered in _TRUE or lowered in _FALSE:
        return lowered in _TRUE
    raise ValueError(
        f"{variable}={text!r} is not a valid bool; use one of {sorted(_TRUE | _FALSE)}"
    )


#: The process-wide default. Read through :func:`get_config` rather than
#: imported directly, so a later :func:`set_config` is seen by code that
#: already imported this module.
_default: Config = Config()

#: This context's override, if any: a thread or an asyncio task sees its own,
#: so two renders in one process cannot read each other's limits.
_context: ContextVar[Config | None] = ContextVar("pyhermes_config", default=None)


def get_config() -> Config:
    """The configuration in force here: this context's override, else the default.

    Consumers call this at use time, not import time, so an override
    installed after import still takes effect.
    """
    override = _context.get()
    return override if override is not None else _default


def set_config(config: Config) -> None:
    """Install ``config`` as the process-wide default, under any context's override."""
    global _default
    if not isinstance(config, Config):
        raise TypeError(f"expected a Config, got {type(config).__name__}")
    _default = config


class config_override:
    """
    Apply a config to this context only, restoring the previous one afterwards.

    Pass a whole :class:`Config`, keyword overrides of the one in force, or
    both. Another thread never sees it, and a new thread starts from the
    process-wide default rather than inheriting it::

        with config_override(inline_image_limit_kb=1):
            ...
    """

    def __init__(self, base: Config | None = None, /, **overrides: object) -> None:
        if base is not None and not isinstance(base, Config):
            raise TypeError(f"expected a Config, got {type(base).__name__}")
        self._base = base
        self._overrides = overrides
        self._token: Token[Config | None] | None = None

    def __enter__(self) -> Config:
        base = self._base if self._base is not None else get_config()
        self._token = _context.set(replace(base, **self._overrides))  # type: ignore[arg-type]
        return get_config()

    def __exit__(self, *exc_info: object) -> None:
        assert self._token is not None
        _context.reset(self._token)
        self._token = None
