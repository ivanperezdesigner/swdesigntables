# swdesigntables — reference

Every example here was run against the version of the package in this
repository, and every output is what it actually printed. Nothing is
illustrative.

- [1. The whole flow](#1-the-whole-flow)
- [2. Columns](#2-columns)
- [3. Values](#3-values)
- [4. Building a table](#4-building-a-table)
- [5. Derived configurations](#5-derived-configurations)
- [6. Extra sheets and defined names](#6-extra-sheets-and-defined-names)
- [7. Validation](#7-validation)
- [8. Strictness](#8-strictness)
- [9. Templates and skeletons](#9-templates-and-skeletons)
- [10. The catalogue](#10-the-catalogue)
- [11. Migrating existing headers](#11-migrating-existing-headers)
- [12. Output](#12-output)
- [13. Other languages](#13-other-languages)
- [14. What the package does not do](#14-what-the-package-does-not-do)

---

## 1. The whole flow

Four objects, in order. A column is built by a factory, a table holds columns,
a configuration is one row of values keyed by column, and saving writes the
file.

```python
import swdesigntables as sw

length = sw.dimension("Length", "Boss-Extrude1")
holes = sw.state("HolePattern")
material = sw.prop("Material")

table = sw.DesignTable("BRK-MASTER", [length, holes, material])
table.add_configuration(
    "BRK-025", {length: 25.0, holes: sw.SUPPRESSED, material: "6061-T6"},
    description="Short",
)
table.add_configuration(
    "BRK-040", {length: 40.0, holes: sw.UNSUPPRESSED, material: "6061-T6"},
    description="Long",
)
table.save("brk_master_dt.xlsx")
```

The sheet that comes out:

```
A1       'Design Table for: BRK-MASTER'
row 2    [None, 'Length@Boss-Extrude1', '$STATE@HolePattern', '$PRP@Material', '$DESCRIPTION']
row 3    ['BRK-025', 25, 'S', '6061-T6', 'Short']
row 4    ['BRK-040', 40, 'U', '6061-T6', 'Long']

defined names: {'Family': 'Sheet1!$A$2'}
```

Insert it with **Insert → Tables → Design Table → From file**.

Three details that decide whether SOLIDWORKS reads the file at all are written
for you: the title in A1, headers starting at B2 with A2 left empty, and the
workbook-level defined name `Family` pointing at `Sheet1!$A$2`.

---

## 2. Columns

A factory returns a `Column`: frozen, hashable, and the key you use when
supplying row values. Two columns built the same way are equal, so you can
rebuild one anywhere in a script and it still addresses the same column.

```python
c = sw.dimension("Length", "Boss-Extrude1")

c.header()      -> 'Length@Boss-Extrude1'
c.key           -> 'dimension(dimension=Length,feature=Boss-Extrude1)'
c.status        -> Status.VERIFIED
c.value_kind    -> ValueKind.NUMBER
str(c)          -> 'Length@Boss-Extrude1'

sw.dimension("Length", "Boss-Extrude1") == sw.dimension("Length", "Boss-Extrude1")
-> True
```

### Parts

```python
sw.dimension("Length", "Boss-Extrude1")   -> 'Length@Boss-Extrude1'
sw.global_variable("width")               -> '$VALUE@width@Equations'
sw.state("Draft2")                        -> '$STATE@Draft2'
sw.prop("Material")                       -> '$PRP@Material'
sw.tolerance("D1", "Extrude1")            -> '$TOLERANCE@D1@Extrude1'
sw.material("Bracket")                    -> '$LIBRARY:MATERIAL@Bracket'
sw.body_material("Body1", "Bracket")      -> '$LIBRARY:MATERIAL@Body1@Bracket'
sw.hole_size("CBORE1")                    -> '$HW-SIZE@CBORE1'
sw.base_part_config("washer")             -> '$CONFIGURATION@washer'
sw.profile_size("Member1")                -> '$PROFILE_SIZE@Member1'
sw.sketch_relation_state("Fixed1", "Sketch2") -> '$STATE@Fixed1@Sketch2'
sw.equation_enable(1)                     -> '$ENABLE@1@Equations'
sw.skip_instances("LPattern1")            -> '$SKIP@LPattern1'
sw.mass()                                 -> '$SW-MASS'
sw.center_of_mass()                       -> '$SW-COG'
sw.sw_property("Mass")                    -> '$SW-Mass'
```

`state()` covers three things that share one syntax: features
(`$STATE@Draft2`), sketches (`$STATE@Sketch1`) and lights
(`$STATE@Directional1`).

### Parts and assemblies

```python
sw.description()            -> '$DESCRIPTION'
sw.parent()                 -> '$PARENT'
sw.part_number()            -> '$PARTNUMBER'
sw.comment()                -> '$COMMENT'
sw.color()                  -> '$COLOR'
sw.user_notes()             -> '$USER_NOTES'
```

### Assemblies

```python
sw.component_config("Arm", 1)    -> '$CONFIGURATION@Arm<1>'
sw.component_state("Screw", 2)   -> '$STATE@Screw<2>'
sw.component_fixed("Screw")      -> '$FIXED@Screw'
sw.display_state()               -> '$DISPLAYSTATE'
sw.never_expand_in_bom()         -> '$NEVER_EXPAND_IN_BOM'
```

`$CONFIGURATION@X` means two different things and the instance number is what
tells them apart: with one it is a component of an assembly, without one it is
the base part of a part document. Parsing follows the same rule.

```python
sw.parse_header("$CONFIGURATION@washer").spec.name     -> 'base_part_config'
sw.parse_header("$CONFIGURATION@washer<1>").spec.name  -> 'component_config'
```

### Not confirmed, and obsolete

Three parameters ship but are not backed by SOLIDWORKS documentation, and one
is documented as obsolete. Using any of them emits a warning.

```python
sw.suppress_new_features()                -> '$SUPPRESS NEW FEATURES'    unverified
sw.suppress_new_components()              -> '$SUPPRESS NEW COMPONENTS'  unverified
sw.component_display_state("Screw", 2)    -> '$DISPLAYSTATE@Screw<2>'    unverified
sw.component_visibility("Screw", 2)       -> '$SHOW@Screw<2>'            obsolete
```

`$SHOW` is obsolete in the SOLIDWORKS help itself; component visibility belongs
to display states now. It stays in the catalogue only so an old table still
round-trips through `parse_header`.

### Escape hatches

```python
sw.raw("$WHATEVER@Thing<3>")  -> '$WHATEVER@Thing<3>'   unverified, unchecked
sw.column("dimension", dimension="Length", feature="Boss-Extrude1")
```

Errors are raised at the call site, not later:

```python
sw.component_config("Screw<2>", 2)
  ValueError: Component 'Screw<2>' already carries an instance number;
  pass either the suffix or the instance argument, not both.

sw.column("dimension", name="Length")
  TypeError: Parameter 'dimension' needs: dimension, feature
```

---

## 3. Values

### Feature suppression: letters or numbers

Both are documented by SOLIDWORKS, and neither is silently rewritten into the
other.

```python
sw.DesignTable("M", [holes])                                     # default
row 3   ['A', 'S']        row 4   ['B', 'U']

sw.DesignTable("M", [holes], state_format=sw.StateFormat.NUMERIC)
row 3   ['A', 1]          row 4   ['B', 0]
```

### Components and flags

A component is Resolved, not Unsuppressed: different letters, different enum,
and mixing them up is caught by validation.

```python
t.add_configuration("A", {vis: sw.YesNo.YES, cs: sw.ComponentState.RESOLVED})
t.add_configuration("B", {vis: sw.YesNo.NO,  cs: sw.ComponentState.SUPPRESSED})

row 2   [None, '$SHOW@Screw<2>', '$STATE@Screw<2>']
row 3   ['A', 'Y', 'R']
row 4   ['B', 'N', 'S']
```

Helpers:

```python
sw.State.from_bool(True)       -> State.SUPPRESSED
sw.State.from_legacy_int(1)    -> State.SUPPRESSED
sw.YesNo.from_bool(False)      -> YesNo.NO
```

### Yes/no columns take a bool

`$FIXED@`, `$NEVER_EXPAND_IN_BOM`, `$ENABLE@` and the other yes/no columns
accept `True` and `False`, and the package writes `Y` and `N`. `sw.YES` and
`sw.NO` are there for when you would rather be explicit, and `YesNo.YES` still
works.

```python
table.add_configuration("A", {eq: True,  bom: sw.YES})
table.add_configuration("B", {eq: False, bom: sw.NO})

row 2  [None, '$ENABLE@2@Equations', '$NEVER_EXPAND_IN_BOM']
row 3  ['A', 'Y', 'Y']
row 4  ['B', 'N', 'N']
```

Writing the bool straight into the cell would put `TRUE` there, which
SOLIDWORKS does not read, so the conversion happens on the way out and only in
a yes/no column. Elsewhere a bool is left alone.

Suppression columns are deliberately left out of this. `True` could be read as
'this feature is on' just as easily as 'suppressed', so `$STATE@` still wants a
`State`, `1`/`0`, or `State.from_bool(...)` where you say which you mean.

### Equations

An equation value is written as literal text, never as an Excel formula: a
formula cell carries no cached result and SOLIDWORKS reads an empty parameter.

```python
t.add_configuration("A", {gv: sw.Expression("W/2")})
t.add_configuration("B", {gv: 30})

row 3   [('A', 's'), ('=W/2', 's')]     # 's' = text cell
row 4   [('B', 's'), (30,    'n')]      # 'n' = number

sw.Expression("=W/2").render()  -> '=W/2'      # one leading '=' either way
```

One caveat the package now warns about: SOLIDWORKS accepts only constant
decimal values for a **global variable** in a design table. To drive a global
variable by equation, leave the column out and write the equation in
**Tools → Equations**.

### Numbers, rounding and text that looks numeric

```python
sw.DesignTable("M", [length, sw.prop("PN")], round_floats=2)
t.add_configuration("A", {length: 25.126789, sw.prop("PN"): "0012"})

row 3   [('A','str'), (25.13,'float'), ('0012','str')]
```

A part number of `0012` stays `0012`.

### Missing values

```python
missing=sw.MissingValue.BLANK                   row 3  ['A', 10, None]
missing=sw.MissingValue.FILL, fill_value="-"    row 3  ['A', 10, '-']
missing=sw.MissingValue.ERROR                   validation reports missing-value
```

### A sheet that uses the less common parameters

```python
mat  = sw.material("BRK-MASTER")
hole = sw.hole_size("CBORE1")
tol  = sw.tolerance("D1", "Boss-Extrude1")
mass = sw.mass()
cog  = sw.center_of_mass()

table = sw.DesignTable("BRK-MASTER", [mat, hole, tol, mass, cog])
table.add_configuration("BRK-A", {
    mat: "SOLIDWORKS Materials:Plain Carbon Steel",
    hole: "M8", tol: "SYMMETRIC;0.5", mass: 2.45, cog: "0, 12.5, 0",
})
table.add_configuration("BRK-B", {
    mat: "SOLIDWORKS Materials:6061 Alloy",
    hole: "M10", tol: "LIMIT;0.2;0.1", mass: 1.10, cog: "0, 10.0, 0",
})
```

```
row 2  [None, '$LIBRARY:MATERIAL@BRK-MASTER', '$HW-SIZE@CBORE1',
        '$TOLERANCE@D1@Boss-Extrude1', '$SW-MASS', '$SW-COG']
row 3  ['BRK-A', 'SOLIDWORKS Materials:Plain Carbon Steel', 'M8',
        'SYMMETRIC;0.5', 2.45, '0, 12.5, 0']
row 4  ['BRK-B', 'SOLIDWORKS Materials:6061 Alloy', 'M10',
        'LIMIT;0.2;0.1', 1.1, '0, 10.0, 0']
```

Tolerance values are keywords: `NONE`, `BASIC`, `MIN`, `MAX`,
`SYMMETRIC;max`, `BILATERAL;max;min`, `LIMIT;max;min`, and the `FIT` forms.

And the weldment and pattern side:

```python
eq   = sw.equation_enable(1)
rel  = sw.sketch_relation_state("Fixed1", "Sketch2")
skip = sw.skip_instances("LPattern1")
prof = sw.profile_size("Member1")
```

```
row 2  [None, '$ENABLE@1@Equations', '$STATE@Fixed1@Sketch2',
        '$SKIP@LPattern1', '$PROFILE_SIZE@Member1']
row 3  ['F-01', 'Y', 'S', '10,1;10,2;', '40 x 40 x 4']
row 4  ['F-02', 'N', 'U', None, '50 x 50 x 5']
```

---

## 4. Building a table

```python
DesignTable(
    model_name,              # goes in A1 after 'Design Table for: '
    columns=(),              # Column objects or header strings
    *,
    output_path=None,        # default target for save()
    sheet_name="Sheet1",
    vocabulary=sw.ENGLISH,
    state_format=StateFormat.LETTERS,
    missing=MissingValue.BLANK,
    fill_value=None,
    round_floats=None,
    autosize_columns=False,
    strict=True,
    ignore=(),
)
```

Columns:

```python
table.add_column(column)      # returns the Column, for use as a value key
table.add_columns(columns)    # returns a tuple
table.columns                 # tuple, left to right
table.headers()               # ('Length@Boss-Extrude1', '$PRP@Material', ...)
table.column_for('$prp@material')  -> $PRP@Material     # case insensitive
```

Configurations:

```python
table.add_configuration(name, values=None, *, description=None, parent=None)
table.configurations          # tuple of Configuration(name, values)
```

`description` and `parent` add their own column on first use, because those two
are the ones people forget to declare.

Values are addressed by column identity, never by column number. There is no
positional form, and supplying a value for a column that was never declared is
always an error:

```python
table.add_configuration("A", {"$PRP@Missing": "x"})
  UnknownColumnError: No column with header '$PRP@Missing'. Add it before
  supplying values for it.
```

That is the whole point: a header-to-index map mixed with literal column
numbers is how a generator silently starts writing the wrong values after
someone inserts a column in the middle.

---

## 5. Derived configurations

SOLIDWORKS cannot create a child before its parent, so the row order matters.

```python
t.add_configuration("CHILD",  {L: 20}, parent="PARENT")
t.add_configuration("PARENT", {L: 10})

before:  ['CHILD', 'PARENT']    validate -> ['parent-after-child']
t.sort_by_parent()
after:   ['PARENT', 'CHILD']    validate -> []
```

`sort_by_parent()` is never automatic. Row order is configuration order in the
SOLIDWORKS tree, and changing it silently is not this library's call.

---

## 6. Extra sheets and defined names

```python
table.add_sheet("Notes", [["Source"], ["main_db.xlsx"]], hidden=True)
table.add_defined_name("Lengths", "Sheet1!$B$3:$B$50")
```

```
sheets:        ['Sheet1', 'Notes']
Notes state:   'hidden'          # never 'veryHidden'
defined names: {'Family': 'Sheet1!$A$2', 'Lengths': 'Sheet1!$B$3:$B$50'}
```

`Sheet1` always stays first and visible. Hidden means `hidden`, so you can
unhide it in Excel when something misbehaves.

Three names are refused:

```python
table.add_sheet("_SWX", [[1]])           -> ReservedNameError
table.add_defined_name("Family", "...")  -> ReservedNameError
table.add_defined_name("_SWX_0", "...")  -> ReservedNameError
```

SOLIDWORKS creates `_SWX` and `_SWX_0` itself when it embeds the table.
Authoring them produces a table it cannot reconcile.

---

## 7. Validation

```python
report = table.validate()
for issue in report.issues:
    print(issue)
```

`report.issues` is a tuple of `Issue`, each with `severity`, `code`, `message`
and `location`. `report.errors` and `report.warnings` filter it, `bool(report)`
is True when there are no errors, and `report.raise_for_errors()` raises.

Issue codes are stable across releases. Message wording is not, so match on the
code.

```
error:   invalid-configuration-name [configuration 'A/B']:
         Configuration name 'A/B' contains '/', which SOLIDWORKS does not allow.

error:   no-configurations [A3]:
         A design table needs at least one configuration row.

warning: text-in-numeric-column [configuration 'A', column 'Length@Boss-Extrude1']:
         Expected a number or an Expression, got 'S'.

warning: equations-dimension-conflict [width@Sk1]:
         Both a dimension and a global variable named 'width' are driven.
         If an equation governs the dimension, the dimension column does nothing.

warning: suspicious-feature-name [$STATE@ Draft2 ]:
         Feature ' Draft2 ' has leading or trailing whitespace, which will not
         match anything in the model.

warning: obsolete-parameter [$SHOW@Screw<2>]:
         Parameter 'component_visibility' is obsolete: the SOLIDWORKS help says
         so, and recent versions no longer list it.

warning: unverified-parameter [$SUPPRESS NEW FEATURES]:
         Parameter 'suppress_new_features' is unverified: its syntax is not
         pinned down by SOLIDWORKS documentation, so the column may be ignored
         on rebuild.

warning: expression-in-global-variable [configuration 'A', column '$VALUE@width@Equations']:
         SOLIDWORKS accepts only constant decimal values for a global variable
         in a design table. To drive it by equation, drop this column and write
         the equation in Tools > Equations.
```

Also caught: duplicate columns and configurations, values for undeclared
columns, `$PARENT` cycles, the reserved `_SWX` sheet name, a state letter in a
numeric column, and a float carrying more decimals than the model will show.

### What validation cannot do

Without a live model there is nothing to check names against. A misspelled
feature name still produces a column SOLIDWORKS silently ignores. This package
catches problems of *shape* — stray whitespace, an embedded `@`, a value of the
wrong kind, a parameter whose syntax is not documented. Claiming more is how
people learn to stop reading warnings.

---

## 8. Strictness

```python
sw.DesignTable(...)                              # errors raise, warnings warn
sw.DesignTable(..., strict=False)                # everything becomes a warning
sw.DesignTable(..., ignore=("float-precision",)) # silence one code
```

```python
sw.DesignTable("M", [L])           # with a bad configuration name
  ValidationError: Design table has 1 error(s):
    - error: invalid-configuration-name ...

sw.DesignTable("M", [L], ignore=("invalid-configuration-name",))
  validate().issues -> ()
```

Some problems are reported when you call the method, not at validation time:

```python
sw.DesignTable("M", [L, sw.dimension("Length", "Boss-Extrude1")])
  DuplicateColumnError: Header 'Length@Boss-Extrude1' is already in this table.
```

In CI, promote warnings so they cannot rot:

```bash
python -W error::swdesigntables.errors.DesignTableWarning build_tables.py
```

### Cleaning a name

Validation warns about a bad configuration name but never rewrites it: a part
number is the caller's to decide. Rewriting is opt-in.

```python
sw.sanitize_configuration_name('BRK/025:A*')              -> 'BRK-025-A-'
sw.sanitize_configuration_name('BRK 025', replacement="_") -> 'BRK 025'
```

---

## 9. Templates and skeletons

`TableTemplate` holds everything that does not change row to row, so every
script in a project starts from the same base. It is frozen; `replace()` gives
a variant without disturbing the original.

```python
BRACKET = sw.TableTemplate(
    model_name="BRK-MASTER",
    output_dir=Path("tables"),
    file_name="brk_master_dt.xlsx",
    columns=(length, width, sw.description()),
    config_name=lambda width, length: f"BRK-{width:03d}-{length:03d}",
    round_floats=3,
)

BRACKET.output_path                     -> tables/brk_master_dt.xlsx
BRACKET.name_for(width=25, length=40)   -> 'BRK-025-040'
BRACKET.new_table()                     -> an empty DesignTable with those settings
BRACKET.replace(model_name="BRK-HEAVY") -> a copy; the original is untouched
```

`new_table(**overrides)` takes the same keyword arguments as `DesignTable`.
`save()` with no argument writes to `output_path` and creates the directory.

An empty but valid file:

```python
sw.blank_table("BRK-MASTER", [length, width], path="skeleton.xlsx",
               configurations=("A", "B"))
```

```
A1     'Design Table for: BRK-MASTER'
row 2  [None, 'Length@Boss-Extrude1', 'Width@Boss-Extrude1']
row 3  ['A', None, None]
row 4  ['B', None, None]
```

---

## 10. The catalogue

Every parameter carries a verification status, readable at runtime.

```python
len(sw.list_parameters())   -> 29

for spec in sw.list_parameters():
    print(spec.name, spec.template, spec.status.value)
```

```
color                    {color}                              verified
comment                  {comment}                            verified
description              {description}                        verified
display_state            {display_state}                      verified
never_expand_in_bom      {never_expand_in_bom}                verified
parent                   {parent}                             verified
part_number              {part_number}                        verified
suppress_new_components  {suppress_new_components}            unverified
suppress_new_features    {suppress_new_features}              unverified
user_notes               {user_notes}                         verified
equation_enable          {enable}@{relation_id}@{equations}   verified
global_variable          {value}@{variable}@{equations}       verified
tolerance                {tolerance}@{dimension}@{feature}    verified
body_material            {library_material}@{body}@{part}     verified
hole_size                {hole_size}@{feature}                verified
material                 {library_material}@{part}            verified
profile_size             {profile_size}@{target}              verified
sketch_relation_state    {state}@{relation}@{sketch}          verified
component_display_state  {display_state}@{component}          unverified
component_fixed          {fixed}@{component}                  verified
component_state          {state}@{component}                  verified
component_visibility     {show}@{component}                   obsolete
skip_instances           {skip}@{pattern}                     verified
component_config         {configuration}@{component}          verified
base_part_config         {configuration}@{part}               verified
prop                     {property}@{name}                    verified
state                    {state}@{feature}                    verified
sw_property              {sw_property}{name}                  verified
dimension                {dimension}@{feature}                verified
```

The order is the order `parse_header` tries them: more specific first.

| Status | Meaning |
|---|---|
| `VERIFIED` | The SOLIDWORKS help documents this exact spelling on a page of its own |
| `DOCUMENTED` | Mentioned by some source, without a page that pins the syntax |
| `UNVERIFIED` | Registered at runtime by you, or otherwise unconfirmed |
| `OBSOLETE` | The SOLIDWORKS help says the parameter is obsolete |

### Adding one at runtime

Nothing is out of reach. Sheet metal (`$SM-…`) is the standing example: no
SOLIDWORKS source consulted confirms its syntax, and shipping an invented
factory is worse than shipping none.

```python
sw.register_parameter(
    "sheet_metal_thickness",
    template="$SM-THICKNESS",
    summary="Sheet metal thickness.",
    value_kind=sw.ValueKind.NUMBER,
)

sw.column("sheet_metal_thickness").header()      -> '$SM-THICKNESS'
sw.column("sheet_metal_thickness").status        -> Status.UNVERIFIED
sw.get_parameter("sheet_metal_thickness").template -> '$SM-THICKNESS'
```

Registering the same name twice raises `ValueError`, and the registry is global
to the process.

Full signature:

```python
sw.register_parameter(
    name, template, *,
    summary="",
    fields=(),             # template fields the caller fills
    vocab_fields=(),       # template field -> Vocabulary attribute
    field_patterns=(),     # template field -> regex, for parse_header
    value_kind=ValueKind.ANY,
    status=Status.UNVERIFIED,
    priority=50,           # lower is tried first by parse_header
)
```

---

## 11. Migrating existing headers

`parse_header` turns a header string into the typed column that renders it, so
a list you already have keeps working.

```python
HEADERS = ["Length@Boss-Extrude1", "$STATE@Draft2", "$ODD"]
table = sw.DesignTable("Extrusion", [sw.parse_header(h) for h in HEADERS],
                       state_format=sw.StateFormat.NUMERIC)
table.headers() -> ('Length@Boss-Extrude1', '$STATE@Draft2', '$ODD')
```

What it recognizes:

```
'Length@Boss-Extrude1'      -> dimension
'$PRP@Material'             -> prop
'$STATE@Draft2'             -> state                  (a feature)
'$STATE@Screw<2>'           -> component_state        (a component: the <2>)
'$STATE@Fixed1@Sketch2'     -> sketch_relation_state
'$VALUE@width@Equations'    -> global_variable
'$CONFIGURATION@washer'     -> base_part_config
'$CONFIGURATION@washer<1>'  -> component_config
'$DESCRIPTION'              -> description
'$ANYTHING_ELSE'            -> raw                    (never an error)
```

---

## 12. Output

```python
table.validate()      -> ValidationReport, writes nothing
table.to_workbook()   -> an openpyxl Workbook, after validating
table.to_bytes()      -> bytes
table.save("x.xlsx")  -> WindowsPath('x.xlsx')   # creates missing directories
table.save(stream)    -> None
table.save()          -> uses output_path, or ValueError if there is none
```

Output is deterministic: document timestamps are fixed, so two identical runs
produce identical bytes and git shows a change only when the table really
changed.

```python
sha256(build()) == sha256(build())   -> True
```

The sheet name is yours, and `Family` follows it:

```python
sw.DesignTable("M", [L], sheet_name="Table", autosize_columns=True)

sheets: ['Table']    Family -> 'Table!$A$2'    column A width: 12.0
```

---

## 13. Other languages

SOLIDWORKS translates header keywords: `$DESCRIPTION` is `$BESCHREIBUNG` in
German and `$DESCRIZIONE` in Italian. Every literal lives in one frozen
`Vocabulary`, so another language is a new instance rather than a rewrite.

```python
GERMAN = sw.Vocabulary(description="$BESCHREIBUNG")   # confirm each one first
table = sw.DesignTable("M", [sw.description()], vocabulary=GERMAN)
table.headers()   -> ('$BESCHREIBUNG',)
```

Only `sw.ENGLISH` ships verified. A column's `key` does not depend on the
vocabulary, so the same script can write the same table in two languages.

---

## 14. What the package does not do

- **It does not talk to SOLIDWORKS.** No COM, no automation, no running
  instance needed. It writes a file; you insert it.
- **It does not read existing tables.** Write only.
- **It cannot check names against a model.** See
  [what validation cannot do](#what-validation-cannot-do).
- **It is not the source of truth.** When a table is generated by a script it
  is an internal detail of the generator. The source of truth is what lives
  outside it: a database, a spreadsheet, a configuration file. If the embedded
  table becomes the source, nothing can read the data without opening
  SOLIDWORKS.

```
external source -> rules -> design table -> configurations
```

### One thing the SOLIDWORKS documentation contradicts itself about

Two help pages disagree about cell A1. *Formatting Manually Created Design
Tables* says A1 must be blank. *Formatting Automatically Created Design Tables*
says A2 is the `Family` cell, that it determines where the data begins, and
that rows above it and columns to its left are valid as long as configuration
names and parameters stay below and to the right.

This package writes `Design Table for: <model>` in A1, which is what SOLIDWORKS
itself writes when it creates a table. That satisfies the second page and not
the first. If a model ever refuses a generated table, A1 is the first thing to
empty — and `sw.DesignTable(...)` will tell you nothing about it, because there
is nothing here to detect.
