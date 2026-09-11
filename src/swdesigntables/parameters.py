"""The catalogue of design table parameters.

Each parameter is data, not a class: a header template, the fields it needs,
the kind of value it accepts, and how confident we are in it. Supporting a
parameter SOLIDWORKS invents next year is therefore a registry entry, not a
new module.

Verification status is part of the public contract:

``VERIFIED``
    Confirmed against real design table files or the verified reference.
``DOCUMENTED``
    Described by SOLIDWORKS documentation, not confirmed here against a model.
``UNVERIFIED``
    Registered at runtime by a caller, or otherwise unconfirmed.

Using anything other than ``VERIFIED`` emits an ``unverified-parameter``
warning. Confirm one with the Auto-create recipe in the README, then silence
that code.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from string import Formatter

from swdesigntables.errors import UnknownParameterError
from swdesigntables.vocabulary import DEFAULT_VOCABULARY, Vocabulary

__all__ = [
    "ValueKind",
    "Status",
    "ParameterSpec",
    "register_parameter",
    "get_parameter",
    "list_parameters",
    "RAW",
]


class ValueKind(Enum):
    """The kind of value a parameter's column accepts."""

    NUMBER = "number"
    TEXT = "text"
    STATE = "state"
    COMPONENT_STATE = "component_state"
    YES_NO = "yes_no"
    CONFIG_NAME = "config_name"
    COLOR = "color"
    READ_ONLY = "read_only"
    ANY = "any"


class Status(Enum):
    """How well confirmed a parameter's syntax is."""

    VERIFIED = "verified"
    DOCUMENTED = "documented"
    UNVERIFIED = "unverified"


# A header segment that must not swallow the '@' separators.
_SEGMENT = r"[^@]+"
# A component reference always carries its instance number: Bracket<2>.
_INSTANCE = r"[^@]+<\d+>"
# A feature name, which must not look like a component reference.
_FEATURE = r"(?!.*<\d+>$)[^@]+"
# A dimension name, which must not look like a $PARAMETER prefix.
_DIMENSION = r"(?!\$)[^@]+"


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """One entry in the catalogue.

    ``template`` is a format string whose fields are filled either from the
    caller's arguments (``fields``) or from the vocabulary (``vocab_fields``,
    which maps a template field to a :class:`Vocabulary` attribute).
    """

    name: str
    template: str
    summary: str
    fields: tuple[str, ...] = ()
    vocab_fields: tuple[tuple[str, str], ...] = ()
    field_patterns: tuple[tuple[str, str], ...] = ()
    value_kind: ValueKind = ValueKind.ANY
    status: Status = Status.DOCUMENTED
    priority: int = 50

    def render(self, args: Mapping[str, str], vocabulary: Vocabulary | None = None) -> str:
        """Return the row 2 header text for this parameter."""
        vocab = vocabulary or DEFAULT_VOCABULARY
        values: dict[str, str] = {
            name: getattr(vocab, attr) for name, attr in self.vocab_fields
        }
        missing = [name for name in self.fields if name not in args]
        if missing:
            raise TypeError(f"Parameter {self.name!r} needs: {', '.join(missing)}")
        values.update({name: args[name] for name in self.fields})
        return self.template.format(**values)

    def pattern(self, vocabulary: Vocabulary | None = None) -> re.Pattern[str]:
        """Return a regex that recognizes this parameter's header text."""
        vocab = vocabulary or DEFAULT_VOCABULARY
        patterns = dict(self.field_patterns)
        vocab_attrs = dict(self.vocab_fields)
        parts: list[str] = []
        for literal, name, _spec, _conversion in Formatter().parse(self.template):
            parts.append(re.escape(literal))
            if name is None:
                continue
            attr = vocab_attrs.get(name)
            if attr is not None:
                parts.append(re.escape(getattr(vocab, attr)))
            else:
                parts.append("(?P<" + name + ">" + patterns.get(name, _SEGMENT) + ")")
        return re.compile("^" + "".join(parts) + "$", re.IGNORECASE)


RAW = ParameterSpec(
    name="raw",
    template="{text}",
    summary="A header written verbatim, with no syntax checking.",
    fields=("text",),
    field_patterns=(("text", r".+"),),
    value_kind=ValueKind.ANY,
    status=Status.UNVERIFIED,
    priority=1000,
)


