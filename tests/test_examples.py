"""End-to-end shapes, and the regression guard for ergonomics.

If the API ever gets clumsy, these two examples get ugly before anything else
does. Read them as documentation that is checked.
"""

from __future__ import annotations

import swdesigntables as sw

FRAMES = ["G01", "G02", "G03"]


def test_assembly_table_shape(reload_table):
    """One row per frame, pointing three component instances at their configs."""
    table = sw.DesignTable("FRAME-ASSY-MASTER")
    slots = [table.add_column(sw.component_config("SubFrame", i)) for i in (1, 2, 3)]
    description = table.add_column(sw.prop("Description"))

    for frame_id in FRAMES:
        table.add_configuration(
            frame_id,
            {
                slots[0]: f"{frame_id}_HOR",
                slots[1]: f"{frame_id}_VER1",
                slots[2]: f"{frame_id}_VER2",
                description: frame_id,
            },
        )

    sheet = reload_table(table)["Sheet1"]
    assert sheet["A1"].value == "Design Table for: FRAME-ASSY-MASTER"
    assert [cell.value for cell in sheet[2]] == [
        None,
        "$CONFIGURATION@SubFrame<1>",
        "$CONFIGURATION@SubFrame<2>",
        "$CONFIGURATION@SubFrame<3>",
        "$PRP@Description",
    ]
    assert [cell.value for cell in sheet[3]] == [
        "G01",
        "G01_HOR",
        "G01_VER1",
        "G01_VER2",
        "G01",
    ]
    assert sheet.max_row == 2 + len(FRAMES)


# The mixed-kind shape: dimensions, feature states, a global variable driven by
# an equation, a repeated five-column hole group, and a title block property.
LENGTH = sw.dimension("Length", "Boss-Extrude1")
ANGLE = sw.dimension("AngleV1", "Draft2")
DRAFT = sw.state("Draft2")
SHRINK = sw.dimension("shrink", "Move Face1")
SHRINK_STATE = sw.state("Move Face1")
QTY = sw.global_variable("hole_qty")
MATERIAL = sw.prop("Material")
PART_NUMBER = sw.prop("PartNo")

HOLE_GROUPS = [
    (
        sw.dimension(f"hole{n}", f"Sketch{n}"),
        sw.state(f"hole{n}"),
        sw.dimension(f"distance{n}", f"pattern{n}"),
        sw.state(f"pattern{n}"),
        sw.global_variable(f"hole{n}qty"),
    )
    for n in (1, 2)
]

SUPPRESSED_SLOT = (100, sw.SUPPRESSED, 100, sw.SUPPRESSED, 2)


def build_profile_table() -> sw.DesignTable:
    columns = [LENGTH, ANGLE, DRAFT, SHRINK, SHRINK_STATE, QTY, MATERIAL, PART_NUMBER]
    for group in HOLE_GROUPS:
        columns.extend(group)

    table = sw.DesignTable("PROFILE-MASTER", columns, round_floats=3)

    for index, frame_id in enumerate(FRAMES):
        values = {
            LENGTH: 1000.0 + index * 316.66666666666663,
            ANGLE: 22.5,
            DRAFT: sw.State.from_bool(index == 0),
            SHRINK: 0.4,
            SHRINK_STATE: sw.UNSUPPRESSED,
            QTY: sw.Expression("hole_pitch * 2"),
            MATERIAL: "6061-T6",
            PART_NUMBER: f"MFP-{index + 1:05d}",
        }
        for group_index, group in enumerate(HOLE_GROUPS):
            active = group_index <= index
            payload = (
                (50.0, sw.UNSUPPRESSED, 120.0, sw.UNSUPPRESSED, 4)
                if active
                else SUPPRESSED_SLOT
            )
            values.update(dict(zip(group, payload, strict=True)))
        table.add_configuration(frame_id, values, description=f"Profile {frame_id}")

    return table


def test_profile_table_headers(reload_table):
    sheet = reload_table(build_profile_table())["Sheet1"]
    assert [cell.value for cell in sheet[2]][:9] == [
        None,
        "Length@Boss-Extrude1",
        "AngleV1@Draft2",
        "$STATE@Draft2",
        "shrink@Move Face1",
        "$STATE@Move Face1",
        "$VALUE@hole_qty@Equations",
        "$PRP@Material",
        "$PRP@PartNo",
    ]
    assert sheet[2][-1].value == "$DESCRIPTION"


def test_profile_table_first_row(reload_table):
    sheet = reload_table(build_profile_table())["Sheet1"]
    headers = {cell.value: cell.column for cell in sheet[2] if cell.value}

    def value_at(row: int, header: str):
        return sheet.cell(row=row, column=headers[header]).value

    assert sheet["A3"].value == "G01"
    assert value_at(3, "Length@Boss-Extrude1") == 1000.0
    assert value_at(3, "$STATE@Draft2") == "S"
    assert value_at(3, "$PRP@PartNo") == "MFP-00001"
    assert value_at(3, "$DESCRIPTION") == "Profile G01"
    # The equation lands as literal text, not an Excel formula.
    assert value_at(3, "$VALUE@hole_qty@Equations") == "=hole_pitch * 2"
    # Hole group 2 is suppressed on the first configuration only.
    assert value_at(3, "$STATE@hole2") == "S"
    assert value_at(4, "$STATE@hole2") == "U"


def test_profile_table_rounds_its_floats(reload_table):
    sheet = reload_table(build_profile_table())["Sheet1"]
    headers = {cell.value: cell.column for cell in sheet[2] if cell.value}
    assert sheet.cell(row=4, column=headers["Length@Boss-Extrude1"]).value == 1316.667


def test_profile_table_validates_clean():
    assert build_profile_table().validate().issues == ()


def test_parse_header_migrates_a_string_list(reload_table):
    """The migration path: keep the header list you already have."""
    headers = [
        "Length@Boss-Extrude1",
        "$STATE@Draft2",
        "$VALUE@hole_qty@EQUATIONS",
        "$PRP@Description",
    ]
    table = sw.DesignTable(
        "PROFILE-MASTER",
        [sw.parse_header(header) for header in headers],
        state_format=sw.StateFormat.NUMERIC,
    )
    table.add_configuration(
        "G01",
        {
            "Length@Boss-Extrude1": 1000.0,
            "$STATE@Draft2": sw.SUPPRESSED,
            "$VALUE@hole_qty@Equations": 4,
            "$PRP@Description": "G01",
        },
    )
    sheet = reload_table(table)["Sheet1"]
    assert sheet["B2"].value == "Length@Boss-Extrude1"
    # Parsed from '@EQUATIONS', rendered in the vocabulary's own casing.
    assert sheet["D2"].value == "$VALUE@hole_qty@Equations"
    assert sheet["C3"].value == 1
