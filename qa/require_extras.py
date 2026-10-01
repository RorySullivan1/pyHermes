"""
A pytest plugin: under ``PYHERMES_REQUIRE_EXTRAS=1``, a skip that names an extra fails (#239).

CI's ``all-extras`` job installs every extra, so a skip there that names one is a
test running nowhere. `.claude/rules/qa-harness.md` has the rule and the job.
"""

from __future__ import annotations

import os
import re
from collections.abc import Generator

import pytest

#: A skip reason naming one of the package's extras: ``"[pdf]"``, ``pyhermes[data]``.
EXTRA_SKIP = re.compile(r"\[(qa|pdf|data|charts|math|outlook-desktop)\]")

#: Set to any non-empty value to turn such a skip into a failure.
ENV = "PYHERMES_REQUIRE_EXTRAS"


def _fail_if_for_an_extra(report: pytest.TestReport | pytest.CollectReport) -> None:
    """Turn ``report`` from a skip into a failure when ``ENV`` is set and it names an extra."""
    if not (os.environ.get(ENV) and report.skipped) or hasattr(report, "wasxfail"):
        return
    longrepr = report.longrepr
    reason = longrepr[2] if isinstance(longrepr, tuple) else str(longrepr)
    if EXTRA_SKIP.search(reason):
        report.outcome = "failed"
        report.longrepr = f"skipped for an extra this job installs: {reason}"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, None]:
    """A test skipped at setup or in its body: a ``skipif`` mark or ``pytest.skip``."""
    outcome = yield
    _fail_if_for_an_extra(outcome.get_result())


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(
    collector: pytest.Collector,
) -> Generator[None, pytest.CollectReport, None]:
    """A whole module skipped at import, by a module-level ``importorskip``."""
    outcome = yield
    _fail_if_for_an_extra(outcome.get_result())
