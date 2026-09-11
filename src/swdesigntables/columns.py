"""Typed columns and the factories that build them.

A column is a parameter spec plus the arguments that fill its template. It is
frozen and hashable, so a column object is the key you use when supplying row
values. That is the whole point: values are addressed by identity, never by
column number.
"""

from __future__ import annotations

from dataclasses import dataclass

from swdesigntables.parameters import (
    RAW,
    ParameterSpec,
    Status,
    ValueKind,
    get_parameter,
    list_parameters,
)
from swdesigntables.vocabulary import DEFAULT_VOCABULARY, Vocabulary

__all__ = [
    "Column",
    "column",
    "parse_header",
    "dimension",
    "global_variable",
    "state",
    "prop",
    "description",
    "parent",
    "display_state",
    "component_config",
    "component_state",
    "component_visibility",
    "component_fixed",
    "component_display_state",
    "comment",
    "color",
    "part_number",
    "user_notes",
    "never_expand_in_bom",
    "suppress_new_features",
    "suppress_new_components",
    "sw_property",
    "tolerance",
    "raw",
]


@dataclass(frozen=True, slots=True)
class Column:
    """One design table column.

    Two columns are equal when they name the same parameter with the same
    arguments, independent of the vocabulary used to render them.
    """

    spec: ParameterSpec
    args: tuple[tuple[str, str], ...] = ()

    def header(self, vocabulary: Vocabulary | None = None) -> str:
        """Return the text that goes in row 2 for this column."""
        return self.spec.render(dict(self.args), vocabulary or DEFAULT_VOCABULARY)

    @property
    def key(self) -> str:
        """A stable identity for this column that does not depend on language."""
        rendered = ",".join(f"{name}={value}" for name, value in self.args)
        return f"{self.spec.name}({rendered})"

    @property
    def status(self) -> Status:
        """How well confirmed this column's syntax is."""
        return self.spec.status

    @property
    def value_kind(self) -> ValueKind:
        """The kind of value this column accepts."""
        return self.spec.value_kind

    def __str__(self) -> str:
        return self.header()


def column(parameter: str, **args: object) -> Column:
    """Build a column for any registered parameter, including runtime ones."""
    spec = get_parameter(parameter)
    return _build(spec, **args)


def _build(spec: ParameterSpec, **args: object) -> Column:
    normalized = tuple(sorted((name, str(value)) for name, value in args.items()))
    column_ = Column(spec=spec, args=normalized)
    # Render once so a missing or malformed argument fails at the call site.
    column_.header()
    return column_


def _component_ref(component: str, instance: int | None) -> str:
    """Return a component reference, appending the instance number if given."""
    if instance is None:
        return component
    if component.endswith(">"):
        raise ValueError(
            f"Component {component!r} already carries an instance number; "
            "pass either the suffix or the instance argument, not both."
        )
    return f"{component}<{instance}>"


# --- verified parameters -------------------------------------------------


def dimension(name: str, feature: str) -> Column:
    """Drive a dimension directly, as in ``Length@Boss-Extrude1``.

    If an equation governs the dimension, this column is ignored on rebuild;
    drive the global variable with :func:`global_variable` instead.
    """
    return _build(get_parameter("dimension"), dimension=name, feature=feature)


def global_variable(name: str) -> Column:
    """Drive a global variable, as in ``$VALUE@width@Equations``."""
    return _build(get_parameter("global_variable"), variable=name)


def state(feature: str) -> Column:
    """Suppress or unsuppress a feature, as in ``$STATE@Draft2``."""
    return _build(get_parameter("state"), feature=feature)


def prop(name: str) -> Column:
    """Set a custom property, as in ``$PRP@Description``."""
    return _build(get_parameter("prop"), name=name)


def description() -> Column:
    """The ``$DESCRIPTION`` column."""
    return _build(get_parameter("description"))


def parent() -> Column:
    """The ``$PARENT`` column, which makes each row a derived configuration."""
    return _build(get_parameter("parent"))


