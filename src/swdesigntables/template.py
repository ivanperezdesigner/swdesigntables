"""Reusable table bases.

A :class:`TableTemplate` holds everything about a family of parts that does
not change row to row: which model the table belongs to, where the file goes,
what it is called, which columns it has, and how configurations are named.
Define it once per family and every script in the project starts from the same
base instead of retyping it.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from swdesigntables.columns import Column
from swdesigntables.table import DesignTable
from swdesigntables.values import CellValue, MissingValue, StateFormat
from swdesigntables.vocabulary import DEFAULT_VOCABULARY, Vocabulary

__all__ = ["TableTemplate", "blank_table"]


@dataclass(frozen=True, slots=True)
class TableTemplate:
    """The reusable base for one family of design tables.

    Frozen on purpose: :meth:`replace` gives you a variant without mutating a
    template other scripts may be importing.
    """

    model_name: str
    columns: tuple[Column, ...] = ()
    output_dir: Path | None = None
    file_name: str | None = None
    sheet_name: str = "Sheet1"
    vocabulary: Vocabulary = DEFAULT_VOCABULARY
    state_format: StateFormat = StateFormat.LETTERS
    missing: MissingValue = MissingValue.BLANK
    fill_value: CellValue = None
    round_floats: int | None = None
    autosize_columns: bool = False
    strict: bool = True
    ignore: tuple[str, ...] = ()
    config_name: Callable[..., str] | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "columns", tuple(self.columns))
        object.__setattr__(self, "ignore", tuple(self.ignore))
        if self.output_dir is not None:
            object.__setattr__(self, "output_dir", Path(self.output_dir))

    @property
    def output_path(self) -> Path | None:
        """Where :meth:`DesignTable.save` writes when called with no argument."""
        if self.file_name is None:
            return None
        directory = self.output_dir or Path.cwd()
        return directory / self.file_name

    def new_table(self, **overrides: object) -> DesignTable:
        """Return a fresh, empty table carrying this template's settings."""
        settings: dict[str, object] = {
            "output_path": self.output_path,
            "sheet_name": self.sheet_name,
            "vocabulary": self.vocabulary,
            "state_format": self.state_format,
            "missing": self.missing,
            "fill_value": self.fill_value,
            "round_floats": self.round_floats,
            "autosize_columns": self.autosize_columns,
            "strict": self.strict,
            "ignore": self.ignore,
        }
        settings.update(overrides)
        model_name = str(settings.pop("model_name", self.model_name))
        columns = settings.pop("columns", self.columns)
        return DesignTable(model_name, columns, **settings)  # type: ignore[arg-type]

    def name_for(self, *args: object, **kwargs: object) -> str:
        """Build a configuration name using this template's naming rule."""
        if self.config_name is None:
            raise ValueError(
                f"Template for {self.model_name!r} has no config_name rule. "
                "Pass config_name=... to use name_for()."
            )
        return self.config_name(*args, **kwargs)

    def replace(self, **changes: object) -> TableTemplate:
        """Return a copy of this template with some fields changed."""
        return replace(self, **changes)  # type: ignore[arg-type]


def blank_table(
    model_name: str,
    columns: Iterable[Column | str] = (),
    path: str | os.PathLike[str] | None = None,
    *,
    sheet_name: str = "Sheet1",
    vocabulary: Vocabulary = DEFAULT_VOCABULARY,
    configurations: Sequence[str] = (),
) -> DesignTable:
    """Build a valid but empty design table, ready to fill in by hand.

    Useful twice: as a starting point for someone who would rather type rows in
    Excel, and as the cheapest way to find out whether SOLIDWORKS accepts a set
    of headers before writing a generator around them. Insert it with
    Insert > Tables > Design Table > From file and see what it says.
    """
    table = DesignTable(
        model_name,
        columns,
        sheet_name=sheet_name,
        vocabulary=vocabulary,
        ignore=("no-configurations",),
    )
    for name in configurations:
        table.add_configuration(name)
    if path is not None:
        table.save(path)
    return table
