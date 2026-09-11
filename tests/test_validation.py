"""One test per issue code, asserting the code rather than the wording."""

from __future__ import annotations

import pytest

import swdesigntables as sw


def codes(table: sw.DesignTable) -> set[str]:
    return {issue.code for issue in table.validate().issues}


def lenient(model: str = "M", **kwargs) -> sw.DesignTable:
    """A table that collects issues instead of raising at the call site."""
    kwargs.setdefault("strict", False)
    return sw.DesignTable(model, **kwargs)


# --- errors --------------------------------------------------------------


def test_empty_model_name():
    table = lenient("   ", columns=[sw.prop("X")])
    table.add_configuration("A", {sw.prop("X"): 1})
    assert "empty-model-name" in codes(table)


def test_no_columns_and_no_configurations():
    assert {"no-columns", "no-configurations"} <= codes(lenient())


def test_duplicate_column_raises_at_the_call_site():
    table = sw.DesignTable("M", [sw.state("Draft2")])
    with pytest.raises(sw.DuplicateColumnError, match="already in this table"):
        table.add_column(sw.state("Draft2"))


def test_duplicate_column_returns_the_existing_one_when_lenient():
    table = lenient("M", columns=[sw.state("Draft2")])
    with pytest.warns(sw.DesignTableWarning, match="duplicate-column"):
        again = table.add_column(sw.state("Draft2"))
    assert again == sw.state("Draft2")
    assert len(table.columns) == 1


def test_duplicate_configuration_is_case_insensitive():
    """SOLIDWORKS configuration names do not differ by case."""
    table = sw.DesignTable("M", [sw.prop("X")])
    table.add_configuration("BRK-1")
    with pytest.raises(sw.DuplicateConfigurationError):
        table.add_configuration("brk-1")


@pytest.mark.parametrize("name", ["A/B", "A:B", "A*B", 'A"B', "A<B", "A|B", "  A"])
def test_invalid_configuration_name(name):
    table = lenient("M", columns=[sw.prop("X")])
    table.add_configuration(name)
    assert "invalid-configuration-name" in codes(table)


def test_configuration_name_length_limits():
    table = lenient("M", columns=[sw.prop("X")])
    table.add_configuration("x" * 200)
    table.add_configuration("y" * 300)
    found = codes(table)
    assert "long-configuration-name" in found
    assert "invalid-configuration-name" in found


def test_unknown_column_raises_at_the_call_site():
    table = sw.DesignTable("M", [sw.prop("X")])
    with pytest.raises(sw.UnknownColumnError, match="No column with header"):
        table.add_configuration("A", {"$PRP@NotDeclared": 1})


def test_reserved_sheet_name_is_refused():
    """SOLIDWORKS writes _SWX itself when it embeds the table."""
    table = sw.DesignTable("M", [sw.prop("X")])
    with pytest.raises(sw.ReservedNameError, match="_SWX"):
        table.add_sheet("_SWX", [["x"]])


def test_reserved_defined_name_is_refused():
    table = sw.DesignTable("M", [sw.prop("X")])
    with pytest.raises(sw.ReservedNameError, match="Family"):
        table.add_defined_name("Family", "Sheet1!$A$2")


def test_duplicate_sheet_name():
    table = lenient("M", columns=[sw.prop("X")])
    table.add_configuration("A")
    table.add_sheet("Notes", [["a"]])
    table.add_sheet("notes", [["b"]])
    assert "duplicate-sheet-name" in codes(table)


def test_parent_not_found():
    table = lenient("M", columns=[sw.parent()])
    table.add_configuration("A", parent="Nope")
    assert "parent-not-found" in codes(table)


def test_parent_after_child():
    table = lenient("M", columns=[sw.parent()])
    table.add_configuration("Child", parent="Base")
    table.add_configuration("Base")
    assert "parent-after-child" in codes(table)


def test_parent_cycle():
    table = lenient("M", columns=[sw.parent()])
    table.add_configuration("A", parent="B")
    table.add_configuration("B", parent="A")
    assert "parent-cycle" in codes(table)


def test_self_parent_is_a_cycle():
    table = lenient("M", columns=[sw.parent()])
    table.add_configuration("A", parent="A")
    assert "parent-cycle" in codes(table)


def test_sort_by_parent_puts_parents_first():
    table = lenient("M", columns=[sw.parent()])
    table.add_configuration("Child", parent="Base")
    table.add_configuration("Base")
    table.sort_by_parent()
    assert [c.name for c in table.configurations] == ["Base", "Child"]
    assert "parent-after-child" not in codes(table)


def test_wrong_value_type_in_a_yes_no_column():
    column = sw.never_expand_in_bom()
    table = lenient("M", columns=[column], ignore=("unverified-parameter",))
    table.add_configuration("A", {column: "yes please"})
    assert "wrong-value-type" in codes(table)


# --- warnings ------------------------------------------------------------


def test_equations_dimension_conflict():
    """The trap: an equation-governed dimension cannot be driven by the table."""
    table = lenient("M", columns=[sw.dimension("width", "Sketch1"), sw.global_variable("width")])
    table.add_configuration("A")
    assert "equations-dimension-conflict" in codes(table)


