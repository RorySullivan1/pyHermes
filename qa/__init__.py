"""
QA harness — the fixture gallery and the tools that consume it (epic #54).

Deliberately a top-level package rather than a subpackage of ``svc``: the
wheel ships ``packages = ["svc"]``, so nothing here reaches an installing
user. The gallery is test data — several PNG-bearing emails — and shipping it
to every consumer would be dead weight in a library whose whole discipline is
staying under a size budget.

It is also not under ``tests/``, because ``tests/`` is not importable from an
installed position and the epic's later tools (the screenshot runner #59, the
lint pass #60, the ``preview`` CLI #61) are not tests. A separate top-level
package is the only home that both the suite and a dev-facing tool can import.
"""
