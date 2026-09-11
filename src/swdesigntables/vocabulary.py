"""Header prefix vocabulary.

Every literal that SOLIDWORKS looks for in a header cell lives here, so a
different interface language is a new ``Vocabulary`` instance rather than a
rewrite. SOLIDWORKS treats header syntax as case insensitive, but not as
punctuation insensitive: a hyphen where an underscore belongs is a different
parameter.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Vocabulary", "ENGLISH", "DEFAULT_VOCABULARY"]


@dataclass(frozen=True, slots=True)
class Vocabulary:
    """The header literals for one SOLIDWORKS interface language.

    Only :data:`ENGLISH` ships verified. To support another language, copy it
    with the prefixes replaced and pass the result to
    :class:`~swdesigntables.table.DesignTable`. Confirm each prefix with the
    Auto-create recipe in the README before trusting it.
    """

    value: str = "$VALUE"
    equations: str = "Equations"
    state: str = "$STATE"
    property: str = "$PRP"
    description: str = "$DESCRIPTION"
    parent: str = "$PARENT"
    configuration: str = "$CONFIGURATION"
    display_state: str = "$DISPLAYSTATE"
    comment: str = "$COMMENT"
    color: str = "$COLOR"
    part_number: str = "$PARTNUMBER"
    tolerance: str = "$TOLERANCE"
    show: str = "$SHOW"
    fixed: str = "$FIXED"
    # Sources disagree on the punctuation of the next three. They are single
    # constants precisely so that correcting one is a one-line change.
    user_notes: str = "$USER_NOTES"
    never_expand_in_bom: str = "$NEVER_EXPAND_IN_BOM"
    suppress_new_features: str = "$SUPPRESS NEW FEATURES"
    suppress_new_components: str = "$SUPPRESS NEW COMPONENTS"
    sw_property: str = "$SW-"


ENGLISH: Vocabulary = Vocabulary()
DEFAULT_VOCABULARY: Vocabulary = ENGLISH
