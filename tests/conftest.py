"""Shared test helpers."""

from __future__ import annotations

import io

import pytest
from openpyxl import load_workbook

import swdesigntables as sw


@pytest.fixture
def reload_table():
    """Build a table, save it to memory, and hand back the reloaded workbook.

    Assertions go against what a reader actually finds in the file, not against
    the in-memory model, which is the only way to catch a writer that quietly
    puts something in the wrong cell.
    """

    def _reload(table: sw.DesignTable):
        buffer = io.BytesIO()
        table.save(buffer)
        buffer.seek(0)
        return load_workbook(buffer)

    return _reload


@pytest.fixture
def simple_columns():
    """A small mixed set of verified columns."""
    return {
        "length": sw.dimension("Length", "Boss-Extrude1"),
        "qty": sw.global_variable("hole_qty"),
        "draft": sw.state("Draft2"),
        "material": sw.prop("Material"),
    }


@pytest.fixture
def simple_table(simple_columns):
    """A two-configuration table using ``simple_columns``."""
    columns = simple_columns
    table = sw.DesignTable("BRK-MASTER", list(columns.values()))
    table.add_configuration(
        "BRK-025",
        {
            columns["length"]: 25.0,
            columns["qty"]: 2,
            columns["draft"]: sw.SUPPRESSED,
            columns["material"]: "6061-T6",
        },
    )
    table.add_configuration(
        "BRK-040",
        {
            columns["length"]: 40.0,
            columns["qty"]: 4,
            columns["draft"]: sw.UNSUPPRESSED,
            columns["material"]: "6061-T6",
        },
    )
    return table