def display_state() -> Column:
    """The ``$DISPLAYSTATE`` column."""
    return _build(get_parameter("display_state"))


def component_config(component: str, instance: int | None = None) -> Column:
    """Choose a component's configuration, as in ``$CONFIGURATION@Arm<1>``."""
    return _build(
        get_parameter("component_config"), component=_component_ref(component, instance)
    )


# --- documented parameters ----------------------------------------------


def component_state(component: str, instance: int | None = None) -> Column:
    """Suppress or resolve a component. Values are ``S``/``R``."""
    return _build(
        get_parameter("component_state"), component=_component_ref(component, instance)
    )


def component_visibility(component: str, instance: int | None = None) -> Column:
    """Show or hide a component, as in ``$SHOW@Arm<1>``."""
    return _build(
        get_parameter("component_visibility"), component=_component_ref(component, instance)
    )


def component_fixed(component: str, instance: int | None = None) -> Column:
    """Fix or float a component, as in ``$FIXED@Arm<1>``."""
    return _build(
        get_parameter("component_fixed"), component=_component_ref(component, instance)
    )


def component_display_state(component: str, instance: int | None = None) -> Column:
    """Choose a component's display state."""
    return _build(
        get_parameter("component_display_state"),
        component=_component_ref(component, instance),
    )


def comment() -> Column:
    """A ``$COMMENT`` column, which SOLIDWORKS ignores."""
    return _build(get_parameter("comment"))


def color() -> Column:
    """The ``$COLOR`` column, taking a 32-bit RGB integer."""
    return _build(get_parameter("color"))


def part_number() -> Column:
    """The ``$PARTNUMBER`` column used by the bill of materials."""
    return _build(get_parameter("part_number"))


def user_notes() -> Column:
    """The ``$USER_NOTES`` column."""
    return _build(get_parameter("user_notes"))


def never_expand_in_bom() -> Column:
    """The ``$NEVER_EXPAND_IN_BOM`` column, taking ``Y``/``N``."""
    return _build(get_parameter("never_expand_in_bom"))


def suppress_new_features() -> Column:
    """The ``$SUPPRESS NEW FEATURES`` column, taking ``Y``/``N``."""
    return _build(get_parameter("suppress_new_features"))


def suppress_new_components() -> Column:
    """The ``$SUPPRESS NEW COMPONENTS`` column, taking ``Y``/``N``."""
    return _build(get_parameter("suppress_new_components"))


def sw_property(name: str) -> Column:
    """A SOLIDWORKS-computed property such as ``$SW-Mass``. Read only."""
    return _build(get_parameter("sw_property"), name=name)


def tolerance(name: str, feature: str) -> Column:
    """Set a dimension's tolerance, as in ``$TOLERANCE@D1@Sketch1``."""
    return _build(get_parameter("tolerance"), dimension=name, feature=feature)


# --- escape hatch --------------------------------------------------------


def raw(text: str) -> Column:
    """Write a header verbatim, with no syntax checking.

    The floor under this library's coverage: whatever SOLIDWORKS accepts, you
    can write, even if the parameter is not in the catalogue.
    """
    if not text.strip():
        raise ValueError("A raw header cannot be empty")
    return Column(spec=RAW, args=(("text", text),))


def parse_header(text: str, vocabulary: Vocabulary | None = None) -> Column:
    """Turn an existing header string into the typed column that renders it.

    This is the migration path for scripts that already hold a list of header
    strings: parse them and keep working, with validation and identity-based
    row values from then on. Anything unrecognized becomes a raw column.
    """
    vocab = vocabulary or DEFAULT_VOCABULARY
    stripped = text.strip()
    if not stripped:
        raise ValueError("Cannot parse an empty header")
    for spec in list_parameters():
        match = spec.pattern(vocab).match(stripped)
        if match is None:
            continue
        args = {name: value for name, value in match.groupdict().items() if value is not None}
        if set(args) != set(spec.fields):
            continue
        return _build(spec, **args)
    return raw(stripped)
