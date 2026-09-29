"""
Root conftest: makes the repo root importable for the test suite.

``tests/`` imports ``qa.fixtures`` (the #54 gallery), and ``qa`` is not an
installed package — the wheel ships ``packages = ["pyhermes"]`` only, deliberately.
Today it resolves anyway, because hatchling's editable install drops the whole
project root onto ``sys.path``; but that is a property of the current build
backend's editable strategy, not something this repo declares. A backend that
exposed only ``pyhermes`` would break ``import qa`` in CI while ``import pyhermes`` kept
working — a failure with no obvious connection to its cause.

pytest inserts a conftest's own directory under the default ``prepend`` import
mode, so this file existing at the root is the whole mechanism.
"""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Register the golden-snapshot regeneration flag (#58).

    It lives here rather than in ``tests/conftest.py`` because pytest only
    reads ``pytest_addoption`` from the rootdir conftest and from plugins.

    Regeneration is opt-in by design: nothing rewrites a golden implicitly,
    and a missing golden fails rather than being created, so the first pinned
    bytes are reviewed like any other change. A golden diff in a pull request
    is a claim that the visual change is intended.
    """
    parser.addoption(
        "--update-goldens",
        action="store_true",
        default=False,
        help=(
            "Rewrite the checked-in golden snapshots in qa/fixtures/goldens/ "
            "from the current render. Review the resulting diff before committing."
        ),
    )
