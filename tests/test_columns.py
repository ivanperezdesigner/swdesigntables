"""Header rendering, parsing, and the catalogue."""

from __future__ import annotations

import pytest

import swdesigntables as sw
from swdesigntables.parameters import Status


@pytest.mark.parametrize(
    ("column", "expected"),
    [
        (sw.dimension("Length", "Boss-Extrude1"), "Length@Boss-Extrude1"),
        (sw.global_variable("hole_qty"), "$VALUE@hole_qty@Equations"),
        (sw.state("Draft2"), "$STATE@Draft2"),
        (sw.state("Move Face5"), "$STATE@Move Face5"),
        (sw.prop("Description"), "$PRP@Description"),
        (sw.description(), "$DESCRIPTION"),
        (sw.parent(), "$PARENT"),
        (sw.display_state(), "$DISPLAYSTATE"),
        (sw.component_config("Arm", 1), "$CONFIGURATION@Arm<1>"),
        (sw.component_config("Arm<3>"), "$CONFIGURATION@Arm<3>"),
        (sw.component_state("Screw", 2), "$STATE@Screw<2>"),
        (sw.component_visibility("Screw", 2), "$SHOW@Screw<2>"),
        (sw.component_fixed("Screw", 2), "$FIXED@Screw<2>"),
        (sw.component_display_state("Screw", 2), "$DISPLAYSTATE@Screw<2>"),
        (sw.comment(), "$COMMENT"),
        (sw.color(), "$COLOR"),
        (sw.part_number(), "$PARTNUMBER"),
        (sw.user_notes(), "$USER_NOTES"),
        (sw.never_expand_in_bom(), "$NEVER_EXPAND_IN_BOM"),
        (sw.suppress_new_features(), "$SUPPRESS NEW FEATURES"),
        (sw.suppress_new_components(), "$SUPPRESS NEW COMPONENTS"),
        (sw.sw_property("Mass"), "$SW-Mass"),
        (sw.tolerance("D1", "Sketch1"), "$TOLERANCE@D1@Sketch1"),
        (sw.raw("$WHATEVER@Thing"), "$WHATEVER@Thing"),
    ],
)
def test_header_rendering(column, expected):
    assert column.header() == expected
    assert str(column) == expected


@pytest.mark.parametrize(
    "column",
    [
        sw.dimension("Length", "Boss-Extrude1"),
        sw.global_variable("hole_qty"),
        sw.state("Move Face5"),
        sw.prop("Description"),
        sw.description(),
        sw.parent(),
        sw.display_state(),
        sw.component_config("Arm", 1),
        sw.component_state("Screw", 2),
        sw.component_visibility("Screw", 2),
        sw.component_fixed("Screw", 2),
        sw.component_display_state("Screw", 2),
        sw.comment(),
        sw.color(),
        sw.part_number(),
        sw.user_notes(),
        sw.never_expand_in_bom(),
        sw.suppress_new_features(),
        sw.suppress_new_components(),
        sw.sw_property("Mass"),
        sw.tolerance("D1", "Sketch1"),
    ],
)
def test_parse_header_round_trips(column):
    assert sw.parse_header(column.header()) == column


def test_parse_header_is_case_insensitive():
    """SOLIDWORKS treats header syntax as case insensitive, so we must too."""
    assert sw.parse_header("$value@width@EQUATIONS") == sw.global_variable("width")
    assert sw.parse_header("$state@Draft2") == sw.state("Draft2")


def test_parse_header_distinguishes_feature_from_component():
    """$STATE@X and $STATE@X<2> are different parameters with different values."""
    assert sw.parse_header("$STATE@Draft2").spec.name == "state"
    assert sw.parse_header("$STATE@Screw<2>").spec.name == "component_state"


def test_parse_header_falls_back_to_raw():
    column = sw.parse_header("$NOT_A_REAL_PARAMETER")
    assert column.spec.name == "raw"
    assert column.header() == "$NOT_A_REAL_PARAMETER"


def test_columns_are_hashable_and_comparable():
    first = sw.dimension("Length", "Boss-Extrude1")
    second = sw.dimension("Length", "Boss-Extrude1")
    assert first == second
    assert len({first, second}) == 1
    assert first.key == second.key


def test_key_is_independent_of_vocabulary():
    spanish = sw.Vocabulary(state="$ESTADO")
    column = sw.state("Draft2")
    assert column.header(spanish) == "$ESTADO@Draft2"
    assert column.key == sw.state("Draft2").key


def test_component_instance_cannot_be_given_twice():
    with pytest.raises(ValueError, match="already carries an instance"):
        sw.component_config("Arm<1>", 1)


