<!--
Copyright 2026 icecake0141
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
-->

# Change Routes for Coding Agents

Each route lists the shortest practical path from change intent to code and
tests. Read the primary files first, then expand only if the behavior crosses a
boundary.

## Add or Change a CLI Option

Primary files:

- `paraping/cli_options.py`: flags, defaults, choices, boolean pairs, config key.
- `paraping/cli.py`: parser wiring, runtime state initialization, save-current-settings behavior.
- `paraping/config.py`: config load/save validation and default path behavior.
- `docs/usage.md`: user-facing CLI documentation.

Relevant tests:

- `pytest tests/unit/test_cli.py -v`
- `pytest tests/unit/test_config.py -v`
- `pytest tests/unit/test_main_options.py -v`
- `pytest tests/unit/test_docs_usage_sync.py -v`

Notes:

- Keep CLI/config/hotkey ownership aligned with `docs/cli_option_policy.md`.
- Boolean options should remain documented as explicit positive/negative pairs.

## Change Ping Scheduling or Intervals

Primary files:

- `paraping_v2/scheduler.py`: scheduling model and stagger behavior.
- `paraping_v2/rate_limit.py`: global ping-rate validation.
- `paraping/cli.py`: runtime interval hotkeys, scheduler integration, worker coordination.
- `paraping_v2/constants.py`: shared runtime limits and timing constants.

Relevant tests:

- `pytest tests/unit/test_scheduler.py -v`
- `pytest tests/unit/test_scheduler_integration.py -v`
- `pytest tests/unit/test_rate_limit.py -v`
- `pytest tests/unit/test_cli.py -v`

Notes:

- Preserve the global rate-limit contract unless the product behavior is being intentionally changed.
- Interval hotkeys and startup interval validation must stay consistent.

## Change Timeline, Event, or History Behavior

Primary files:

- `paraping_v2/domain.py`: event and host/stat data structures.
- `paraping_v2/engine.py`: event application, pending sequence replacement, timeline resizing.
- `paraping_v2/history.py`: snapshot creation and history buffer updates.
- `paraping_v2/render_state.py`: live vs historical render-state selection.
- `paraping_v2/legacy_adapter.py`: projection into the existing UI shape.

Relevant tests:

- `pytest tests/unit/test_v2_engine.py -v`
- `pytest tests/unit/test_v2_history.py -v`
- `pytest tests/unit/test_v2_render_state.py -v`
- `pytest tests/unit/test_timeline_sync.py -v`
- `pytest tests/unit/test_sequence_tracking_integration.py -v`

Notes:

- Do not reintroduce removed legacy history helpers on `main` or `paraping.core`.
- If the v2 shape changes, check the legacy adapter and UI tests because rendering still consumes projected data.

## Change Rendering or Layout

Primary files:

- `paraping/ui_render.py`: display entries, layout computation, panels, status box, graph rendering, ANSI output.
- `paraping_v2/render_state.py`: render-source selection.
- `paraping_v2/legacy_adapter.py`: data shape consumed by UI functions.
- `paraping_v2/term_size.py`: terminal-size normalization and timeline-width extraction.

Relevant tests:

- `pytest tests/unit/test_main_rendering.py -v`
- `pytest tests/unit/test_main_display.py -v`
- `pytest tests/unit/test_main_layout.py -v`
- `pytest tests/unit/test_v2_render_state.py -v`
- `pytest tests/unit/test_v2_term_size.py -v`

Notes:

- Keep rendering functions free of network side effects.
- Avoid line-number-sensitive assumptions in tests; assert rendered behavior and stable layout contracts.

## Change Hotkeys

Primary files:

- `paraping/keymap.py`: key-to-action mappings, action metadata, help grouping.
- `paraping/input_keys.py`: raw key and escape-sequence parsing.
- `paraping/cli.py`: action handling and runtime state updates.
- `paraping/ui_render.py`: help view rendering.
- `docs/usage.md`: interactive key documentation.

Relevant tests:

- `pytest tests/unit/test_keymap.py -v`
- `pytest tests/unit/test_input_keys.py -v`
- `pytest tests/unit/test_main_interaction.py -v`
- `pytest tests/unit/test_docs_usage_sync.py -v`

Notes:

- Add actions centrally in `keymap.py`; avoid scattering key literals through the CLI loop.
- Update help text and usage docs when a user-visible key changes.

## Change Host Parsing

Primary files:

- `paraping_v2/hosts.py`: current host-line parsing, host-info construction, duplicate handling, diagnostics.
- `paraping/core.py`: compatibility wrappers for legacy helper names.
- `paraping/cli.py`: input-file load/reload behavior and user-facing diagnostics.
- `hosts.txt.sample`: example host file if syntax changes.

Relevant tests:

- `pytest tests/unit/test_v2_hosts.py -v`
- `pytest tests/unit/test_core.py -v`
- `pytest tests/integration/test_multi_host_integration.py -v`

Notes:

- Prefer changing v2 host parsing first, then keep `paraping.core` wrappers delegating to it.
- If accepted input syntax changes, update usage docs and examples together.

## Change Ping Execution or Native Helper Behavior

Primary files:

- `paraping/pinger.py`: worker behavior, rDNS integration, scheduler-driven ping calls.
- `paraping/ping_wrapper.py`: native helper invocation, output parsing, error handling.
- `src/native/ping_helper.c`: privileged ICMP implementation.
- `src/native/README.md` and `docs/ping_helper.md`: native helper contract documentation.

Relevant tests:

- `pytest tests/unit/test_pinger.py -v`
- `pytest tests/unit/test_ping_wrapper.py -v`
- `pytest tests/contract/test_ping_helper_contract.py -v`
- `pytest tests/integration/test_multi_host_integration.py -v`

Notes:

- Keep the C helper contract and Python parser in sync.
- Security-sensitive native-helper changes should preserve validation, minimal privilege assumptions, and documented exit/error behavior.

## Update Public Compatibility Exports

Primary files:

- `main.py`: `_LAZY_EXPORTS`, eager wrappers, `__all__`, and compatibility aliases.
- `paraping/core.py`: selected legacy helper names that delegate to v2 modules.
- `paraping/__init__.py`: package-level exports, if the package surface changes.
- `docs/v2_migration_status.md`: compatibility policy if the public contract changes.

Relevant tests:

- `pytest tests/unit/test_main_public_api_surface.py -v`
- `pytest tests/unit/test_main_test_usage_surface.py -v`
- `pytest tests/unit/test_main_lazy_wrappers.py -v`
- `pytest tests/unit/test_public_api_surface.py -v`
- `pytest tests/unit/test_no_main_imports_in_package.py -v`
- `pytest tests/unit/test_removed_legacy_symbol_imports.py -v`

Notes:

- New implementation code should not depend on `main.py`.
- When adding a lazy export, keep `_LAZY_EXPORTS` and `__all__` consistent.
- Removed legacy history APIs are intentionally guarded; do not restore them unless the compatibility policy changes.
