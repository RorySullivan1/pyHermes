"""
The package's old import name, kept for one release (#248). Use ``pyhermes``.

``import svc.builder`` returns the very module ``pyhermes.builder`` is, so a
class imported under either name is the same class. Importing it warns once.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import sys
import warnings
from collections.abc import Sequence
from types import ModuleType

warnings.warn(
    "the svc package is now pyhermes: import pyhermes.builder (and so on) instead. "
    "svc will be removed in the next release.",
    DeprecationWarning,
    stacklevel=2,
)

#: A package with no directory of its own: every submodule is found by the finder below.
__path__ = []


class _Alias(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Resolves ``svc.<name>`` to the already-importable ``pyhermes.<name>``."""

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if not fullname.startswith("svc."):
            return None
        return importlib.machinery.ModuleSpec(fullname, self)

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> ModuleType:
        module = importlib.import_module("pyhermes." + spec.name.removeprefix("svc."))
        spec.loader_state = module.__spec__
        return module

    def exec_module(self, module: ModuleType) -> None:
        # The import system has just overwritten __spec__ with this alias's
        # spec, which is no package; importlib.resources then refuses the
        # templates. Put the real one back. The module itself already ran.
        spec = module.__spec__
        if spec is not None and spec.loader_state is not None:
            module.__spec__ = spec.loader_state


if not any(isinstance(finder, _Alias) for finder in sys.meta_path):
    sys.meta_path.insert(0, _Alias())
