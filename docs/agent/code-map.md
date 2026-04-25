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

# Code Map for Coding Agents

Use this map to find the owner of a behavior before editing. Prefer current
runtime modules over compatibility shims.

## Runtime Flow

```text
paraping.cli
  -> paraping.pinger / paraping.ping_wrapper
  -> paraping_v2.engine.MonitorState
  -> paraping_v2.history
  -> paraping_v2.render_state
  -> paraping_v2.legacy_adapter
  -> paraping.ui_render
```

`paraping.cli` is the orchestrator. It wires command-line options, config,
host loading, worker threads, v2 state, interactive key actions, terminal
redraws, snapshots, and shutdown cleanup.

## Subsystem Ownership

| Subsystem | Primary files | Notes |
| --- | --- | --- |
| CLI entrypoint and runtime loop | `paraping/cli.py`, `paraping/__main__.py` | `pyproject.toml` exposes `paraping = "paraping.cli:main"`. |
| CLI option definitions | `paraping/cli_options.py`, `paraping/cli.py` | Option specs centralize flags, defaults, choices, and config keys. |
| Runtime config persistence | `paraping/config.py`, `paraping/cli.py` | Runtime settings saved from CLI state use config keys from option specs. |
| v2 event/state engine | `paraping_v2/engine.py`, `paraping_v2/domain.py` | Owns timeline symbols, pending sequences, and aggregate counters. |
| History snapshots | `paraping_v2/history.py` | Current history implementation. Do not reintroduce removed legacy history APIs. |
| Render-state selection | `paraping_v2/render_state.py` | Chooses live vs historical v2 state for rendering. |
| Legacy render projection | `paraping_v2/legacy_adapter.py` | Converts v2 state into the shape expected by current UI functions. |
| Scheduler and rate limits | `paraping_v2/scheduler.py`, `paraping_v2/rate_limit.py` | Own ping timing and global rate validation. |
| Sequence tracking | `paraping_v2/sequence_tracker.py`, `paraping/sequence_tracker.py` | v2 is the current runtime source; legacy package surface remains tested. |
| Host parsing and host IDs | `paraping_v2/hosts.py`, `paraping/core.py` | `paraping.core` delegates compatibility helpers to v2 host parsing. |
| Terminal size and history paging | `paraping_v2/term_size.py`, `paraping_v2/paging.py`, `paraping/core.py` | Compatibility wrappers remain in `paraping.core`. |
| Terminal rendering and layout | `paraping/ui_render.py` | Owns display entries, layout sizing, panels, status lines, graphs, and ANSI output. |
| Statistics formatting | `paraping/stats.py`, `paraping/ui_render.py` | `stats.py` computes summary data; rendering formats it. |
| Hotkeys and input parsing | `paraping/keymap.py`, `paraping/input_keys.py`, `paraping/cli.py` | Key definitions are centralized in `keymap.py`; raw key reading is separate. |
| Ping worker behavior | `paraping/pinger.py` | Owns worker ping flow, rDNS worker behavior, and scheduler-driven ping calls. |
| Ping helper wrapper | `paraping/ping_wrapper.py` | Owns subprocess invocation and parsing for the native helper. |
| Native ICMP helper | `src/native/ping_helper.c`, `src/native/Makefile` | Linux privileged helper; see `docs/ping_helper.md`. |
| ASN lookup | `paraping/network_asn.py` | Team Cymru lookup, retry behavior, and ASN worker thread. |
| Compatibility shim | `main.py` | Backward-compatible lazy exports for tests and external callers. |

## Compatibility Boundaries

- `main.py` is not the implementation target for new behavior. It should only
  expose compatibility wrappers and lazy exports when a public compatibility
  contract intentionally changes.
- `main.__all__` is the compatibility contract for the shim. Keep
  `_LAZY_EXPORTS`, eager wrappers, and `__all__` consistent.
- `paraping.core` keeps selected legacy helper names and delegates current
  behavior to `paraping_v2`. New runtime logic should usually live in v2 modules
  or focused `paraping.*` modules, not in `paraping.core`.
- Package code must not import from `main.py`. Guardrail tests enforce this.

## Import Guidance

- New current-runtime state, history, scheduler, host parsing, paging, and
  terminal-size logic should import from `paraping_v2.*`.
- CLI orchestration, rendering, ping execution, config, key handling, and
  compatibility wrappers live under `paraping.*`.
- Tests may import compatibility surfaces when explicitly validating them, but
  new implementation code should use direct package modules.

## Historical Docs

Some older docs describe pre-v2 modularization and remain useful as background.
For current runtime ownership, prefer this directory and
[`../v2_migration_status.md`](../v2_migration_status.md).
