<!--
Copyright 2026 icecake0141
SPDX-License-Identifier: Apache-2.0
-->

# CLI Option Policy

## Scope Separation

- `paraping/keymap.py` is the single source of truth for runtime key actions.
- CLI options define startup defaults only.
- Runtime state transitions happen through keymap actions, not direct CLI mutation.

## Source of Truth

- CLI parser and config schema are both derived from `paraping/cli_options.py`.
- New startup option fields must be added to `CLI_OPTION_SPECS`.
- Config field types are generated from the same spec (`build_config_field_types()`).

## Boolean Option Policy

- Boolean startup defaults use paired flags:
  - `--foo` / `--no-foo`
- Legacy one-way flags are supported only as deprecation aliases and should not
  be documented as primary interfaces.

## Compatibility

- Deprecated flags must:
  - continue to parse for one release cycle,
  - emit `DeprecationWarning`,
  - map to the replacement option at parse time.

Current deprecations:

- `--verbose` -> `--log-level DEBUG`
- `--verbose-ui-errors` -> `--ui-log-errors`
