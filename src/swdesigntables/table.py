"""The design table model."""

from __future__ import annotations

import io
import os
import warnings
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, TYPE_CHECKING

from swdesigntables.columns import Column, parse_header
from swdesigntables.errors import (
    DesignTableWarning,
    DuplicateColumnError,
    DuplicateConfigurationError,
    ReservedNameError,
    UnknownColumnError,
)
from swdesigntables.validation import (
    INVALID_NAME_CHARACTERS,
    RESERVED_DEFINED_NAMES,
    RESERVED_SHEET_NAMES,
    ValidationReport,
    check,
)
from swdesigntables.values import CellValue, MissingValue, StateFormat
from swdesigntables.vocabulary import DEFAULT_VOCABULARY, Vocabulary

if TYPE_CHECKING:
    from openpyxl import Workbook

__all__ = [
    "DesignTable",
    "Configuration",
    "ExtraSheet",
    "sanitize_configuration_name",
]


@dataclass(frozen=True, slots=True)
class Configuration:
    """One row: a configuration name and its values, keyed by column key."""

    name: str
    values: Mapping[str, CellValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExtraSheet:
    """A sheet beside Sheet1, for notes, source data or a parameter legend."""

    name: str
    rows: tuple[tuple[CellValue, ...], ...]
    hidden: bool = False


def sanitize_configuration_name(name: str, replacement: str = "-") -> str:
    """Return ``name`` with characters SOLIDWORKS rejects replaced.

    Explicitly opt-in. Validation warns about a bad name but never rewrites it:
    a part number is the caller's to decide, not this library's.
    """
    cleaned = "".join(
        replacement if character in INVALID_NAME_CHARACTERS else character
        for character in name
    ).strip()
    if not cleaned:
        raise ValueError(f"Nothing usable left after sanitizing {name!r}")
    return cleaned


class DesignTable:
    """A SOLIDWORKS design table under construction.

    Columns are ordered and immutable once added; the first column added is
    column B. Values are addressed by column identity, never by number, which
    is what makes inserting a column in the middle safe.
    """

    def __init__(
        self,
        model_name: str,
        columns: Iterable[Column | str] = (),
        *,
        output_path: str | os.PathLike[str] | None = None,
        sheet_name: str = "Sheet1",
        vocabulary: Vocabulary = DEFAULT_VOCABULARY,
        state_format: StateFormat = StateFormat.LETTERS,
        missing: MissingValue = MissingValue.BLANK,
        fill_value: CellValue = None,
        round_floats: int | None = None,
        autosize_columns: bool = False,
        strict: bool = True,
        ignore: Sequence[str] = (),
    ) -> None:
        self.model_name = model_name
        self.sheet_name = sheet_name
        self.vocabulary = vocabulary
        self.state_format = state_format
        self.missing = missing
        self.fill_value = fill_value
        self.round_floats = round_floats
        self.autosize_columns = autosize_columns
        self.strict = strict
        self.ignore = tuple(ignore)
        self.output_path = Path(output_path) if output_path is not None else None

        self._columns: list[Column] = []
        self._column_keys: set[str] = set()
        self._headers: dict[str, Column] = {}
        self._configurations: list[Configuration] = []
        self._configuration_names: set[str] = set()
        self._extra_sheets: list[ExtraSheet] = []
        self._defined_names: dict[str, str] = {}

        self.add_columns(columns)

    # --- columns ---------------------------------------------------------

    @property
    def columns(self) -> tuple[Column, ...]:
        """The columns, left to right."""
        return tuple(self._columns)

    def add_column(self, column: Column | str) -> Column:
        """Add one column and return it, so it can be used as a value key."""
        resolved = column if isinstance(column, Column) else parse_header(column, self.vocabulary)
        header = resolved.header(self.vocabulary).lower()
        if header in self._headers:
            self._report(
                DuplicateColumnError,
                "duplicate-column",
                f"Header {resolved.header(self.vocabulary)!r} is already in this table.",
            )
            return self._headers[header]
        self._columns.append(resolved)
        self._column_keys.add(resolved.key)
        self._headers[header] = resolved
        return resolved

    def _ensure_column(self, column: Column) -> Column:
        """Return the matching column, adding it only if it is not there yet."""
        existing = self._headers.get(column.header(self.vocabulary).lower())
        return existing if existing is not None else self.add_column(column)

    def add_columns(self, columns: Iterable[Column | str]) -> tuple[Column, ...]:
        """Add several columns, returning them in order."""
        return tuple(self.add_column(column) for column in columns)

    def headers(self) -> tuple[str, ...]:
        """The rendered row 2 headers, left to right."""
        return tuple(column.header(self.vocabulary) for column in self._columns)

    def column_for(self, header: str) -> Column:
        """Return the column that renders ``header``."""
        try:
            return self._headers[header.strip().lower()]
        except KeyError:
            raise UnknownColumnError(f"No column with header {header!r}") from None

    # --- configurations --------------------------------------------------

    @property
    def configurations(self) -> tuple[Configuration, ...]:
        """The configuration rows, top to bottom."""
        return tuple(self._configurations)

    def add_configuration(
        self,
        name: str,
        values: Mapping[Column | str, CellValue] | None = None,
        *,
        description: str | None = None,
        parent: str | None = None,
    ) -> Configuration:
        """Add one configuration row.

        ``description`` and ``parent`` add their columns on first use, because
        those two are the ones people forget to declare.
        """
        lowered = name.strip().lower()
        if lowered in self._configuration_names:
            self._report(
                DuplicateConfigurationError,
                "duplicate-configuration",
                f"Configuration {name!r} is already in this table.",
            )

        resolved: dict[str, CellValue] = {}
        for key, value in (values or {}).items():
            column = key if isinstance(key, Column) else self._resolve_header(key)
            if column is None:
                continue
            resolved[column.key] = value

        if description is not None:
            from swdesigntables.columns import description as description_column

            resolved[self._ensure_column(description_column()).key] = description
        if parent is not None:
            from swdesigntables.columns import parent as parent_column

            resolved[self._ensure_column(parent_column()).key] = parent

        configuration = Configuration(name=name, values=resolved)
        self._configurations.append(configuration)
        self._configuration_names.add(lowered)
        return configuration

    def _resolve_header(self, header: str) -> Column | None:
        lowered = header.strip().lower()
        if lowered in self._headers:
            return self._headers[lowered]
        self._report(
            UnknownColumnError,
            "unknown-column",
            f"No column with header {header!r}. Add it before supplying values for it.",
        )
        return None

    # --- extras ----------------------------------------------------------

    @property
    def extra_sheets(self) -> tuple[ExtraSheet, ...]:
        """The sheets beside Sheet1."""
        return tuple(self._extra_sheets)

    def add_sheet(
        self,
        name: str,
        rows: Sequence[Sequence[CellValue]],
        *,
        hidden: bool = False,
    ) -> ExtraSheet:
        """Add a sheet beside Sheet1, optionally hidden.

        ``_SWX`` is rejected: SOLIDWORKS creates that sheet itself when it
        embeds the table, and authoring one produces a table it cannot
        reconcile.
        """
        if name.upper() in {reserved.upper() for reserved in RESERVED_SHEET_NAMES}:
            self._report(
                ReservedNameError,
                "reserved-sheet-name",
                "'_SWX' is generated by SOLIDWORKS when it embeds the table. "
                "Authoring it here produces a table SOLIDWORKS cannot "
                "reconcile. Use a different sheet name.",
            )
        sheet = ExtraSheet(
            name=name,
            rows=tuple(tuple(row) for row in rows),
            hidden=hidden,
        )
        self._extra_sheets.append(sheet)
        return sheet

    @property
    def defined_names(self) -> Mapping[str, str]:
        """The extra defined names, excluding the automatic ``Family``."""
        return dict(self._defined_names)

    def add_defined_name(self, name: str, ref: str) -> None:
        """Add a workbook-level defined name, as in ``Sheet1!$B$3:$B$50``."""
        if name in RESERVED_DEFINED_NAMES:
            self._report(
                ReservedNameError,
                "reserved-defined-name",
                f"{name!r} is reserved. 'Family' is created automatically and "
                "'_SWX_0' belongs to SOLIDWORKS.",
            )
            return
        self._defined_names[name] = ref

    # --- ordering --------------------------------------------------------

    def sort_by_parent(self) -> None:
        """Reorder rows so every derived configuration follows its parent.

        Never automatic: row order is configuration order in the SOLIDWORKS
        tree, and silently changing it is not this library's call.
        """
        parent_columns = [c for c in self._columns if c.spec.name == "parent"]
        if not parent_columns:
            return
        key = parent_columns[0].key
        remaining = list(self._configurations)
        placed: list[Configuration] = []
        placed_names: set[str] = set()
        while remaining:
            progressed = False
            for configuration in list(remaining):
                parent = configuration.values.get(key)
                parent_name = str(parent).strip().lower() if parent else ""
                if not parent_name or parent_name in placed_names:
                    placed.append(configuration)
                    placed_names.add(configuration.name.strip().lower())
                    remaining.remove(configuration)
                    progressed = True
            if not progressed:
                # A cycle or a missing parent; validation reports it properly.
                placed.extend(remaining)
                break
        self._configurations = placed

    # --- output ----------------------------------------------------------

    def validate(self) -> ValidationReport:
        """Return every issue found, without writing anything."""
        return check(self)

    def to_workbook(self) -> Workbook:
        """Return the openpyxl workbook, after validating."""
        from swdesigntables.writer import build_workbook

        self._enforce(self.validate())
        return build_workbook(self)

    def save(self, target: str | os.PathLike[str] | IO[bytes] | None = None) -> Path | None:
        """Write the table. Returns the path written, or None for a stream.

        With no argument, writes to ``output_path``.
        """
        destination = target if target is not None else self.output_path
        if destination is None:
            raise ValueError(
                "No target given and no output_path set on this table."
            )
        workbook = self.to_workbook()
        if hasattr(destination, "write"):
            workbook.save(destination)  # type: ignore[arg-type]
            return None
        path = Path(destination)  # type: ignore[arg-type]
        path.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(path)
        return path

    def to_bytes(self) -> bytes:
        """Return the .xlsx as bytes, for callers with no filesystem."""
        buffer = io.BytesIO()
        self.to_workbook().save(buffer)
        return buffer.getvalue()

    # --- strictness ------------------------------------------------------

    def _report(self, error_class: type[Exception], code: str, message: str) -> None:
        """Raise or warn, depending on strictness and the ignore list."""
        if code in self.ignore:
            return
        if self.strict:
            raise error_class(message)
        warnings.warn(f"{code}: {message}", DesignTableWarning, stacklevel=3)

    def _enforce(self, report: ValidationReport) -> None:
        for issue in report.warnings:
            warnings.warn(str(issue), DesignTableWarning, stacklevel=3)
        if not self.strict:
            for issue in report.errors:
                warnings.warn(str(issue), DesignTableWarning, stacklevel=3)
            return
        report.raise_for_errors()

    def __repr__(self) -> str:
        return (
            f"DesignTable(model_name={self.model_name!r}, "
            f"columns={len(self._columns)}, configurations={len(self._configurations)})"
        )
