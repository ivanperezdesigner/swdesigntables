# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.1] - 2026-09-11

### Added

- Python 3.14 in the test matrix and in the package classifiers. Nothing
  in the package changed; this records where it is known to run.

## [0.2.0] - 2026-09-11

Every parameter in the catalogue was checked against the SOLIDWORKS 2027 help,
page by page. Most of the uncertainty 0.1.0 shipped with is gone; what remains
is now named precisely.

### Added

- Ten parameters the SOLIDWORKS help documents and 0.1.0 did not ship:
  `base_part_config` (`$CONFIGURATION@part`), `material`
  (`$LIBRARY:MATERIAL@part`), `body_material`, `hole_size` (`$HW-SIZE@`),
  `profile_size` (`$PROFILE_SIZE@`), `equation_enable` (`$ENABLE@id@Equations`),
  `sketch_relation_state` (`$STATE@relation@sketch`), `skip_instances`
  (`$SKIP@`), plus `mass()` and `center_of_mass()` for `$SW-MASS` and
  `$SW-COG`.
- `Status.OBSOLETE` and the `obsolete-parameter` warning code, for a parameter
  the SOLIDWORKS help itself calls obsolete.
- `expression-in-global-variable` warning: SOLIDWORKS takes only constant
  decimal values for a global variable in a design table. An equation-driven
  global variable belongs in Tools > Equations, with no column for it.
- A full reference with a runnable example and the real output for every
  feature: `DOCUMENTATION.md`.

### Changed

- `$USER_NOTES` and `$NEVER_EXPAND_IN_BOM` are confirmed, underscores and all.
  The 0.1.0 note about sources disagreeing on punctuation is withdrawn.
- Promoted to `VERIFIED` after confirmation: `comment`, `color`, `part_number`,
  `user_notes`, `never_expand_in_bom`, `tolerance`, `component_state`,
  `component_fixed`, `sw_property`.
- `sw_property` is no longer a read-only column. `$SW-MASS` and `$SW-COG`
  override the calculated values, the same as the Override Mass Properties
  dialog box, so a value written there is no longer flagged.
- `component_fixed()` no longer suggests an instance number: the documented
  syntax is `$FIXED@component_name`.
- `component_config()` now requires an instance number to parse as a component.
  `$CONFIGURATION@X` without one is a base part, and `parse_header` follows that
  rule.
- The suppression documentation is corrected: SOLIDWORKS documents `S`/`U`
  **and** `1`/`0` for feature suppression. 0.1.0 claimed only `S`/`U` was
  documented.
- Warning messages no longer tell you to verify a parameter with Auto-create in
  SOLIDWORKS. The catalogue is the reference.
- `Vocabulary` documents that translated headers are a real SOLIDWORKS feature
  (`$DESCRIPTION`, `$BESCHREIBUNG`, `$DESCRIZIONE`).

### Deprecated

- `component_visibility()` writes `$SHOW@component<instance>`, which the
  SOLIDWORKS help states is obsolete; display states replaced it. It still
  builds, so an old table round-trips through `parse_header`, but it warns.

### Fixed

- `suppress_new_features` and `suppress_new_components` were marked
  `DOCUMENTED` without a source. They are `UNVERIFIED`.
- `component_display_state` (`$DISPLAYSTATE@component<instance>`) was marked
  `DOCUMENTED` without a source. The help documents `$DISPLAYSTATE` for the
  configuration only, so it is `UNVERIFIED`.

### Known limitations

- Sheet metal parameters (`$SM-…`) are still not shipped: no source consulted
  confirms their syntax. Use `raw()` or `register_parameter()`.
- Two SOLIDWORKS help pages contradict each other about cell A1. This package
  writes the title there, which is what SOLIDWORKS writes when it creates a
  table itself. See the end of `DOCUMENTATION.md`.
- Write only. No reading of existing tables, no COM integration, no CLI.

## [0.1.0] - 2026-09-11

First release.

### Added

- `DesignTable`: title cell, headers from B2, the `Family` defined name, and
  configuration rows addressed by column identity rather than column number.
- A parameter catalogue with typed factories for `dimension`, `global_variable`,
  `state`, `prop`, `description`, `parent`, `display_state`, `component_config`,
  `component_state`, `component_visibility`, `component_fixed`,
  `component_display_state`, `comment`, `color`, `part_number`, `user_notes`,
  `never_expand_in_bom`, `suppress_new_features`, `suppress_new_components`,
  `sw_property` and `tolerance`.
- A verification `Status` on every parameter, and an `unverified-parameter`
  warning for anything not confirmed against a real model.
- `register_parameter()` and `raw()` so no header is out of reach.
- `parse_header()`, which turns an existing header string into its typed column,
  for migrating scripts that already hold a list of header strings.
- `TableTemplate` and `blank_table()` for reusable bases and empty skeletons.
- Value types `State`, `ComponentState`, `YesNo` and `Expression`, with
  `StateFormat.NUMERIC` for tables that spell suppression `1`/`0`.
- Validation with stable issue codes, three levels of strictness, and per-code
  suppression.
- Extra sheets, optionally hidden, plus extra workbook defined names. `_SWX`,
  `Family` and `_SWX_0` are reserved.
- Deterministic output: fixed document timestamps, so a regenerated table only
  differs in git when it actually changed.

### Known limitations

- Roughly half the catalogue is marked `DOCUMENTED` rather than `VERIFIED`: the
  syntax comes from documentation but has not been watched working in
  SOLIDWORKS. See the README for the Auto-create recipe that confirms one.
- Sheet metal parameters (`$SM-…`) are not shipped, because no reliable source
  confirmed their syntax. Use `raw()` or `register_parameter()`.
- The spelling of `$USER_NOTES` and `$NEVER_EXPAND_IN_BOM` is uncertain; sources
  disagree on hyphens versus underscores. Both are single constants in
  `Vocabulary`.
- Write only. No reading of existing tables, no COM integration, no CLI.

[Unreleased]: https://github.com/ivanperezdesigner/swdesigntables/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/ivanperezdesigner/swdesigntables/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ivanperezdesigner/swdesigntables/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ivanperezdesigner/swdesigntables/releases/tag/v0.1.0
