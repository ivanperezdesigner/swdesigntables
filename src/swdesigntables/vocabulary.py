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

    Only :data:`ENGLISH` ships verified. Translated headers are a real
    SOLIDWORKS feature: the same parameter is ``$DESCRIPTION`` in English,
    ``$BESCHREIBUNG`` in German and ``$DESCRIZIONE`` in Italian. To support
    another language, copy this vocabulary with the prefixes replaced and pass
    the result to :class:`~swdesigntables.table.DesignTable`.
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
    fixed: str = "$FIXED"
    user_notes: str = "$USER_NOTES"
    never_expand_in_bom: str = "$NEVER_EXPAND_IN_BOM"
    enable: str = "$ENABLE"
    library_material: str = "$LIBRARY:MATERIAL"
    hole_size: str = "$HW-SIZE"
    profile_size: str = "$PROFILE_SIZE"
    skip: str = "$SKIP"
    sw_property: str = "$SW-"
    # Obsolete: SOLIDWORKS replaced component visibility with display states.
    show: str = "$SHOW"
    # Not described by the SOLIDWORKS documentation in any version consulted.
    # They are single constants so that correcting one is a one-line change.
    suppress_new_features: str = "$SUPPRESS NEW FEATURES"
    suppress_new_components: str = "$SUPPRESS NEW COMPONENTS"


ENGLISH: Vocabulary = Vocabulary()
DEFAULT_VOCABULARY: Vocabulary = ENGLISH
