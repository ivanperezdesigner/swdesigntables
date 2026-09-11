"""Ordering, identity and the row data model."""

from __future__ import annotations

import pytest

import swdesigntables as sw


def test_columns_keep_insertion_order():
    columns = [sw.prop("Z"), sw.prop("A"), sw.prop("M")]
    table = sw.DesignTable("M", columns)
    assert table.headers() == ("$PRP@Z", "$PRP@A", "$PRP@M")


def test_configurations_keep_insertion_order():
    table = sw.DesignTable("M", [sw.prop("X")])
    for name in ("C", "A", "B"):
        table.add_configuration(name)
    assert [c.name for c in table.configurations] == ["C", "A", "B"]


def test_add_column_returns_the_key_you_use():
    table = sw.DesignTable("M")
    length = table.add_column(sw.dimension("Length", "Sketch1"))
    table.add_configuration("A", {length: 10})
    assert table.configurations[0].values[length.key] == 10


def test_strings_work_anywhere_a_column_does():
    """Half-migrated scripts must keep working."""
    table = sw.DesignTable("M", ["Length@Sketch1", "$STATE@Draft2"])
    table.add_configuration("A", {"Length@Sketch1": 10, "$STATE@Draft2": sw.SUPPRESSED})
    assert table.headers() == ("Length@Sketch1", "$STATE@Draft2")
    assert table.columns[0] == sw.dimension("Length", "Sketch1")


def test_column_for_finds_a_column_by_header():
    table = sw.DesignTable("M", [sw.state("Draft2")])
    assert table.column_for("$STATE@Draft2") == sw.state("Draft2")
    with pytest.raises(sw.UnknownColumnError):
        table.column_for("$STATE@Nope")


def test_description_and_parent_add_their_columns_once():
    table = sw.DesignTable("M", [sw.prop("X")])
    table.add_configuration("A", description="first", parent="")
    table.add_configuration("B", description="second")
    assert table.headers().count("$DESCRIPTION") == 1
    assert "$DESCRIPTION" in table.headers()


def test_none_is_written_as_blank_not_filled(reload_table):
    column = sw.prop("X")
    table = sw.DesignTable("M", [column], missing=sw.MissingValue.FILL, fill_value="?")
    table.add_configuration("A", {column: None})
    table.add_configuration("B")
    sheet = reload_table(table)["Sheet1"]
    assert sheet["B3"].value is None
    assert sheet["B4"].value == "?"


def test_sanitize_configuration_name():
    assert sw.sanitize_configuration_name("A/B:C") == "A-B-C"
    assert sw.sanitize_configuration_name("A|B", replacement="_") == "A_B"
    assert sw.sanitize_configuration_name("  A/B  ") == "A-B"
    # Replacing leaves something usable; only an empty result is refused.
    assert sw.sanitize_configuration_name("///") == "---"
    with pytest.raises(ValueError, match="Nothing usable left"):
        sw.sanitize_configuration_name("   ")


def test_sanitize_is_opt_in_never_automatic():
    """A part number is the caller's to decide, not the library's to rewrite."""
    table = sw.DesignTable("M", [sw.prop("X")], strict=False)
    table.add_configuration("A/B")
    assert table.configurations[0].name == "A/B"


def test_repr_is_useful():
    table = sw.DesignTable("BRK-MASTER", [sw.prop("X")])
    table.add_configuration("A")
    assert "BRK-MASTER" in repr(table)
    assert "columns=1" in repr(table)


def test_spanish_vocabulary_changes_only_the_prefix():
    spanish = sw.Vocabulary(state="$ESTADO")
    table = sw.DesignTable("M", [sw.state("Draft2"), sw.prop("X")], vocabulary=spanish)
    assert table.headers() == ("$ESTADO@Draft2", "$PRP@X")
