"""Cell value types and their normalization.

SOLIDWORKS reads a handful of value vocabularies that look like plain strings
but are not interchangeable: ``S``/``U`` for feature suppression, ``S``/``R``
for component suppression, ``Y``/``N`` for flags. Each gets its own enum so a
wrong one is a type error rather than a silently ignored cell.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from swdesigntables.parameters import ValueKind

__all__ = [
    "State",
    "ComponentState",
    "YesNo",
    "StateFormat",
    "Expression",
    "MissingValue",
    "CellValue",
    "CellPayload",
    "SUPPRESSED",
    "UNSUPPRESSED",
    "YES",
    "NO",
    "normalize",
]


class State(str, Enum):
    """Suppression state of a feature, for a ``$STATE@<feature>`` column."""

    SUPPRESSED = "S"
    UNSUPPRESSED = "U"

    @classmethod
    def from_bool(cls, suppressed: bool) -> State:
        """Return SUPPRESSED when ``suppressed`` is true, UNSUPPRESSED otherwise."""
        return cls.SUPPRESSED if suppressed else cls.UNSUPPRESSED

    @classmethod
    def from_legacy_int(cls, value: int) -> State:
        """Convert the 1 = suppressed / 0 = unsuppressed convention to a State."""
        if value not in (0, 1):
            raise ValueError(f"Legacy state must be 0 or 1, got {value!r}")
        return cls.SUPPRESSED if value == 1 else cls.UNSUPPRESSED


class ComponentState(str, Enum):
    """Suppression state of an assembly component, ``$STATE@<component><n>``.

    Note the letters differ from :class:`State`: a component is Resolved, not
    Unsuppressed.
    """

    SUPPRESSED = "S"
    RESOLVED = "R"


class YesNo(str, Enum):
    """A yes/no flag column such as ``$SHOW@`` or ``$NEVER_EXPAND_IN_BOM``."""

    YES = "Y"
    NO = "N"

    @classmethod
    def from_bool(cls, value: bool) -> YesNo:
        """Return YES when ``value`` is true, NO otherwise."""
        return cls.YES if value else cls.NO


class StateFormat(Enum):
    """How :class:`State` is serialized into the cell.

    LETTERS is what the SOLIDWORKS documentation describes. NUMERIC exists
    because working tables in the wild use 1/0, and rewriting someone's table
    from under them is not this library's job.
    """

    LETTERS = "letters"
    NUMERIC = "numeric"


class MissingValue(Enum):
    """What to do when a configuration supplies no value for a column."""

    BLANK = "blank"
    ERROR = "error"
    FILL = "fill"


@dataclass(frozen=True, slots=True)
class Expression:
    """An equation-style value, written as ``=<text>``.

    It is stored as a literal string, never as an Excel formula: openpyxl would
    write a formula with no cached result and SOLIDWORKS would read an empty
    parameter.
    """

    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Expression text cannot be empty")

    def render(self) -> str:
        """Return the cell text, with exactly one leading '='."""
        return "=" + self.text.lstrip("=").strip()


CellValue = (
    str | int | float | bool | None | State | ComponentState | YesNo | Expression
)

# What the writer is allowed to hand to an openpyxl cell.
CellPayload = str | int | float | bool | None

SUPPRESSED = State.SUPPRESSED
UNSUPPRESSED = State.UNSUPPRESSED
YES = YesNo.YES
NO = YesNo.NO


def normalize(
    value: CellValue,
    *,
    state_format: StateFormat = StateFormat.LETTERS,
    round_floats: int | None = None,
    value_kind: ValueKind | None = None,
) -> tuple[CellPayload, bool]:
    """Convert a user value into what the writer should put in the cell.

    Returns the payload and whether it must be forced to a string cell (which
    is how an Expression avoids becoming an Excel formula).

    ``value_kind`` is the kind of the column the value belongs to, when there
    is one. It is what lets True and False become Y and N in a yes/no column,
    and only there: Excel would otherwise write TRUE, which SOLIDWORKS does
    not read. A value with no column behind it, such as a cell of an extra
    sheet, passes with ``value_kind=None``.
    """
    if value is None:
        return None, False
    if value_kind is ValueKind.YES_NO and isinstance(value, bool):
        return YesNo.from_bool(value).value, False
    if isinstance(value, Expression):
        return value.render(), True
    if isinstance(value, State):
        if state_format is StateFormat.NUMERIC:
            return (1 if value is State.SUPPRESSED else 0), False
        return value.value, False
    if isinstance(value, (ComponentState, YesNo)):
        return value.value, False
    if isinstance(value, bool):
        return value, False
    if isinstance(value, (int, str)):
        return value, False
    if isinstance(value, float):
        return (round(value, round_floats) if round_floats is not None else value), False
    if isinstance(value, Decimal):
        converted = float(value)
        return (round(converted, round_floats) if round_floats is not None else converted), False
    if hasattr(value, "__float__"):
        # numpy scalars and anything else that claims to be a real number.
        converted = float(value)  # type: ignore[arg-type]
        return (round(converted, round_floats) if round_floats is not None else converted), False
    raise TypeError(
        f"Unsupported cell value of type {type(value).__name__!r}: {value!r}. "
        "Convert it to a string, a number, or one of the swdesigntables value types."
    )
