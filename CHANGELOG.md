# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/ivanperezdesigner/swdesigntables/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ivanperezdesigner/swdesigntables/releases/tag/v0.1.0