_CATALOGUE: list[ParameterSpec] = [
    ParameterSpec(
        name="global_variable",
        template="{value}@{variable}@{equations}",
        summary=(
            "Drive a global variable. Use this, not a dimension, when an "
            "equation governs the dimension."
        ),
        fields=("variable",),
        vocab_fields=(("value", "value"), ("equations", "equations")),
        value_kind=ValueKind.NUMBER,
        status=Status.VERIFIED,
        priority=10,
    ),
    ParameterSpec(
        name="tolerance",
        template="{tolerance}@{dimension}@{feature}",
        summary="Set the tolerance of one dimension per configuration.",
        fields=("dimension", "feature"),
        vocab_fields=(("tolerance", "tolerance"),),
        value_kind=ValueKind.TEXT,
        status=Status.DOCUMENTED,
        priority=10,
    ),
    ParameterSpec(
        name="component_state",
        template="{state}@{component}",
        summary="Suppress or resolve an assembly component. Values are S/R, not S/U.",
        fields=("component",),
        vocab_fields=(("state", "state"),),
        field_patterns=(("component", _INSTANCE),),
        value_kind=ValueKind.COMPONENT_STATE,
        status=Status.DOCUMENTED,
        priority=15,
    ),
    ParameterSpec(
        name="component_visibility",
        template="{show}@{component}",
        summary="Show or hide an assembly component.",
        fields=("component",),
        vocab_fields=(("show", "show"),),
        field_patterns=(("component", _INSTANCE),),
        value_kind=ValueKind.YES_NO,
        status=Status.DOCUMENTED,
        priority=15,
    ),
    ParameterSpec(
        name="component_fixed",
        template="{fixed}@{component}",
        summary="Fix or float an assembly component.",
        fields=("component",),
        vocab_fields=(("fixed", "fixed"),),
        field_patterns=(("component", _INSTANCE),),
        value_kind=ValueKind.YES_NO,
        status=Status.DOCUMENTED,
        priority=15,
    ),
    ParameterSpec(
        name="component_display_state",
        template="{display_state}@{component}",
        summary="Choose the display state of an assembly component.",
        fields=("component",),
        vocab_fields=(("display_state", "display_state"),),
        field_patterns=(("component", _INSTANCE),),
        value_kind=ValueKind.TEXT,
        status=Status.DOCUMENTED,
        priority=15,
    ),
    ParameterSpec(
        name="component_config",
        template="{configuration}@{component}",
        summary="Choose which configuration of a component an assembly uses.",
        fields=("component",),
        vocab_fields=(("configuration", "configuration"),),
        value_kind=ValueKind.CONFIG_NAME,
        status=Status.VERIFIED,
        priority=16,
    ),
    ParameterSpec(
        name="state",
        template="{state}@{feature}",
        summary="Suppress or unsuppress a feature. Values are S/U, or 1/0.",
        fields=("feature",),
        vocab_fields=(("state", "state"),),
        field_patterns=(("feature", _FEATURE),),
        value_kind=ValueKind.STATE,
        status=Status.VERIFIED,
        priority=20,
    ),
    ParameterSpec(
        name="prop",
        template="{property}@{name}",
        summary="Set a custom property, which is what a drawing title block reads.",
        fields=("name",),
        vocab_fields=(("property", "property"),),
        value_kind=ValueKind.ANY,
        status=Status.VERIFIED,
        priority=20,
    ),
    ParameterSpec(
        name="sw_property",
        template="{sw_property}{name}",
        summary="A SOLIDWORKS-computed property such as Mass or COG. Read only.",
        fields=("name",),
        vocab_fields=(("sw_property", "sw_property"),),
        value_kind=ValueKind.READ_ONLY,
        status=Status.DOCUMENTED,
        priority=25,
    ),
    ParameterSpec(
        name="description",
        template="{description}",
        summary="The configuration description.",
        vocab_fields=(("description", "description"),),
        value_kind=ValueKind.TEXT,
        status=Status.VERIFIED,
        priority=5,
    ),
    ParameterSpec(
        name="parent",
        template="{parent}",
        summary="The parent configuration, making this row a derived configuration.",
        vocab_fields=(("parent", "parent"),),
        value_kind=ValueKind.CONFIG_NAME,
        status=Status.VERIFIED,
        priority=5,
    ),
    ParameterSpec(
        name="display_state",
        template="{display_state}",
        summary="The display state of the configuration.",
        vocab_fields=(("display_state", "display_state"),),
        value_kind=ValueKind.TEXT,
        status=Status.VERIFIED,
        priority=5,
    ),
    ParameterSpec(
        name="comment",
        template="{comment}",
        summary="A column SOLIDWORKS ignores, for notes to whoever reads the sheet.",
        vocab_fields=(("comment", "comment"),),
        value_kind=ValueKind.TEXT,
        status=Status.DOCUMENTED,
        priority=5,
    ),
    ParameterSpec(
        name="color",
        template="{color}",
        summary="The configuration colour, as a 32-bit RGB integer.",
        vocab_fields=(("color", "color"),),
        value_kind=ValueKind.COLOR,
        status=Status.DOCUMENTED,
        priority=5,
    ),
    ParameterSpec(
        name="part_number",
        template="{part_number}",
        summary="The part number the bill of materials shows for this configuration.",
        vocab_fields=(("part_number", "part_number"),),
        value_kind=ValueKind.TEXT,
        status=Status.DOCUMENTED,
        priority=5,
    ),
    ParameterSpec(
        name="user_notes",
        template="{user_notes}",
        summary="Free text notes stored on the configuration.",
        vocab_fields=(("user_notes", "user_notes"),),
        value_kind=ValueKind.TEXT,
        status=Status.DOCUMENTED,
        priority=5,
    ),
    ParameterSpec(
        name="never_expand_in_bom",
        template="{never_expand_in_bom}",
        summary="Keep a subassembly from being expanded in the bill of materials.",
        vocab_fields=(("never_expand_in_bom", "never_expand_in_bom"),),
        value_kind=ValueKind.YES_NO,
        status=Status.DOCUMENTED,
        priority=5,
    ),
    ParameterSpec(
        name="suppress_new_features",
        template="{suppress_new_features}",
        summary="Suppress features added to the model after this configuration exists.",
        vocab_fields=(("suppress_new_features", "suppress_new_features"),),
        value_kind=ValueKind.YES_NO,
        status=Status.DOCUMENTED,
        priority=5,
    ),
    ParameterSpec(
        name="suppress_new_components",
        template="{suppress_new_components}",
        summary="Suppress components added to the assembly after this configuration exists.",
        vocab_fields=(("suppress_new_components", "suppress_new_components"),),
        value_kind=ValueKind.YES_NO,
        status=Status.DOCUMENTED,
        priority=5,
    ),
    # The catch-all, tried last: anything shaped Name@Target is a dimension.
    ParameterSpec(
        name="dimension",
        template="{dimension}@{feature}",
        summary="Drive a dimension directly. Does nothing if an equation governs it.",
        fields=("dimension", "feature"),
        field_patterns=(("dimension", _DIMENSION),),
        value_kind=ValueKind.NUMBER,
        status=Status.VERIFIED,
        priority=90,
    ),
]

