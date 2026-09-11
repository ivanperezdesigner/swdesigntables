"""Two identical builds must produce identical bytes.

Without fixed document timestamps every regenerated table looks modified in
git, which makes "did this actually change?" unanswerable.
"""

from __future__ import annotations

import swdesigntables as sw


def build() -> sw.DesignTable:
    length = sw.dimension("Length", "Boss-Extrude1")
    table = sw.DesignTable("BRK-MASTER", [length])
    table.add_configuration("BRK-025", {length: 25.0})
    table.add_configuration("BRK-040", {length: 40.0})
    return table


def test_same_table_twice_is_byte_identical():
    assert build().to_bytes() == build().to_bytes()


def test_a_changed_value_changes_the_bytes():
    other = build()
    other.add_configuration("BRK-060", {other.columns[0]: 60.0})
    assert build().to_bytes() != other.to_bytes()


def test_document_timestamps_are_fixed():
    from swdesigntables.writer import FIXED_TIMESTAMP

    workbook = build().to_workbook()
    assert workbook.properties.created == FIXED_TIMESTAMP
    assert workbook.properties.modified == FIXED_TIMESTAMP
