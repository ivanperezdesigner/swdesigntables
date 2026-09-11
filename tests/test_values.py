"""Value vocabularies and their serialization."""

from __future__ import annotations

import pytest

import swdesigntables as sw
from swdesigntables.values import normalize


def test_state_from_bool():
    assert sw.State.from_bool(True) is sw.State.SUPPRESSED
    assert sw.State.from_bool(False) is sw.State.UNSUPPRESSED


def test_state_from_legacy_int():
    """1/0 is the convention used by hand-written generators in the wild."""
    assert sw.State.from_legacy_int(1) is sw.State.SUPPRESSED
    assert sw.State.from_legacy_int(0) is sw.State.UNSUPPRESSED
    with pytest.raises(ValueError, match="must be 0 or 1"):
        sw.State.from_legacy_int(2)


def test_state_serialization_follows_the_format():
    assert normalize(sw.SUPPRESSED)[0] == "S"
    assert normalize(sw.SUPPRESSED, state_format=sw.StateFormat.NUMERIC)[0] == 1
    assert normalize(sw.UNSUPPRESSED, state_format=sw.StateFormat.NUMERIC)[0] == 0


def test_component_state_uses_different_letters():
    """A component is Resolved, not Unsuppressed. Mixing them does nothing."""
    assert sw.ComponentState.RESOLVED.value == "R"
    assert sw.ComponentState.SUPPRESSED.value == "S"
    assert normalize(sw.ComponentState.RESOLVED)[0] == "R"


def test_component_state_ignores_the_numeric_format():
    """Only feature suppression has a 1/0 spelling."""
    assert normalize(sw.ComponentState.SUPPRESSED, state_format=sw.StateFormat.NUMERIC)[0] == "S"


def test_yes_no():
    assert sw.YesNo.from_bool(True) is sw.YesNo.YES
    assert normalize(sw.YesNo.NO)[0] == "N"


def test_expression_is_flagged_as_text():
    payload, force_text = normalize(sw.Expression("W/2"))
    assert payload == "=W/2"
    assert force_text is True


def test_expression_rejects_empty():
    with pytest.raises(ValueError, match="cannot be empty"):
        sw.Expression("   ")


def test_none_passes_through():
    assert normalize(None) == (None, False)


def test_round_floats_applies_to_floats_only():
    assert normalize(1.23456789, round_floats=3)[0] == 1.235
    assert normalize(7, round_floats=3)[0] == 7
    assert normalize("7.123456789", round_floats=3)[0] == "7.123456789"


def test_unsupported_type_is_refused():
    with pytest.raises(TypeError, match="Unsupported cell value"):
        normalize(object())
