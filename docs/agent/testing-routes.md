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

# Testing Routes for Coding Agents

Use targeted tests while iterating, then run the broader checks needed for the
change risk. The full testing guide remains in [`../testing.md`](../testing.md).

## Quick Commands

```bash
# Default suite
make test

# Full pytest suite
pytest tests/ -v

# Coverage run
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml
```

## Targeted Test Selection

| Change area | Start with |
| --- | --- |
| CLI options and startup behavior | `pytest tests/unit/test_cli.py tests/unit/test_main_options.py -v` |
| Runtime config | `pytest tests/unit/test_config.py -v` |
| Scheduler and intervals | `pytest tests/unit/test_scheduler.py tests/unit/test_scheduler_integration.py tests/unit/test_rate_limit.py -v` |
| runtime event engine | `pytest tests/unit/test_runtime_engine.py -v` |
| History and render-state resolution | `pytest tests/unit/test_runtime_history.py tests/unit/test_runtime_render_state.py tests/unit/test_timeline_sync.py -v` |
| Host parsing | `pytest tests/unit/test_runtime_hosts.py tests/unit/test_core.py -v` |
| Rendering and layout | `pytest tests/unit/test_main_rendering.py tests/unit/test_main_display.py tests/unit/test_main_layout.py -v` |
| Terminal sizing and paging | `pytest tests/unit/test_runtime_term_size.py tests/unit/test_runtime_paging.py tests/unit/test_core_term_size_normalization.py -v` |
| Hotkeys and key input | `pytest tests/unit/test_keymap.py tests/unit/test_input_keys.py tests/unit/test_main_interaction.py -v` |
| Ping worker and helper wrapper | `pytest tests/unit/test_pinger.py tests/unit/test_ping_wrapper.py -v` |
| Native ping helper contract | `pytest tests/contract/test_ping_helper_contract.py -v` |
| ASN lookup | `pytest tests/integration/test_network_asn.py -v` |
| Documentation sync | `pytest tests/unit/test_docs_usage_sync.py -v` |

## Runtime Guardrails

Run these when touching `paraping/core.py`, `paraping.runtime`, or public
exports:

```bash
pytest \
  tests/unit/test_public_api_surface.py \
  tests/unit/test_no_main_imports_in_package.py \
  -v
```

These tests protect the current runtime architecture:

- Runtime exports exist and stay importable.
- Package code does not import from removed top-level script shims.

## Pre-PR Checks

Use the same checks documented in [`../testing.md`](../testing.md) and
[`../CONTRIBUTING.md`](../CONTRIBUTING.md):

```bash
make lint
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
pylint . --fail-under=9.0
mypy
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml
```

For documentation-only changes, targeted documentation tests plus a Markdown
link sanity check are usually enough unless CI policy requires the full suite.
