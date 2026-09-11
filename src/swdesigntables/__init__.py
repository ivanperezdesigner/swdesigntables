"""Build SOLIDWORKS design tables from Python.

A design table is an Excel sheet embedded in a SOLIDWORKS model: each row makes
a configuration, each column drives a parameter. The file format has a few
load-bearing details that are easy to get wrong and fail silently, so this
package writes them for you:

* ``Design Table for: <model>`` in A1
* headers from **B2**, never A2
* the workbook-level defined name ``Family`` pointing at ``Sheet1!$A$2``
* equation values written as literal text, not as Excel formulas

Quickstart::

    import swdesigntables as sw

    length = sw.dimension("Length", "Boss-Extrude1")
    holes = sw.state("HolePattern")

    table = sw.DesignTable("BRK-MASTER", [length, holes])
    table.add_configuration("BRK-025", {length: 25.0, holes: sw.SUPPRESSED})
    table.add_configuration("BRK-040", {length: 40.0, holes: sw.UNSUPPRESSED})
    table.save("brk_master_dt.xlsx")

Then insert it with Insert > Tables > Design Table > From file.
"""

from __future__ import annotations

__version__ = "0.2.0"

from swdesigntables.columns import (
    Column,
    base_part_config,
    body_material,
    center_of_mass,
    color,
    column,
    comment,
    component_config,
    component_display_state,
    component_fixed,
    component_state,
    component_visibility,
    description,
    dimension,
    display_state,
    equation_enable,
    global_variable,
    hole_size,
    mass,
    material,
    never_expand_in_bom,
    parent,
    parse_header,
    part_number,
    profile_size,
    prop,
    raw,
    sketch_relation_state,
    skip_instances,
    state,
    suppress_new_components,
    suppress_new_features,
    sw_property,
    tolerance,
    user_notes,
)
from swdesigntables.errors import (
    DesignTableError,
    DesignTableWarning,
    DuplicateColumnError,
    DuplicateConfigurationError,
    InvalidNameError,
    ReservedNameError,
    UnknownColumnError,
    UnknownParameterError,
    ValidationError,
)
from swdesigntables.parameters import (
    ParameterSpec,
    Status,
    ValueKind,
    get_parameter,
    list_parameters,
    register_parameter,
)
from swdesigntables.table import (
    Configuration,
    DesignTable,
    ExtraSheet,
    sanitize_configuration_name,
)
from swdesigntables.template import TableTemplate, blank_table
from swdesigntables.validation import Issue, Severity, ValidationReport
from swdesigntables.values import (
    SUPPRESSED,
    UNSUPPRESSED,
    CellValue,
    ComponentState,
    Expression,
    MissingValue,
    State,
    StateFormat,
    YesNo,
)
from swdesigntables.vocabulary import ENGLISH, Vocabulary
from swdesigntables.writer import FAMILY_NAME, TITLE_PREFIX

__all__ = [
    "__version__",
    # model
    "DesignTable",
    "Configuration",
    "ExtraSheet",
    "TableTemplate",
    "blank_table",
    "sanitize_configuration_name",
    # columns
    "Column",
    "column",
    "parse_header",
    "dimension",
    "global_variable",
    "state",
    "prop",
    "description",
    "parent",
    "display_state",
    "component_config",
    "component_state",
    "component_visibility",
    "component_fixed",
    "component_display_state",
    "comment",
    "color",
    "part_number",
    "user_notes",
    "never_expand_in_bom",
    "suppress_new_features",
    "suppress_new_components",
    "sw_property",
    "mass",
    "center_of_mass",
    "tolerance",
    "base_part_config",
    "material",
    "body_material",
    "hole_size",
    "profile_size",
    "equation_enable",
    "sketch_relation_state",
    "skip_instances",
    "raw",
    # parameters
    "ParameterSpec",
    "Status",
    "ValueKind",
    "register_parameter",
    "get_parameter",
    "list_parameters",
    # values
    "State",
    "ComponentState",
    "YesNo",
    "StateFormat",
    "Expression",
    "MissingValue",
    "CellValue",
    "SUPPRESSED",
    "UNSUPPRESSED",
    # vocabulary
    "Vocabulary",
    "ENGLISH",
    # validation
    "ValidationReport",
    "Issue",
    "Severity",
    # errors
    "DesignTableError",
    "ValidationError",
    "DuplicateColumnError",
    "DuplicateConfigurationError",
    "UnknownColumnError",
    "InvalidNameError",
    "ReservedNameError",
    "UnknownParameterError",
    "DesignTableWarning",
    # constants
    "FAMILY_NAME",
    "TITLE_PREFIX",
]
