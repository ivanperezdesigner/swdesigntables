# swdesigntables

Build SOLIDWORKS design tables from Python, with typed headers instead of
hand-typed strings.

A design table is an Excel sheet embedded in a SOLIDWORKS model: each row makes
a configuration, each column drives a parameter. The format has a handful of
load-bearing details that are easy to get wrong and that fail *silently* — the
table inserts, nothing changes, and you go looking at the model. This package
writes those details for you and warns about the rest.

```bash
pip install swdesigntables
```

Only dependency: `openpyxl`. Pure Python, no SOLIDWORKS install needed to
generate a file.

**[Full reference, with a runnable example and the real output for every
feature →](https://github.com/ivanperezdesigner/swdesigntables/blob/main/DOCUMENTATION.md)**

## Quickstart

```python
import swdesigntables as sw

length = sw.dimension("Length", "Boss-Extrude1")
holes = sw.state("HolePattern")
material = sw.prop("Material")

table = sw.DesignTable("BRK-MASTER", [length, holes, material])
table.add_configuration(
    "BRK-025",
    {length: 25.0, holes: sw.SUPPRESSED, material: "6061-T6"},
    description="Short bracket",
)
table.add_configuration(
    "BRK-040",
    {length: 40.0, holes: sw.UNSUPPRESSED, material: "6061-T6"},
    description="Long bracket",
)

table.save("brk_master_dt.xlsx")
```

What comes out:

```
A1       'Design Table for: BRK-MASTER'
row 2    [None, 'Length@Boss-Extrude1', '$STATE@HolePattern', '$PRP@Material', '$DESCRIPTION']
row 3    ['BRK-025', 25, 'S', '6061-T6', 'Short bracket']
row 4    ['BRK-040', 40, 'U', '6061-T6', 'Long bracket']
```

Insert the result with **Insert → Tables → Design Table → From file**. That is
the only step that touches SOLIDWORKS: everything else, including the header
syntax, comes from this package.

## What it gets right so you do not have to

| Detail | Why it matters |
|---|---|
| `Design Table for: <model>` in A1 | The title cell SOLIDWORKS writes itself |
| Headers start in **B2**, A2 stays empty | Writing from A2 shifts every value one column left |
| Workbook-level defined name `Family` → `Sheet1!$A$2` | Without it SOLIDWORKS cannot find the table at all |
| Equation values written as literal text | `cell = "=W/2"` becomes an Excel *formula* with no cached result, and SOLIDWORKS reads an empty parameter |
| Fixed document timestamps | Two identical runs produce identical bytes, so git shows a change only when the table really changed |
| Numeric-looking strings stay strings | A part number of `0012` does not come back as `12` |

## Values are addressed by identity, never by column number

```python
length = table.add_column(sw.dimension("Length", "Boss-Extrude1"))
table.add_configuration("A", {length: 25.0})
```

You cannot pass a positional row. That is deliberate: mixing a
header-to-index map with literal column numbers is how a table silently starts
writing the wrong values after someone inserts a column in the middle.

Supplying a value for a column that was never declared is always an error, so
a typo loses nothing quietly.

## The parameter catalogue

Every parameter carries a **verification status**, readable at runtime via
`column.status` and listed by `sw.list_parameters()`.

- **`VERIFIED`** — the SOLIDWORKS help documents this exact spelling on a page
  of its own.
- **`DOCUMENTED`** — mentioned by some source, without a page that pins the
  syntax down.
- **`UNVERIFIED`** — registered at runtime by you, or otherwise unconfirmed.
  Using one emits an `unverified-parameter` warning.
- **`OBSOLETE`** — the SOLIDWORKS help says the parameter is obsolete. Using
  one emits an `obsolete-parameter` warning.

### Parts

| Factory | Header | Values |
|---|---|---|
| `dimension("Length", "Boss-Extrude1")` | `Length@Boss-Extrude1` | number |
| `global_variable("width")` | `$VALUE@width@Equations` | a constant decimal |
| `state("Draft2")` | `$STATE@Draft2` | `S`/`U`, or `1`/`0` |
| `prop("Material")` | `$PRP@Material` | text or number |
| `tolerance("D1", "Extrude1")` | `$TOLERANCE@D1@Extrude1` | tolerance keyword |
| `material("Bracket")` | `$LIBRARY:MATERIAL@Bracket` | `library:material` |
| `body_material("Body1", "Bracket")` | `$LIBRARY:MATERIAL@Body1@Bracket` | `library:material` |
| `hole_size("CBORE1")` | `$HW-SIZE@CBORE1` | a Hole Wizard size |
| `base_part_config("washer")` | `$CONFIGURATION@washer` | configuration name |
| `profile_size("Member1")` | `$PROFILE_SIZE@Member1` | profile size |
| `sketch_relation_state("Fixed1", "Sketch2")` | `$STATE@Fixed1@Sketch2` | `S`/`U` |
| `equation_enable(1)` | `$ENABLE@1@Equations` | `Y`/`N` |
| `skip_instances("LPattern1")` | `$SKIP@LPattern1` | `10,1;10,2;` |
| `mass()` | `$SW-MASS` | number |
| `center_of_mass()` | `$SW-COG` | `x, y, z` |

`state()` also covers sketches (`$STATE@Sketch1`) and lights
(`$STATE@Directional1`): one syntax, three kinds of target.

### Parts and assemblies

| Factory | Header | Values |
|---|---|---|
| `description()` | `$DESCRIPTION` | text |
| `parent()` | `$PARENT` | configuration name |
| `part_number()` | `$PARTNUMBER` | text, or `$D`/`$P`/`$C` |
| `comment()` | `$COMMENT` | text |
| `color()` | `$COLOR` | 32-bit RGB integer |
| `user_notes()` | `$USER_NOTES` | text; SOLIDWORKS ignores the column |

### Assemblies

| Factory | Header | Values |
|---|---|---|
| `component_config("Arm", 1)` | `$CONFIGURATION@Arm<1>` | configuration name |
| `component_state("Screw", 2)` | `$STATE@Screw<2>` | `S`/`R` |
| `component_fixed("Screw")` | `$FIXED@Screw` | `Y`/`N` |
| `display_state()` | `$DISPLAYSTATE` | display state name |
| `never_expand_in_bom()` | `$NEVER_EXPAND_IN_BOM` | `Y`/`N` |

`$CONFIGURATION@X` means two different things, and the instance number tells
them apart: with one it is a component of an assembly, without one it is the
base part of a part document.

### Not confirmed, and obsolete

| Factory | Header | Status |
|---|---|---|
| `suppress_new_features()` | `$SUPPRESS NEW FEATURES` | unverified |
| `suppress_new_components()` | `$SUPPRESS NEW COMPONENTS` | unverified |
| `component_display_state("Screw", 2)` | `$DISPLAYSTATE@Screw<2>` | unverified |
| `component_visibility("Screw", 2)` | `$SHOW@Screw<2>` | **obsolete** |

`$SHOW` is obsolete in the SOLIDWORKS help itself; component visibility belongs
to display states now. It stays in the catalogue only so an old table still
round-trips through `parse_header`.

**Sheet metal (`$SM-…`) is deliberately absent.** No source consulted confirms
its syntax, and shipping an invented factory is worse than shipping none. Use
`raw()` or `register_parameter()`.

### Nothing is out of reach

```python
sw.raw("$WHATEVER@Thing<3>")          # any header at all, unchecked

sw.register_parameter(                # a new typed factory, at runtime
    "sheet_metal_thickness",
    template="$SM-THICKNESS",
    summary="Sheet metal thickness.",
    value_kind=sw.ValueKind.NUMBER,
)
sw.column("sheet_metal_thickness")
```

## Reusable bases

`TableTemplate` holds everything that does not change row to row — model, output
directory, file name, columns, naming rule — so every script in a project starts
from the same base.

```python
from pathlib import Path
import swdesigntables as sw

BRACKET = sw.TableTemplate(
    model_name="BRK-MASTER",
    output_dir=Path("tables"),
    file_name="brk_master_dt.xlsx",
    columns=(length, width, sw.description()),
    config_name=lambda width, length: f"BRK-{width:03d}-{length:03d}",
    round_floats=3,
)

table = BRACKET.new_table()
table.add_configuration(BRACKET.name_for(width=25, length=40), {...})
table.save()                      # goes to tables/brk_master_dt.xlsx
```

It is frozen; `BRACKET.replace(model_name="BRK-HEAVY")` gives you a variant
without disturbing the original.

To start from an empty but valid file:

```python
sw.blank_table("BRK-MASTER", [length, width], path="skeleton.xlsx")
```

## Suppression: `S`/`U` or `1`/`0`

SOLIDWORKS documents both spellings for feature suppression, and neither is
silently rewritten into the other:

```python
sw.DesignTable(..., state_format=sw.StateFormat.NUMERIC)   # writes 1 / 0
sw.State.from_legacy_int(1)                                # -> State.SUPPRESSED
```

Component suppression is a different vocabulary — `ComponentState` is `S`/`R`,
where `R` is Resolved — and mixing them up is caught.

## Migrating a script that already has header strings

`parse_header` turns an existing header string into the typed column that
renders it, so a list you already have keeps working:

```python
table = sw.DesignTable(
    "Extrusion Profile",
    columns=[sw.parse_header(h) for h in HEADERS],
    state_format=sw.StateFormat.NUMERIC,
)
```

Anything unrecognized becomes a `raw()` column rather than an error.

## Validation

```python
report = table.validate()
for issue in report.issues:
    print(issue)
```

Issue codes are stable across releases; message wording is not, so match on the
code. Errors stop the write, warnings do not.

A selection of what is caught: duplicate columns and configurations,
configuration names containing `/ \ : * ? " < > |`, values for undeclared
columns, `$PARENT` cycles and children placed before their parent, the reserved
`_SWX` sheet name, a state letter in a numeric column, an equation in a global
variable column, an obsolete or unverified parameter, and
`equations-dimension-conflict` — driving both a dimension and a global variable
of the same name, which usually means someone expected the dimension column to
win an argument it cannot win.

Three levels of strictness:

```python
sw.DesignTable(...)                              # errors raise, warnings warn
sw.DesignTable(..., strict=False)                # everything degrades to a warning
sw.DesignTable(..., ignore=("float-precision",)) # silence one code
```

In CI, promote warnings so they cannot rot:

```bash
python -W error::swdesigntables.errors.DesignTableWarning build_tables.py
```

### What validation cannot do

Without a live model there is nothing to check names against. A misspelled
feature name still produces a column SOLIDWORKS silently ignores. This package
only catches problems of *shape* — stray whitespace, an embedded `@`, a value of
the wrong kind. Claiming more is how people learn to stop reading warnings.

## Extra sheets, and why `_SWX` is refused

You can add your own sheets — source data, notes, a parameter legend — and hide
them:

```python
table.add_sheet("Notes", [["Source"], ["main_db.xlsx"]], hidden=True)
table.add_defined_name("Lengths", "Sheet1!$B$3:$B$50")
```

`Sheet1` always stays first and visible. Hidden means `hidden`, never
`veryHidden`, so you can unhide it in Excel when something misbehaves.

**`_SWX` is rejected.** When SOLIDWORKS embeds a design table it creates a
hidden `_SWX` sheet and a `_SWX_0` defined name of its own. Authoring them here
produces a table SOLIDWORKS cannot reconcile. Likewise `Family` is created
automatically and adding it by hand is an error.

## Design tables are not the source of truth

When a table is generated by a script it stays an internal detail of the
generator. The source of truth is what lives outside: a database, a spreadsheet,
a configuration file. If the embedded table becomes the source, no other process
can read the data without opening SOLIDWORKS.

```
external source -> rules -> design table -> configurations
```

## Preparing the master model

The table can only be as good as the model underneath it:

1. **Name your dimensions.** Without a name they stay `D1@Sketch1`, and in three
   weeks nobody knows which is which.
2. **Name the features you intend to suppress.** `$STATE@Cut-Extrude7` breaks
   the moment someone reorders the tree.
3. **One brain only.** Equations or the table, not both governing the same thing.
   A dimension driven by an equation cannot be driven by the table — drive the
   global variable instead.
4. **Set document units to at least 2 decimals.** At 0 decimals a radius of 2.4
   shows as `2`, in the model and on the drawing.
5. **Name the model after the family, not a variant.** Rename *before* creating
   drawings or assemblies, or you break the references.
6. **Model the full case and suppress downwards.** Removing is easier than
   creating.

## License

MIT.
