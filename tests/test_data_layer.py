"""
The data adapters are optional, and these tests are what prove it (#179, #180).

They need no extra installed, so they run in the ``[dev]``-only CI job, which
is the environment the claim is about. The adapters' own behaviour is tested in
``test_frames.py`` and ``test_charts.py``, which skip without their extras.
"""

import ast
import builtins
import pathlib

import pytest

#: What only ``svc.data`` may import, and only inside a function.
_OPTIONAL = {"pandas", "matplotlib", "numpy"}


def _imports(path: pathlib.Path, *, module_level_only: bool = False) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = tree.body if module_level_only else list(ast.walk(tree))
    names: set[str] = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module)
    return names


class TestTheCoreNeverImportsTheAdapters:
    """
    The one-way dependency: ``svc.data`` imports the builder, never the reverse.

    This is why there is no ``DataTable.from_frame``. A lazy import inside a
    builder method would still be the builder importing ``svc.data``, and the
    rule would then be enforced nowhere.
    """

    @pytest.mark.parametrize(
        "package", ["svc/builder", "svc/document", "svc/email", "svc/delivery", "svc/pdf"]
    )
    def test_no_core_module_imports_an_optional_backend_or_the_adapters(self, package):
        for path in sorted(pathlib.Path(package).rglob("*.py")):
            roots = {name.split(".")[0] for name in _imports(path)}
            assert not roots & _OPTIONAL, f"{path} imports {roots & _OPTIONAL}"
            assert not any(name.startswith("svc.data") for name in _imports(path)), path

    def test_the_adapters_import_their_backends_lazily(self):
        for path in sorted(pathlib.Path("svc/data").glob("*.py")):
            roots = {name.split(".")[0] for name in _imports(path, module_level_only=True)}
            assert not roots & _OPTIONAL, f"{path} imports {roots & _OPTIONAL} at module level"


class TestAMissingBackendNamesTheInstall:
    @pytest.fixture
    def refuse(self, monkeypatch):
        real_import = builtins.__import__

        def refuse(name, *args, **kwargs):
            if name.split(".")[0] in _OPTIONAL:
                raise ImportError(f"no {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", refuse)

    def test_the_package_imports_without_any_extra(self, refuse):
        import importlib

        import svc.data

        importlib.reload(svc.data)

    def test_a_frame_without_pandas_says_install_data(self, refuse):
        from svc.data import BackendMissingError, table_from_frame

        with pytest.raises(BackendMissingError, match=r"pyhermes\[data\]"):
            table_from_frame(object())

    def test_a_figure_without_matplotlib_says_install_charts(self, refuse):
        from svc.data import BackendMissingError, image_from_figure

        with pytest.raises(BackendMissingError, match=r"pyhermes\[charts\]"):
            image_from_figure(object(), alt="Chart", width=320)

    def test_availability_reports_each_backend(self, refuse):
        from svc.data import charts_available, frames_available

        assert frames_available() is False
        assert charts_available() is False


def test_the_extras_are_declared_separately():
    """A table author should not have to install a plotting library."""
    import tomllib

    extras = tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"][
        "optional-dependencies"
    ]
    assert any(dep.startswith("pandas") for dep in extras["data"])
    assert not any(dep.startswith("matplotlib") for dep in extras["data"])
    assert any(dep.startswith("matplotlib") for dep in extras["charts"])
    assert not any(dep.startswith("pandas") for dep in extras["charts"])


def test_mypy_ignores_both_spellings_of_each_backend():
    """
    The #157 lesson: a ``foo.*`` pattern matches submodules only, so ``import
    foo`` needs the bare name too, or mypy is green locally and red in CI.
    """
    import tomllib

    overrides = tomllib.loads(pathlib.Path("pyproject.toml").read_text())["tool"]["mypy"][
        "overrides"
    ]
    modules = {name for block in overrides for name in block["module"]}
    for backend in ("pandas", "matplotlib", "numpy"):
        assert {backend, f"{backend}.*"} <= modules, backend


def test_mypy_skips_the_backends_rather_than_reading_them():
    """
    ``ignore_missing_imports`` covers only the *absent* case. With the extras
    installed, mypy followed matplotlib into numpy 2.5's stubs, which use the
    3.12 ``type`` statement, and failed at ``python_version = "3.11"``. That
    failure appeared only in CI's ``data`` job. Skipping makes the installed and
    absent cases one check.
    """
    import tomllib

    overrides = tomllib.loads(pathlib.Path("pyproject.toml").read_text())["tool"]["mypy"][
        "overrides"
    ]
    for backend in ("pandas", "matplotlib", "numpy"):
        block = next(b for b in overrides if backend in b["module"])
        assert block.get("follow_imports") == "skip", backend
        # Without this, mypy ignores the skip for .pyi stubs, which both ship.
        assert block.get("follow_imports_for_stubs") is True, backend
