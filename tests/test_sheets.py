"""Extra sheets and workbook defined names."""

from __future__ import annotations

import swdesigntables as sw


def test_sheet1_stays_first_and_visible(simple_table, reload_table):
    simple_table.add_sheet("Notes", [["Source"], ["main_db.xlsx"]], hidden=True)
    workbook = reload_table(simple_table)
    assert workbook.sheetnames[0] == "Sheet1"
    assert workbook["Sheet1"].sheet_state == "visible"


def test_hidden_sheet_is_hidden_not_very_hidden(simple_table, reload_table):
    """You must be able to unhide it in Excel when the table misbehaves."""
    simple_table.add_sheet("Notes", [["Source"], ["main_db.xlsx"]], hidden=True)
    sheet = reload_table(simple_table)["Notes"]
    assert sheet.sheet_state == "hidden"


def test_visible_extra_sheet_stays_visible(simple_table, reload_table):
    simple_table.add_sheet("Legend", [["Column", "Meaning"]])
    assert reload_table(simple_table)["Legend"].sheet_state == "visible"


def test_extra_sheet_contents_land_from_a1(simple_table, reload_table):
    simple_table.add_sheet("Notes", [["Source", 1], ["main_db.xlsx", 2.5]])
    sheet = reload_table(simple_table)["Notes"]
    assert sheet["A1"].value == "Source"
    assert sheet["B1"].value == 1
    assert sheet["A2"].value == "main_db.xlsx"
    assert sheet["B2"].value == 2.5


def test_extra_defined_names_are_written(simple_table, reload_table):
    simple_table.add_defined_name("Lengths", "Sheet1!$B$3:$B$50")
    workbook = reload_table(simple_table)
    assert workbook.defined_names["Lengths"].attr_text == "Sheet1!$B$3:$B$50"
    assert "Family" in workbook.defined_names


def test_defined_names_property_excludes_family(simple_table):
    simple_table.add_defined_name("Lengths", "Sheet1!$B$3:$B$50")
    assert simple_table.defined_names == {"Lengths": "Sheet1!$B$3:$B$50"}


def test_sheet_model_is_exposed(simple_table):
    sheet = simple_table.add_sheet("Notes", [["a", "b"]], hidden=True)
    assert isinstance(sheet, sw.ExtraSheet)
    assert sheet.rows == (("a", "b"),)
    assert simple_table.extra_sheets == (sheet,)
