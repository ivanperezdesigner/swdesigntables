"""Validation of a built table.

Pure functions over the table model: no file is written and no openpyxl object
is created, so a caller can inspect problems before committing to output.

What this catches is shape, not truth. Without a live model there is nothing to
check feature names against, so a misspelled feature still produces a column
SOLIDWORKS silently ignores. Promising otherwise is how people learn to skip
warnings.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from swdesigntables.columns import Column
from swdesigntables.errors import ValidationError
from swdesigntables.parameters import Status, ValueKind
from swdesigntables.values import (
    ComponentState,
    Expression,
    MissingValue,
    State,
    YesNo,
)

if TYPE_CHECKING:
    from swdesigntables.table import DesignTable

__all__ = ["Severity", "Issue", "ValidationReport", "check"]

# Characters SOLIDWORKS rejects in a configuration name.
INVALID_NAME_CHARACTERS = set('/\\:*?"<>|')
RESERVED_SHEET_NAMES = frozenset({"_SWX"})
RESERVED_DEFINED_NAMES = frozenset({"Family", "_SWX_0"})
MAX_CONFIGURATION_NAME = 255
LONG_CONFIGURATION_NAME = 128


class Severity(Enum):
    """Whether an issue stops the write or merely warns about it."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Issue:
    """One validation finding.

    ``code`` is stable across releases; message wording is not. Match on the
    code when you suppress or assert on an issue.
    """

    severity: Severity
    code: str
    message: str
    location: str | None = None

    def __str__(self) -> str:
        where = f" [{self.location}]" if self.location else ""
        return f"{self.severity.value}: {self.code}{where}: {self.message}"


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """The findings for one table."""

    issues: tuple[Issue, ...] = ()

    @property
    def errors(self) -> tuple[Issue, ...]:
        """Every issue that would stop the file being written."""
        return tuple(i for i in self.issues if i.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[Issue, ...]:
        """Every issue that is probably a mistake but does not stop the write."""
        return tuple(i for i in self.issues if i.severity is Severity.WARNING)

    def __bool__(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        """Raise :class:`ValidationError` if any error was found."""
        errors = self.errors
        if not errors:
            return
        detail = "\n".join(f"  - {issue}" for issue in errors)
        raise ValidationError(
            f"Design table has {len(errors)} error(s):\n{detail}", report=self
        )


def check(table: DesignTable) -> ValidationReport:
    """Return every issue found in ``table``."""
    issues: list[Issue] = []
    issues += _check_structure(table)
    issues += _check_columns(table)
    issues += _check_configurations(table)
    issues += _check_values(table)
    issues += _check_parents(table)
    issues += _check_sheets(table)
    ignored = set(table.ignore)
    return ValidationReport(tuple(i for i in issues if i.code not in ignored))


def _error(code: str, message: str, location: str | None = None) -> Issue:
    return Issue(Severity.ERROR, code, message, location)


def _warn(code: str, message: str, location: str | None = None) -> Issue:
    return Issue(Severity.WARNING, code, message, location)


def _check_structure(table: DesignTable) -> list[Issue]:
    issues: list[Issue] = []
    if not table.model_name.strip():
        issues.append(
            _error("empty-model-name", "The model name in A1 cannot be empty.", "A1")
        )
    if not table.columns:
        issues.append(
            _error("no-columns", "A design table needs at least one column.", "B2")
        )
    if not table.configurations:
        issues.append(
            _error(
                "no-configurations",
                "A design table needs at least one configuration row.",
                "A3",
            )
        )
    return issues


def _check_columns(table: DesignTable) -> list[Issue]:
    issues: list[Issue] = []
    seen: dict[str, int] = {}
    for index, col in enumerate(table.columns):
        header = col.header(table.vocabulary)
        lowered = header.lower()
        if lowered in seen:
            issues.append(
                _error(
                    "duplicate-column",
                    f"Header {header!r} is already used by column "
                    f"{seen[lowered] + 1}. SOLIDWORKS reads the first and "
                    "ignores the rest.",
                    header,
                )
            )
        else:
            seen[lowered] = index
        if col.status is not Status.VERIFIED:
            issues.append(
                _warn(
                    "unverified-parameter"
                    if col.spec.name != "raw"
                    else "raw-column",
                    f"Parameter {col.spec.name!r} is {col.status.value}, not "
                    "confirmed against a real model. Verify it with "
                    "Insert > Tables > Design Table > Auto-create.",
                    header,
                )
            )
        issues += _check_target_names(col, header)
    issues += _check_equation_conflicts(table)
    return issues


def _check_target_names(col: Column, header: str) -> list[Issue]:
    issues: list[Issue] = []
    for name, value in col.args:
        if name == "text":
            continue
        if value != value.strip():
            issues.append(
                _warn(
                    "suspicious-feature-name",
                    f"{name.capitalize()} {value!r} has leading or trailing "
                    "whitespace, which will not match anything in the model.",
                    header,
                )
            )
        if "@" in value:
            issues.append(
                _warn(
                    "suspicious-feature-name",
                    f"{name.capitalize()} {value!r} contains '@', which "
                    "usually means the header was assembled twice.",
                    header,
                )
            )
    return issues


def _check_equation_conflicts(table: DesignTable) -> list[Issue]:
    """Warn when a dimension and a global variable of the same name collide.

    A dimension governed by an equation cannot be driven from the table: the
    equation overwrites the value on rebuild. Having both columns present is
    the usual sign that someone expected the dimension column to win.
    """
    variables = {
        dict(col.args)["variable"].lower()
        for col in table.columns
        if col.spec.name == "global_variable"
    }
    issues: list[Issue] = []
    for col in table.columns:
        if col.spec.name != "dimension":
            continue
        name = dict(col.args)["dimension"]
        if name.lower() in variables:
            issues.append(
                _warn(
                    "equations-dimension-conflict",
                    f"Both a dimension and a global variable named {name!r} "
                    "are driven. If an equation governs the dimension, the "
                    "dimension column does nothing.",
                    col.header(table.vocabulary),
                )
            )
    return issues


def _check_configurations(table: DesignTable) -> list[Issue]:
    issues: list[Issue] = []
    seen: set[str] = set()
    for config in table.configurations:
        name = config.name
        location = f"configuration {name!r}"
        if not name.strip():
            issues.append(
                _error(
                    "invalid-configuration-name",
                    "A configuration name cannot be empty.",
                    location,
                )
            )
            continue
        if name != name.strip():
            issues.append(
                _error(
                    "invalid-configuration-name",
                    f"Configuration name {name!r} has leading or trailing whitespace.",
                    location,
                )
            )
        bad = sorted(set(name) & INVALID_NAME_CHARACTERS)
        if bad:
            issues.append(
                _error(
                    "invalid-configuration-name",
                    f"Configuration name {name!r} contains {''.join(bad)!r}, "
                    "which SOLIDWORKS does not allow.",
                    location,
                )
            )
        if len(name) > MAX_CONFIGURATION_NAME:
            issues.append(
                _error(
                    "invalid-configuration-name",
                    f"Configuration name is {len(name)} characters, over the "
                    f"{MAX_CONFIGURATION_NAME} character limit.",
                    location,
                )
            )
        elif len(name) > LONG_CONFIGURATION_NAME:
            issues.append(
                _warn(
                    "long-configuration-name",
                    f"Configuration name is {len(name)} characters, which is "
                    "awkward in the configuration tree and in drawings.",
                    location,
                )
            )
        lowered = name.strip().lower()
        if lowered in seen:
            issues.append(
                _error(
                    "duplicate-configuration",
                    f"Configuration {name!r} appears more than once. "
                    "SOLIDWORKS config names are case insensitive.",
                    location,
                )
            )
        seen.add(lowered)
    return issues


def _check_values(table: DesignTable) -> list[Issue]:
    issues: list[Issue] = []
    declared = {col.key: col for col in table.columns}
    for config in table.configurations:
        location = f"configuration {config.name!r}"
        for key in config.values:
            if key not in declared:
                issues.append(
                    _error(
                        "unknown-column",
                        f"Value supplied for a column that was never declared: {key}.",
                        location,
                    )
                )
        for col in table.columns:
            header = col.header(table.vocabulary)
            where = f"{location}, column {header!r}"
            if col.key not in config.values:
                if table.missing is MissingValue.ERROR:
                    issues.append(
                        _error("missing-value", "No value supplied.", where)
                    )
                continue
            issues += _check_one_value(
                config.values[col.key], col, where, table.round_floats
            )
    return issues


def _is_number(value: object) -> bool:
    """True for anything the writer can turn into a number."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float, Decimal)):
        return True
    # numpy scalars and other real-number stand-ins.
    return hasattr(value, "__float__") and not isinstance(value, str)


def _check_one_value(
    value: object, col: Column, where: str, round_floats: int | None = None
) -> list[Issue]:
    kind = col.value_kind
    if value is None or kind is ValueKind.ANY:
        return []
    if kind is ValueKind.READ_ONLY:
        return [
            _warn(
                "read-only-column",
                "SOLIDWORKS computes this property; a value written here is "
                "overwritten on rebuild.",
                where,
            )
        ]
    if kind is ValueKind.STATE:
        if isinstance(value, State):
            return []
        if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
            return []
        return [
            _warn(
                "non-state-value-in-state-column",
                f"Expected a State (S/U) or 1/0, got {value!r}.",
                where,
            )
        ]
    if kind is ValueKind.COMPONENT_STATE and not isinstance(value, ComponentState):
        return [
            _warn(
                "non-state-value-in-state-column",
                f"Expected a ComponentState (S/R), got {value!r}. Component "
                "suppression does not use the feature S/U letters.",
                where,
            )
        ]
    if kind is ValueKind.YES_NO and not isinstance(value, YesNo):
        return [
            _error(
                "wrong-value-type",
                f"Expected YesNo (Y/N), got {value!r}.",
                where,
            )
        ]
    if kind in (ValueKind.NUMBER, ValueKind.COLOR):
        if isinstance(value, Expression):
            return []
        if not _is_number(value):
            return [
                _warn(
                    "text-in-numeric-column",
                    f"Expected a number or an Expression, got {value!r}.",
                    where,
                )
            ]
        # When round_floats is set the caller has already dealt with precision.
        if (
            round_floats is None
            and isinstance(value, float)
            and len(f"{value!r}".split(".")[-1]) > 6
        ):
            return [
                _warn(
                    "float-precision",
                    f"{value!r} carries more decimals than a document with "
                    "millimetre units will show. Consider round_floats.",
                    where,
                )
            ]
    return []


def _check_parents(table: DesignTable) -> list[Issue]:
    parent_columns = [col for col in table.columns if col.spec.name == "parent"]
    if not parent_columns:
        return []
    key = parent_columns[0].key
    issues: list[Issue] = []
    position = {
        config.name.strip().lower(): index
        for index, config in enumerate(table.configurations)
    }
    for index, config in enumerate(table.configurations):
        raw_parent = config.values.get(key)
        if raw_parent is None or not str(raw_parent).strip():
            continue
        parent_name = str(raw_parent).strip().lower()
        location = f"configuration {config.name!r}"
        if parent_name == config.name.strip().lower():
            issues.append(
                _error("parent-cycle", "A configuration cannot be its own parent.", location)
            )
            continue
        if parent_name not in position:
            issues.append(
                _error(
                    "parent-not-found",
                    f"Parent {raw_parent!r} is not a configuration in this table.",
                    location,
                )
            )
            continue
        if position[parent_name] > index:
            issues.append(
                _error(
                    "parent-after-child",
                    f"Parent {raw_parent!r} appears after its child. "
                    "Derived configurations must follow their parent.",
                    location,
                )
            )
    issues += _check_parent_cycles(table, key, position)
    return issues


def _check_parent_cycles(table: DesignTable, key: str, position: dict[str, int]) -> list[Issue]:
    parents: dict[str, str] = {}
    for config in table.configurations:
        value = config.values.get(key)
        if value is not None and str(value).strip():
            parents[config.name.strip().lower()] = str(value).strip().lower()
    issues: list[Issue] = []
    for start in parents:
        seen = {start}
        current = parents.get(start)
        while current is not None and current in parents:
            if current in seen:
                issues.append(
                    _error(
                        "parent-cycle",
                        f"Configuration {start!r} is part of a $PARENT cycle.",
                        f"configuration {start!r}",
                    )
                )
                break
            seen.add(current)
            current = parents.get(current)
    return issues


def _check_sheets(table: DesignTable) -> list[Issue]:
    issues: list[Issue] = []
    names = {table.sheet_name.lower()}
    for sheet in table.extra_sheets:
        location = f"sheet {sheet.name!r}"
        if sheet.name.upper() in {n.upper() for n in RESERVED_SHEET_NAMES}:
            issues.append(
                _error(
                    "reserved-sheet-name",
                    "'_SWX' is generated by SOLIDWORKS when it embeds the "
                    "table. Authoring it here produces a table SOLIDWORKS "
                    "cannot reconcile. Use a different sheet name.",
                    location,
                )
            )
        if sheet.name.lower() in names:
            issues.append(
                _error(
                    "duplicate-sheet-name",
                    f"Sheet name {sheet.name!r} is already used.",
                    location,
                )
            )
        names.add(sheet.name.lower())
    for name in table.defined_names:
        if name in RESERVED_DEFINED_NAMES:
            issues.append(
                _error(
                    "reserved-defined-name",
                    f"{name!r} is reserved. 'Family' is created automatically "
                    "and '_SWX_0' belongs to SOLIDWORKS.",
                    f"defined name {name!r}",
                )
            )
    return issues


def format_report(issues: Sequence[Issue]) -> str:
    """Return a readable multi-line rendering of ``issues``."""
    return "\n".join(str(issue) for issue in issues)
