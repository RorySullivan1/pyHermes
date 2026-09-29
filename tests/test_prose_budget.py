"""The prose-budget gate: this repo's caps, its shrinking baseline, and the ratchet.

The measurement itself lives in ``.claude/hooks/prose_budget.py`` (#142) and is shared
with the edit-time hook, so a CI failure and an in-session notice cannot disagree about
the rule. What is here is the half that is this repository's: the caps in
``.claude/prose-budget.json``, chosen by reading real docstrings rather than by
percentile, and the baseline of what predates them.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: Locations exempt today. It may only shrink: #138 empties pyhermes/, #139 empties qa/.
BASELINE_PATH = ROOT / "qa" / "prose_baseline.json"


def _measurer() -> ModuleType:
    """Import the hook script by path — .claude/hooks is not an importable package."""
    spec = importlib.util.spec_from_file_location(
        "prose_budget", ROOT / ".claude" / "hooks" / "prose_budget.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Registered before exec: its dataclasses resolve their own __module__ through
    # sys.modules, and a module absent from it fails at class-creation time.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pb = _measurer()


class TestTheBudgetIsAdopted:
    def test_the_config_is_the_adoption_marker(self) -> None:
        assert pb.load_budgets(ROOT) is not None, (
            ".claude/prose-budget.json is missing — without it every entry point is "
            "silent by design, and this gate would pass while measuring nothing."
        )

    def test_the_caps_are_this_repo_s_own(self) -> None:
        budgets = pb.load_budgets(ROOT)
        assert (budgets.module, budgets.cls, budgets.function, budgets.comment_run) == (
            16,
            28,
            18,
            4,
        )


class TestTheTreeIsWithinBudget:
    def test_nothing_unbaselined_is_over(self) -> None:
        findings = pb.scan_tree(ROOT)
        assert not findings, "prose over budget and not baselined:\n" + "\n".join(
            f"  {f.describe()}" for f in findings
        )


class TestTheBaselineIsARatchet:
    """A baseline entry that stopped violating hides the next one — #132's shape."""

    @staticmethod
    def _all_violations() -> set[str]:
        budgets = pb.load_budgets(ROOT)
        return {f.location for f in pb.scan_tree(ROOT, pb.replace(budgets, baseline=frozenset()))}

    def test_every_entry_still_violates(self) -> None:
        stale = sorted(set(json.loads(BASELINE_PATH.read_text())) - self._all_violations())
        assert not stale, "baseline entries that no longer violate — delete them:\n" + "\n".join(
            f"  {location}" for location in stale
        )

    def test_every_entry_carries_a_reason(self) -> None:
        entries = json.loads(BASELINE_PATH.read_text())
        assert all(isinstance(v, str) and v.strip() for v in entries.values())


class TestTheGateBites:
    """Perturbation, both directions. A guard proved only against correct code is not one."""

    @staticmethod
    def _over_budget_source() -> str:
        body = "\n".join(f"    L{i}" for i in range(30))
        return f'"""Purpose.\n\n{body}\n"""\n'

    def test_an_over_budget_module_is_found(self, tmp_path: Path) -> None:
        budgets = pb.load_budgets(ROOT)
        findings = pb.scan_source(self._over_budget_source(), "probe.py", budgets)
        assert [f.scope for f in findings] == ["module"]
        assert findings[0].measured > budgets.module

    def test_a_compliant_module_is_not(self) -> None:
        budgets = pb.load_budgets(ROOT)
        assert pb.scan_source('"""Purpose, stated."""\n', "probe.py", budgets) == []

    @pytest.mark.parametrize(
        "location",
        [
            "pyhermes/builder/email.py::function:Email.render",
            "pyhermes/gmail/__init__.py::module:__init__.py",
        ],
    )
    def test_the_read_examples_pass_on_their_merits(self, location: str) -> None:
        """The caps were chosen so these stay legal — not baselined into legality."""
        assert location not in json.loads(BASELINE_PATH.read_text())
        path, _, rest = location.partition("::")
        scope, _, name = rest.partition(":")
        budgets = pb.load_budgets(ROOT)
        over = pb.scan_source(
            (ROOT / path).read_text(), path, pb.replace(budgets, baseline=frozenset())
        )
        assert not [f for f in over if f.scope == scope and f.name == name]
