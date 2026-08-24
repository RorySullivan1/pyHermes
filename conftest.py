"""
Root conftest: makes the repo root importable for the test suite.

``tests/`` imports ``qa.fixtures`` (the #54 gallery), and ``qa`` is not an
installed package — the wheel ships ``packages = ["svc"]`` only, deliberately.
Today it resolves anyway, because hatchling's editable install drops the whole
project root onto ``sys.path``; but that is a property of the current build
backend's editable strategy, not something this repo declares. A backend that
exposed only ``svc`` would break ``import qa`` in CI while ``import svc`` kept
working — a failure with no obvious connection to its cause.

pytest inserts a conftest's own directory under the default ``prepend`` import
mode, so this file existing at the root is the whole mechanism.
"""
