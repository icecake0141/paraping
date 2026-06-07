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
runtime modules over removed shims.

## Runtime Flow

```text
paraping.cli
  -> paraping.pinger / paraping.ping_wrapper
  -> paraping.runtime.engine.MonitorState
  -> paraping.runtime.history
  -> paraping.runtime.render_state
  -> paraping.runtime.render_projection
  -> paraping.ui_render
```

`paraping.cli` is the orchestrator. It wires command-line options, config,
host loading, worker threads, runtime state, interactive key actions, terminal
redraws, snapshots, and shutdown cleanup.

## Subsystem Ownership

| Subsystem | Primary files | Notes |
| --- | --- | --- |
| CLI entrypoint and runtime loop | `paraping/cli.py`, `paraping/__main__.py` | `pyproject.toml` exposes `paraping = "paraping.cli:main"`. |
| CLI option definitions | `paraping/cli_options.py`, `paraping/cli.py` | Option specs centralize flags, defaults, choices, and config keys. |
| Runtime config persistence | `paraping/config.py`, `paraping/cli.py` | Runtime settings saved from CLI state use config keys from option specs. |
| runtime event/state engine | `paraping/runtime/engine.py`, `paraping/runtime/domain.py` | Owns timeline symbols, pending sequences, and aggregate counters. |
| History snapshots | `paraping/runtime/history.py` | Current history implementation. Do not reintroduce removed history APIs. |
| Render-state selection | `paraping/runtime/render_state.py` | Chooses live vs historical runtime state for rendering. |
| Render projection | `paraping/runtime/render_projection.py` | Converts runtime state into the shape expected by current UI functions. |
| Scheduler and rate limits | `paraping/runtime/scheduler.py`, `paraping/runtime/rate_limit.py` | Own ping timing and global rate validation. |
| Sequence tracking | `paraping/runtime/sequence_tracker.py` | Owns per-host ICMP sequence allocation and outstanding-ping limits. |
| Host parsing and host IDs | `paraping/runtime/hosts.py`, `paraping/core.py` | `paraping.core` keeps CLI-facing wrappers around runtime host parsing. |
| Terminal size and history paging | `paraping/runtime/term_size.py`, `paraping/runtime/paging.py`, `paraping/core.py` | Runtime wrappers remain in `paraping.core`. |
| Terminal rendering and layout | `paraping/ui_render.py` | Owns display entries, layout sizing, panels, status lines, graphs, and ANSI output. |
| Statistics formatting | `paraping/stats.py`, `paraping/ui_render.py` | `stats.py` computes summary data; rendering formats it. |
| Hotkeys and input parsing | `paraping/keymap.py`, `paraping/input_keys.py`, `paraping/cli.py` | Key definitions are centralized in `keymap.py`; raw key reading is separate. |
| Ping worker behavior | `paraping/pinger.py` | Owns worker ping flow, rDNS worker behavior, and scheduler-driven ping calls. |
| Ping helper wrapper | `paraping/ping_wrapper.py` | Owns subprocess invocation and parsing for the native helper. |
| Native ICMP helper | `src/native/ping_helper.c`, `src/native/Makefile` | Linux privileged helper; see `docs/ping_helper.md`. |
| ASN lookup | `paraping/network_asn.py` | Team Cymru lookup, retry behavior, and ASN worker thread. |

## Runtime Boundaries

- `paraping.core` keeps selected runtime helper names and delegates current
  behavior to `paraping.runtime`. New runtime logic should usually live in runtime modules
  or focused `paraping.*` modules, not in `paraping.core`.
- Package code must not import from removed top-level script shims.

## Import Guidance

- New current-runtime state, history, scheduler, host parsing, paging, and
  terminal-size logic should import from `paraping.runtime.*`.
- CLI orchestration, rendering, ping execution, config, and key handling live
  under `paraping.*`.

## Historical Docs

For a concise current overview, see
[`../runtime_architecture.md`](../runtime_architecture.md).
