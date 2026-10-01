"""
Load a document from ``path/to/module.py:callable``, the form the check command takes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from pyhermes.builder import EmailBuilder
from pyhermes.builder.document import Document
from pyhermes.builder.exceptions import EmailBuilderError


class TargetError(RuntimeError):
    """A target that names no file, no callable, or nothing that builds a document."""


def load_target(target: str) -> tuple[str, Document]:
    """
    ``(name, document)`` from ``path/to/module.py:callable``.

    Split on the last colon, so a Windows drive letter is not the separator.
    The callable takes no arguments and returns a ``Document``, an ``Email``
    or an ``EmailBuilder``. The name is ``{stem}-{callable}``, so two files
    that both define ``build`` do not overwrite each other's output.

    Raises:
        TargetError: For a missing file or callable, or one that fails to import.
        EmailBuilderError: When the builder rejects the email; its message names the field.
    """
    path_text, _, attribute = target.rpartition(":")
    path = Path(path_text)
    if not path_text or not attribute:
        raise TargetError(f"{target!r} names no callable. Expected path/to/module.py:callable.")
    if not path.is_file():
        raise TargetError(f"No such file: {path}")

    module_name = f"_pyhermes_target_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise TargetError(f"{path} is not importable as Python.")
    module = importlib.util.module_from_spec(spec)
    # Registered first: a dataclass in the module looks itself up by __module__.
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except EmailBuilderError:
        raise
    except Exception as exc:
        raise TargetError(f"{path} failed to import: {exc}") from exc

    builder = getattr(module, attribute, None)
    if builder is None:
        raise TargetError(f"{path} has no attribute {attribute!r}.")
    if not callable(builder):
        raise TargetError(f"{attribute!r} in {path} is not callable.")
    name = f"{path.stem}-{attribute}"
    return name, as_document(builder(), name)


def as_document(value: object, name: str) -> Document:
    """``value`` as a ``Document``: an ``EmailBuilder`` is built, anything else is refused."""
    if isinstance(value, EmailBuilder):
        return value.build()
    if isinstance(value, Document):
        return value
    raise TargetError(
        f"{name} returned {type(value).__name__}, not a Document, Email or EmailBuilder."
    )
