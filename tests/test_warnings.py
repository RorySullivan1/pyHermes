"""
The library's soft limits arrive as warnings a host can filter, and it never prints (#246).
"""

from __future__ import annotations

import ast
import warnings
from pathlib import Path

import pytest

from pyhermes.builder import PrintQualityWarning, SizeError, SizeWarning
from pyhermes.config import config_override
from qa.fixtures import kitchen_sink

SVC = Path(__file__).resolve().parent.parent / "pyhermes"


def _print_calls(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ]


def test_no_module_in_the_package_calls_print():
    offenders = {
        str(path.relative_to(SVC.parent)): lines
        for path in sorted(SVC.rglob("*.py"))
        if (lines := _print_calls(path))
    }
    assert not offenders, f"print() in the library writes into a host's stdout: {offenders}"


def test_both_categories_are_user_warnings_a_host_can_filter():
    assert issubclass(SizeWarning, UserWarning)
    assert issubclass(PrintQualityWarning, UserWarning)


def test_a_render_under_the_thresholds_writes_nothing_and_warns_nothing(capsys):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        kitchen_sink.build().render()
    assert capsys.readouterr().out == ""


class TestTheSizeWarning:
    def test_it_is_raised_once_with_the_size_and_the_target(self):
        with config_override(size_warn_kb=1), pytest.warns(SizeWarning) as caught:
            kitchen_sink.build().render()
        (warning,) = [w for w in caught if w.category is SizeWarning]
        assert "target < 1 KB" in str(warning.message)

    @pytest.mark.parametrize("via", ["email", "builder"])
    def test_it_points_at_the_callers_line_not_the_library(self, via):
        # A fixed stacklevel would name a frame inside pyhermes/ for one of these.
        email = kitchen_sink.build()
        render = email.render if via == "email" else _builder_of(email).render
        with config_override(size_warn_kb=1), pytest.warns(SizeWarning) as caught:
            render()
        assert Path(caught[0].filename).resolve() == Path(__file__).resolve()

    def test_a_host_can_promote_it_to_an_error(self):
        with config_override(size_warn_kb=1), warnings.catch_warnings():
            warnings.simplefilter("error", SizeWarning)
            with pytest.raises(SizeWarning):
                kitchen_sink.build().render()

    def test_the_hard_limit_still_raises_its_exception_under_error_filtering(self):
        tiny = {"size_limit_kb": 1, "size_warn_kb": 1, "inline_image_limit_kb": 1}
        with config_override(**tiny), warnings.catch_warnings():
            warnings.simplefilter("error")
            with pytest.raises(SizeError):
                kitchen_sink.build().render()


def _builder_of(email):
    from pyhermes.builder import EmailBuilder

    builder = EmailBuilder()
    builder._email = email
    return builder
