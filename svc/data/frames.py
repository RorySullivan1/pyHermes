"""
A pandas DataFrame, as a :class:`~svc.builder.components.DataTable`.

Column kinds come from dtypes, figures go through :mod:`svc.builder.formats`,
and a sign can become a tone, all in one call. pandas is the ``[data]`` extra,
imported only when a frame is actually adapted.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from svc.builder import DataTable
from svc.builder.enums import ColumnKind, RowKind, Tone
from svc.builder.exceptions import ValidationError
from svc.builder.formats import MISSING, number
from svc.builder.models import Cell, Column, TableRow

from .exceptions import BackendMissingError

#: The value a ``tones`` mapping takes to derive each cell's tone from its sign.
AUTO = "auto"


def available() -> bool:
    """Whether pandas is installed, for a caller that wants to skip."""
    try:
        import pandas  # noqa: F401
    except ImportError:
        return False
    return True


def table_from_frame(
    frame: Any,
    *,
    formats: Mapping[Any, Callable[[Any], str]] | None = None,
    tones: Mapping[Any, str] | None = None,
    index: bool | None = None,
    index_label: str = "",
    total_row: bool = False,
    subheads: Mapping[Any, str] | None = None,
    missing: str = MISSING,
    source: str = "",
    as_of: str = "",
    subtitle: str | None = None,
    caption: str = "",
    disclosure: str = "",
) -> DataTable:
    """
    Adapt a DataFrame to a data table: one column per frame column, one row per row.

    Args:
        frame:       The DataFrame. Flat columns and a flat index only.
        formats:     Column → formatter. A numeric column with none uses
                     ``formats.number``: whole if integer, two places if float.
        tones:       Column → ``"auto"`` (the sign decides) or a ``Tone``.
        index:       Include the index as the first, row-header column. ``None``
                     includes it unless it is a default ``RangeIndex``.
        index_label: The index column's heading, if the index has no name.
        total_row:   Mark the last row as a total.
        subheads:    Index label → a subhead inserted before that row.
        missing:     What a missing figure renders as.

    The rest pass through to ``DataTable``. A shape it cannot adapt raises
    ``ValidationError``, by name.
    """
    pd = _backend()
    if not isinstance(frame, pd.DataFrame):
        raise ValidationError(f"table_from_frame takes a DataFrame, got {type(frame).__name__}")
    if isinstance(frame.columns, pd.MultiIndex) or isinstance(frame.index, pd.MultiIndex):
        raise ValidationError("table_from_frame takes flat columns and a flat index; flatten first")
    formats, tones, subheads = dict(formats or {}), dict(tones or {}), dict(subheads or {})
    _check_keys(frame, formats, "formats")
    _check_keys(frame, tones, "tones")

    types = pd.api.types
    numeric = {
        name: types.is_numeric_dtype(frame[name]) and not types.is_bool_dtype(frame[name])
        for name in frame.columns
    }
    for name, tone in tones.items():
        if tone != AUTO and tone not in tuple(Tone):
            raise ValidationError(f"tones[{name!r}] must be 'auto' or a Tone, got {tone!r}")
        if tone == AUTO and not numeric[name]:
            raise ValidationError(f"tones[{name!r}] is 'auto', but {name!r} is not numeric")
    fmt = {
        name: formats.get(name) or _default_format(frame[name], types)
        for name in frame.columns
        if numeric[name]
    }

    with_index = _is_meaningful(frame.index, pd) if index is None else index
    columns = [
        Column(str(name), kind=ColumnKind.NUMERIC if numeric[name] else ColumnKind.TEXT)
        for name in frame.columns
    ]
    if with_index:
        label = index_label or frame.index.name
        if not label:
            raise ValidationError("the index has no name; pass index_label= to head its column")
        columns.insert(0, Column(str(label), kind=ColumnKind.TEXT))

    unknown = set(subheads) - set(frame.index)
    if unknown:
        raise ValidationError(f"subheads names rows the frame does not have: {sorted(unknown)!r}")

    rows: list[TableRow] = []
    for position, (label, *values) in enumerate(frame.itertuples(index=True, name=None)):
        if label in subheads:
            rows.append(TableRow([subheads[label]], kind=RowKind.SUBHEAD))
        cells = [_text_cell(label, missing, pd)] if with_index else []
        for name, value in zip(frame.columns, values, strict=True):
            if not numeric[name]:
                cells.append(_text_cell(value, missing, pd))
            elif pd.isna(value):
                cells.append(Cell(missing))
            else:
                figure = value.item() if hasattr(value, "item") else value
                cells.append(Cell.from_number(figure, fmt[name], tone=tones.get(name, "")))
        last = position == len(frame) - 1
        rows.append(TableRow(cells, kind=RowKind.TOTAL if total_row and last else RowKind.DATA))

    return DataTable(
        headers=list(columns),
        rows=rows,
        source=source,
        as_of=as_of,
        subtitle=subtitle,
        caption=caption,
        disclosure=disclosure,
    )


def _check_keys(frame: Any, mapping: Mapping[Any, Any], name: str) -> None:
    """A typo in a column name raises here rather than silently formatting nothing."""
    unknown = set(mapping) - set(frame.columns)
    if unknown:
        raise ValidationError(f"{name} names columns the frame does not have: {sorted(unknown)!r}")


def _default_format(series: Any, types: Any) -> Callable[[Any], str]:
    places = 0 if types.is_integer_dtype(series) else 2
    return lambda value: number(value, places)


def _is_meaningful(frame_index: Any, pd: Any) -> bool:
    """A default ``RangeIndex`` is row numbering, not data, so it is left out."""
    default = (
        isinstance(frame_index, pd.RangeIndex)
        and frame_index.start == 0
        and frame_index.step == 1
        and frame_index.name is None
    )
    return not default


def _text_cell(value: Any, missing: str, pd: Any) -> Cell:
    return Cell(missing if pd.isna(value) else str(value))


def _backend() -> Any:
    """
    Import pandas, or say what to install.

    Typed ``Any`` for the reason ``svc.pdf``'s backend is: the extra is absent
    where CI runs mypy and present on a developer's machine.
    """
    try:
        import pandas
    except ImportError as exc:
        raise BackendMissingError(
            "Building a table from a DataFrame needs pandas, which is an optional extra. "
            'Install it with: pip install "pyhermes[data]"'
        ) from exc
    return pandas
