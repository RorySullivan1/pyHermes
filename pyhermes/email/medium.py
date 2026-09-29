"""
The email medium: the Gmail size constraint and the four-slot skeleton.

What ``pyhermes.builder.Email`` renders through. The regions and the skeleton it
names still live in ``pyhermes.builder``; this module owns the *choice* of them
and the one check that is email-specific rather than universal.
"""

from __future__ import annotations

from pyhermes.builder.exceptions import SizeError, SizeWarning, warn_caller
from pyhermes.builder.medium import Medium
from pyhermes.builder.regions import Banner, Footer, Header
from pyhermes.config import Config, get_config

__all__ = ["EMAIL_MEDIUM", "validate_gmail_size"]

# The shipped defaults, kept as module constants because they read as the
# thresholds themselves at a call site. The live values come from
# :func:`pyhermes.config.get_config` at check time -- read those, not these, if
# you need what is actually in force.
_SIZE_LIMIT_KB = Config().size_limit_kb  # Gmail clips emails above this.
_SIZE_WARN_KB = Config().size_warn_kb


def validate_gmail_size(html: str, hint: str = "") -> None:
    """
    Check the rendered size against the Gmail clipping limit.

    Takes the HTML as its argument rather than a document, so the size edges
    can be driven directly in tests. The thresholds come from the active
    :class:`~pyhermes.config.Config` at call time, not import time.

    ``hint`` appends caller-supplied context to the failure message —
    ``Email.render()`` uses it to name inlined images.
    """
    config = get_config()
    size_kb = len(html.encode("utf-8")) / 1024
    if size_kb > config.size_limit_kb:
        raise SizeError(
            f"Rendered email is {size_kb:.1f} KB, "
            f"exceeds {config.size_limit_kb} KB Gmail clipping limit.{hint}"
        )
    if size_kb > config.size_warn_kb:
        warn_caller(f"Email size {size_kb:.1f} KB (target < {config.size_warn_kb} KB)", SizeWarning)


#: The shipped email medium. Its region order is the skeleton's own, which is
#: what makes ``Medium.slots`` the contract ``base.html`` is checked against.
EMAIL_MEDIUM = Medium(
    name="email",
    skeleton="base.html",
    region_types=(Header, Banner, Footer),
    constraints=(validate_gmail_size,),
    template_search_path=("email",),
    email=True,
)