def test_unverified_parameter_warns():
    table = lenient("M", columns=[sw.component_display_state("Screw", 2)])
    table.add_configuration("A")
    assert "unverified-parameter" in codes(table)


def test_raw_column_warns_under_its_own_code():
    table = lenient("M", columns=[sw.raw("$ANYTHING")])
    table.add_configuration("A")
    found = codes(table)
    assert "raw-column" in found
    assert "unverified-parameter" not in found


def test_suspicious_feature_name():
    table = lenient("M", columns=[sw.state(" Draft2 ")])
    table.add_configuration("A")
    assert "suspicious-feature-name" in codes(table)


def test_state_letter_in_a_numeric_column():
    column = sw.dimension("Length", "Sketch1")
    table = lenient("M", columns=[column])
    table.add_configuration("A", {column: sw.SUPPRESSED})
    assert "text-in-numeric-column" in codes(table)


def test_number_in_a_state_column_is_tolerated():
    """1/0 is a legitimate spelling, so it must not be flagged."""
    column = sw.state("Draft2")
    table = lenient("M", columns=[column])
    table.add_configuration("A", {column: 1})
    assert "non-state-value-in-state-column" not in codes(table)


def test_feature_letters_in_a_component_state_column():
    column = sw.component_state("Screw", 2)
    table = lenient("M", columns=[column], ignore=("unverified-parameter",))
    table.add_configuration("A", {column: sw.SUPPRESSED})
    assert "non-state-value-in-state-column" in codes(table)


def test_float_precision():
    column = sw.dimension("Length", "Sketch1")
    table = lenient("M", columns=[column])
    table.add_configuration("A", {column: 316.66666666666663})
    assert "float-precision" in codes(table)


def test_round_floats_silences_float_precision():
    column = sw.dimension("Length", "Sketch1")
    table = lenient("M", columns=[column], round_floats=3)
    table.add_configuration("A", {column: 316.66666666666663})
    assert "float-precision" not in codes(table)


def test_read_only_column_warns():
    """A caller can register a read-only parameter of their own."""
    sw.register_parameter(
        "computed_thing",
        template="$COMPUTED-THING",
        summary="Something SOLIDWORKS calculates.",
        value_kind=sw.ValueKind.READ_ONLY,
    )
    column = sw.column("computed_thing")
    table = lenient("M", columns=[column], ignore=("unverified-parameter",))
    table.add_configuration("A", {column: 1.0})
    assert "read-only-column" in codes(table)


def test_obsolete_parameter_warns_under_its_own_code():
    table = lenient("M", columns=[sw.component_visibility("Screw", 2)])
    table.add_configuration("A")
    found = codes(table)
    assert "obsolete-parameter" in found
    assert "unverified-parameter" not in found


def test_expression_in_a_global_variable_warns():
    """SOLIDWORKS takes only constant decimals for a global variable."""
    variable = sw.global_variable("width")
    table = lenient("M", columns=[variable])
    table.add_configuration("A", {variable: sw.Expression("W/2")})
    assert "expression-in-global-variable" in codes(table)


def test_mass_is_writable_not_read_only():
    """$SW-MASS overrides the calculated value; it is not read only."""
    column = sw.mass()
    table = lenient("M", columns=[column])
    table.add_configuration("A", {column: 2.5})
    assert "read-only-column" not in codes(table)


# --- strictness ----------------------------------------------------------


def test_strict_true_raises_on_save(tmp_path):
    table = sw.DesignTable("", [sw.prop("X")])
    table.add_configuration("A", {sw.prop("X"): 1})
    with pytest.raises(sw.ValidationError) as caught:
        table.save(tmp_path / "x.xlsx")
    assert "empty-model-name" in {issue.code for issue in caught.value.report.errors}


def test_strict_false_downgrades_errors_and_still_writes(tmp_path):
    table = lenient("", columns=[sw.prop("X")])
    table.add_configuration("A", {sw.prop("X"): 1})
    with pytest.warns(sw.DesignTableWarning, match="empty-model-name"):
        written = table.save(tmp_path / "x.xlsx")
    assert written.exists()


def test_ignore_removes_exactly_one_code():
    unverified = sw.suppress_new_features()
    table = lenient("M", columns=[unverified, sw.raw("$X")])
    table.add_configuration("A")
    found = codes(sw.DesignTable(
        "M",
        [unverified, sw.raw("$X")],
        strict=False,
        ignore=("unverified-parameter",),
    ))
    assert "unverified-parameter" in codes(table)
    assert "unverified-parameter" not in found
    assert "raw-column" in found


def test_report_bool_and_raise_for_errors():
    table = lenient("M", columns=[sw.prop("X")])
    table.add_configuration("A", {sw.prop("X"): 1})
    report = table.validate()
    assert bool(report) is True
    report.raise_for_errors()


def test_issue_str_includes_code_and_location():
    table = lenient("M", columns=[sw.state(" Draft2 ")])
    table.add_configuration("A")
    issue = next(i for i in table.validate().issues if i.code == "suspicious-feature-name")
    assert "suspicious-feature-name" in str(issue)
    assert "$STATE@ Draft2 " in str(issue)
