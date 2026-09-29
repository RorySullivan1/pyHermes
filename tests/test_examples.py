"""
The worked examples, and the README's two headline programs, actually run.

Documentation rots silently: a rename lands, the suite stays green, and the
first thing a new reader copies is the one thing that no longer works. These
are the cheapest guard against that — they execute the code rather than
reading it.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import tempfile
from pathlib import Path

import pytest

from pyhermes.data.exceptions import BackendMissingError as _DataMissing
from pyhermes.math.exceptions import BackendMissingError as _MathMissing

#: An example that needs an extra skips without it: [charts] or [math] (#233).
DataBackendMissing = (_DataMissing, _MathMissing)

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = sorted(REPO_ROOT.glob("examples/*/*.py"))
README = REPO_ROOT / "README.md"


def _pdf_available() -> bool:
    """Whether this environment can print. Used to skip, never to fail."""
    from pyhermes.pdf import available

    return available()


def _load(path: Path):
    """Import an example by path, without requiring it to be a package."""
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _python_blocks(markdown: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", markdown, re.S)


def _block_after(heading: str) -> str:
    """The first fenced Python block following ``heading`` in the README."""
    text = README.read_text(encoding="utf-8")
    index = text.index(heading)
    blocks = _python_blocks(text[index:])
    assert blocks, f"no python block follows {heading!r}"
    return blocks[0]


def _run(source: str, label: str) -> None:
    """Execute a snippet in a scratch directory, so it may write files."""
    previous = os.getcwd()
    with tempfile.TemporaryDirectory() as scratch:
        os.chdir(scratch)
        try:
            exec(compile(source, label, "exec"), {"__name__": "__snippet__"})
        finally:
            os.chdir(previous)


def _build(path):
    """
    Build the example at ``path``, or skip if it needs an absent extra.

    ``fund-factsheet`` plots through ``[charts]``, which ``pip install -e
    ".[dev]"`` deliberately does not bring: a table author should not have to
    install a plotting library. So an example that needs a backend **skips**
    here rather than failing, on exactly the reasoning the PDF tests already
    use — a suite that fails without an optional extra is a suite claiming the
    extra is not optional. CI's `data` job installs ``[charts]`` and runs this
    file, so the skip never becomes a hole.
    """
    try:
        return _load(path).build()
    except DataBackendMissing as exc:  # pragma: no cover - depends on the install
        pytest.skip(f"{path.name} needs an optional extra: {exc}")


class TestEveryExampleBuilds:
    def test_the_directory_is_not_empty(self):
        assert EXAMPLES, "examples/ has no scripts; this test would pass vacuously"

    @pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
    def test_it_imports_and_builds(self, path):
        assert _build(path).render(), f"{path.name} built nothing"

    @pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
    def test_it_is_deterministic(self, path):
        # The rule the fixture gallery rests on, applied to the examples: a
        # script that reads a clock cannot be shown beside its own output.
        first = _build(path).render()
        assert first == _load(path).build().render()

    def test_both_media_are_represented(self):
        media = {_build(path).medium.name for path in EXAMPLES}
        assert {"email", "document"} <= media, (
            f"the examples only cover {sorted(media)}; a reader has no worked "
            "example of the other medium"
        )


class TestTheReadmesHeadlinePrograms:
    """
    Only the blocks the README presents as complete programs.

    **Not every fenced block**, deliberately. Most are illustrative fragments
    — ``{..., "language": "fr"}`` is prose, not Python, and several
    deliberately reference an ``email`` built in an earlier block or read an
    image path that does not exist. A check that demanded all twenty run
    would be wrong about its own scope, and the fix would be to ruin correct
    documentation to satisfy it.
    """

    def test_the_email_quickstart_runs(self):
        _run(_block_after("# pyHermes"), "README: quickstart")

    @pytest.mark.skipif(
        not _pdf_available(),
        reason='the README\'s paged block ends in save_pdf; that is the "[pdf]" extra',
    )
    def test_the_paged_example_runs(self):
        _run(_block_after("## The same content, printed"), "README: paged")

    def test_the_paged_example_builds_without_the_extra(self):
        # The half that needs nothing installed: everything up to save_pdf.
        source = _block_after("## The same content, printed")
        _run(source.split("save_pdf(document")[0], "README: paged (no extra)")

    @pytest.mark.skipif(
        not _pdf_available(),
        reason='the README\'s attachment renders a PDF; that is the "[pdf]" extra',
    )
    def test_the_sent_as_a_pdf_example_runs(self):
        _run(_block_after("## Sent as a PDF"), "README: sent as a PDF")

    def test_the_sent_as_a_pdf_example_builds_without_the_extra(self):
        # Both documents build with nothing installed; only the attachment prints.
        source = _block_after("## Sent as a PDF")
        _run(source.split("message = build_message(")[0], "README: sent as a PDF (no extra)")

    @pytest.mark.skipif(
        not _pdf_available(),
        reason='the README\'s brochure block ends in save_pdf; that is the "[pdf]" extra',
    )
    def test_the_brochure_example_runs(self):
        _run(_block_after("## The same content, folded"), "README: brochure")

    def test_the_brochure_example_builds_without_the_extra(self):
        source = _block_after("## The same content, folded")
        _run(source.split("save_pdf(brochure")[0], "README: brochure (no extra)")

    def test_the_illustrative_fragments_say_so(self):
        # The teeth on the exemption: a block that does not parse must be
        # visibly pseudo-code. One that does not parse and has no ellipsis is
        # a real syntax error hiding among them.
        for index, block in enumerate(_python_blocks(README.read_text(encoding="utf-8"))):
            try:
                ast.parse(block)
            except SyntaxError:
                assert "..." in block, f"README block {index} is broken, not illustrative"


class TestTheFactsheetIsTwoSheets:
    """
    The one example whose *shape* is part of its specification.

    Every other example may grow a section without anyone minding. A factsheet
    may not: two sheets is the format. It drifted to five and to three while
    being built -- a default ``BackMatter`` region quietly spending a sheet,
    then a single extra sentence of fine print -- so the count is pinned here
    rather than left to whoever next re-renders it.
    """

    FACTSHEET = REPO_ROOT / "examples" / "fund-factsheet" / "fund-factsheet.py"

    def test_the_example_is_still_there(self):
        assert self.FACTSHEET in EXAMPLES, "the factsheet example has moved or been renamed"

    def test_it_lays_out_to_exactly_two_sheets(self):
        from pyhermes.pdf import available as pdf_available

        if not pdf_available():
            pytest.skip('laying a document onto sheets needs the "[pdf]" extra')
        from pyhermes.pdf import page_count

        module = _load(self.FACTSHEET)
        try:
            document = module.build()
        except DataBackendMissing as exc:  # pragma: no cover - depends on the install
            pytest.skip(f"the factsheet needs an optional extra: {exc}")
        assert page_count(document) == module.SHEETS == 2