_REGISTRY: dict[str, ParameterSpec] = {spec.name: spec for spec in _CATALOGUE}
_REGISTRY[RAW.name] = RAW


def register_parameter(
    name: str,
    template: str,
    *,
    summary: str = "",
    fields: tuple[str, ...] = (),
    vocab_fields: tuple[tuple[str, str], ...] = (),
    field_patterns: tuple[tuple[str, str], ...] = (),
    value_kind: ValueKind = ValueKind.ANY,
    status: Status = Status.UNVERIFIED,
    priority: int = 50,
) -> ParameterSpec:
    """Add a parameter to the catalogue at runtime.

    Use this for a parameter this package does not ship, such as the sheet
    metal family, instead of waiting for a release. The new spec is usable
    immediately through :func:`swdesigntables.columns.column`.
    """
    if name in _REGISTRY:
        raise ValueError(f"Parameter {name!r} is already registered")
    spec = ParameterSpec(
        name=name,
        template=template,
        summary=summary,
        fields=fields,
        vocab_fields=vocab_fields,
        field_patterns=field_patterns,
        value_kind=value_kind,
        status=status,
        priority=priority,
    )
    _REGISTRY[name] = spec
    return spec


def get_parameter(name: str) -> ParameterSpec:
    """Return the spec registered under ``name``."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise UnknownParameterError(
            f"No parameter named {name!r}. Registered: {', '.join(sorted(_REGISTRY))}"
        ) from None


def list_parameters(*, include_raw: bool = False) -> tuple[ParameterSpec, ...]:
    """Return every registered spec, in the order ``parse_header`` tries them."""
    specs = [spec for spec in _REGISTRY.values() if include_raw or spec is not RAW]
    return tuple(sorted(specs, key=lambda spec: (spec.priority, spec.name)))