def test_raw_rejects_empty():
    with pytest.raises(ValueError):
        sw.raw("   ")


def test_every_parameter_declares_a_status():
    for spec in sw.list_parameters(include_raw=True):
        assert isinstance(spec.status, Status)
        assert spec.summary, f"{spec.name} has no summary"


def test_register_parameter_adds_a_usable_column():
    sw.register_parameter(
        "sheet_metal_thickness",
        template="$SM-THICKNESS",
        summary="Sheet metal thickness. Syntax unconfirmed.",
    )
    column = sw.column("sheet_metal_thickness")
    assert column.header() == "$SM-THICKNESS"
    assert column.status is Status.UNVERIFIED
    with pytest.raises(ValueError, match="already registered"):
        sw.register_parameter("sheet_metal_thickness", template="$X")


def test_unknown_parameter_is_named_clearly():
    with pytest.raises(sw.UnknownParameterError, match="No parameter named"):
        sw.column("nonexistent")


# --- the parameters documented by the SOLIDWORKS help --------------------


DOCUMENTED_HEADERS = [
    (sw.dimension("Length", "Boss-Extrude1"), "Length@Boss-Extrude1"),
    (sw.global_variable("width"), "$VALUE@width@Equations"),
    (sw.state("Draft2"), "$STATE@Draft2"),
    (sw.prop("Material"), "$PRP@Material"),
    (sw.description(), "$DESCRIPTION"),
    (sw.parent(), "$PARENT"),
    (sw.display_state(), "$DISPLAYSTATE"),
    (sw.comment(), "$COMMENT"),
    (sw.color(), "$COLOR"),
    (sw.part_number(), "$PARTNUMBER"),
    (sw.user_notes(), "$USER_NOTES"),
    (sw.never_expand_in_bom(), "$NEVER_EXPAND_IN_BOM"),
    (sw.tolerance("D1", "Extrude1"), "$TOLERANCE@D1@Extrude1"),
    (sw.component_state("Screw", 2), "$STATE@Screw<2>"),
    (sw.component_config("Arm", 1), "$CONFIGURATION@Arm<1>"),
    (sw.component_fixed("Screw"), "$FIXED@Screw"),
    (sw.base_part_config("washer"), "$CONFIGURATION@washer"),
    (sw.material("Bracket"), "$LIBRARY:MATERIAL@Bracket"),
    (sw.body_material("Body1", "Bracket"), "$LIBRARY:MATERIAL@Body1@Bracket"),
    (sw.hole_size("CBORE1"), "$HW-SIZE@CBORE1"),
    (sw.profile_size("Member1"), "$PROFILE_SIZE@Member1"),
    (sw.equation_enable(1), "$ENABLE@1@Equations"),
    (sw.sketch_relation_state("Fixed1", "Sketch2"), "$STATE@Fixed1@Sketch2"),
    (sw.skip_instances("LPattern1"), "$SKIP@LPattern1"),
    (sw.mass(), "$SW-MASS"),
    (sw.center_of_mass(), "$SW-COG"),
]


@pytest.mark.parametrize("column, header", DOCUMENTED_HEADERS)
def test_documented_header_spelling(column, header):
    """Each spelling comes from a SOLIDWORKS help page of its own."""
    assert column.header() == header
    assert column.status is Status.VERIFIED


@pytest.mark.parametrize("column, header", DOCUMENTED_HEADERS)
def test_documented_header_round_trips(column, header):
    assert sw.parse_header(header).spec.name == column.spec.name


def test_a_component_config_without_an_instance_reads_as_a_base_part():
    """$CONFIGURATION@X is a base part in a part, a component in an assembly.

    The instance number is what tells them apart, so a header without one
    parses as the base part parameter.
    """
    assert sw.parse_header("$CONFIGURATION@washer").spec.name == "base_part_config"
    assert sw.parse_header("$CONFIGURATION@washer<1>").spec.name == "component_config"


def test_show_is_kept_but_marked_obsolete():
    assert sw.component_visibility("Screw", 2).status is Status.OBSOLETE


def test_component_display_state_is_not_documented():
    assert sw.component_display_state("Screw", 2).status is Status.UNVERIFIED


@pytest.mark.parametrize(
    "column",
    [sw.suppress_new_features(), sw.suppress_new_components()],
)
def test_suppress_new_parameters_are_unverified(column):
    assert column.status is Status.UNVERIFIED


def test_mass_accepts_a_value():
    """$SW-MASS overrides the calculated mass; it is not a read-only column."""
    assert sw.mass().value_kind is not sw.ValueKind.READ_ONLY
