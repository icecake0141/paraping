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

# Coding Agent Guide

This directory is the fastest starting point for coding agents working on ParaPing.
It is organized by purpose: first understand which subsystem owns a behavior, then
open the smallest set of files and tests needed for the change.

## Current Source of Truth

ParaPing is an interactive terminal ICMP monitor. The current runtime path is
runtime-based:

1. `paraping.cli` coordinates CLI parsing, runtime state, workers, hotkeys, and rendering.
2. Ping workers emit normalized events into `paraping.runtime.engine.MonitorState`.
3. History and render-source selection use `paraping.runtime.history` and `paraping.runtime.render_state`.
4. Existing UI functions consume a render-shaped projection from `paraping.runtime.render_projection`.

New package code should import from `paraping.*` or `paraping.runtime.*`.

## Fast Navigation

| Goal | Start here | Then check |
| --- | --- | --- |
| Add or change a CLI option | [change-routes.md](change-routes.md#add-or-change-a-cli-option) | `paraping/cli_options.py`, `paraping/cli.py`, `paraping/config.py` |
| Change ping scheduling or intervals | [change-routes.md](change-routes.md#change-ping-scheduling-or-intervals) | `paraping/runtime/scheduler.py`, `paraping/runtime/rate_limit.py`, `paraping/cli.py` |
| Change timeline, event, or history behavior | [change-routes.md](change-routes.md#change-timeline-event-or-history-behavior) | `paraping/runtime/engine.py`, `paraping/runtime/history.py`, `paraping/runtime/render_state.py` |
| Change terminal rendering or layout | [change-routes.md](change-routes.md#change-rendering-or-layout) | `paraping/ui_render.py`, `paraping/runtime/render_state.py`, `paraping/runtime/render_projection.py` |
| Change hotkeys or help text | [change-routes.md](change-routes.md#change-hotkeys) | `paraping/keymap.py`, `paraping/input_keys.py`, `paraping/ui_render.py` |
| Change host-file parsing or host metadata | [change-routes.md](change-routes.md#change-host-parsing) | `paraping/runtime/hosts.py`, `paraping/core.py` |
| Change ping execution or native helper behavior | [change-routes.md](change-routes.md#change-ping-execution-or-native-helper-behavior) | `paraping/pinger.py`, `paraping/ping_wrapper.py`, `src/native/ping_helper.c` |
| Update runtime exports | [change-routes.md](change-routes.md#update-public-runtime-exports) | `paraping/runtime/__init__.py`, `paraping/core.py`, export tests |
| Pick tests for a change | [testing-routes.md](testing-routes.md) | `docs/testing.md` |

## Documents in This Directory

- [Code Map](code-map.md): subsystem ownership and preferred files to inspect.
- [Change Routes](change-routes.md): practical routes from change intent to code and tests.
- [Testing Routes](testing-routes.md): targeted test commands and runtime guardrails.

## Canonical Project Docs

- [Documentation Index](../index.md)
- [Usage Guide](../usage.md)
- [Testing Guide](../testing.md)
- [Runtime Architecture](../runtime_architecture.md)
- [Ping Helper](../ping_helper.md)
- [Contributing](../CONTRIBUTING.md)
