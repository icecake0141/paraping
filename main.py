#!/usr/bin/env python3
# Copyright 2025 icecake0141
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

"""
ParaPing - Interactive terminal-based ICMP ping monitor.

This module provides an interactive, terminal-based ICMP monitor that pings multiple
hosts concurrently and visualizes results as a live timeline or sparkline. It includes
useful operator controls like sorting, filtering, pause modes, snapshots, and optional
ASN/rDNS display for fast network triage.

Features:
- Concurrent ICMP ping to multiple hosts using a capability-based helper binary
- Live timeline or sparkline visualization with success/slow/fail markers
- Real-time statistics and aggregate counts with TTL display
- Sort and filter results by failures, streaks, latency, or host name
- Toggle display name mode: IP, reverse DNS, or alias
- Optional ASN display (fetched from Team Cymru)
- Configurable timezone for timestamps and snapshot naming
- History navigation to review past ping results
- Pause modes and snapshot export functionality

This file serves as a compatibility shim for the refactored ParaPing package.
The main logic has been split into separate modules in the paraping/ package.
"""

# Standard library imports for test compatibility (tests patch these from main module)
# This module is a compatibility shim and intentionally uses lazy/local imports.
# pylint: disable=unused-import,import-outside-toplevel,no-name-in-module,undefined-all-variable
# isort: skip_file
import os
import queue
import select
import socket
import sys
import termios
import threading
import tty
from concurrent.futures import ThreadPoolExecutor

# pylint: enable=unused-import

# Import and re-export from the refactored modules

# pylint: enable=unused-import

_TEST_PATCH_REFS = (os, queue, select, socket, sys, termios, threading, tty, ThreadPoolExecutor)
# Keep references for tests that patch main.<module> symbols.

_LAZY_EXPORTS = {
    # Network ASN (kept for compatibility)
    "resolve_asn": ("paraping.network_asn", "resolve_asn"),
    "asn_worker": ("paraping.network_asn", "asn_worker"),
    "should_retry_asn": ("paraping.network_asn", "should_retry_asn"),
    # Pinger
    "ping_host": ("paraping.pinger", "ping_host"),
    # Stats
    "latest_ttl_value": ("paraping.stats", "latest_ttl_value"),
    "compute_summary_data": ("paraping.stats", "compute_summary_data"),
    # UI
    "build_colored_timeline": ("paraping.ui_render", "build_colored_timeline"),
    "build_colored_sparkline": ("paraping.ui_render", "build_colored_sparkline"),
    "build_activity_indicator": ("paraping.ui_render", "build_activity_indicator"),
    "get_terminal_size": ("paraping.ui_render", "get_terminal_size"),
    "build_status_metrics": ("paraping.ui_render", "build_status_metrics"),
    "compute_main_layout": ("paraping.ui_render", "compute_main_layout"),
    "compute_panel_sizes": ("paraping.ui_render", "compute_panel_sizes"),
    "box_lines": ("paraping.ui_render", "box_lines"),
    "build_sparkline": ("paraping.ui_render", "build_sparkline"),
    "build_ascii_graph": ("paraping.ui_render", "build_ascii_graph"),
    "build_status_line": ("paraping.ui_render", "build_status_line"),
    "build_display_entries": ("paraping.ui_render", "build_display_entries"),
    "render_square_view": ("paraping.ui_render", "render_square_view"),
    "render_summary_view": ("paraping.ui_render", "render_summary_view"),
    "render_help_view": ("paraping.ui_render", "render_help_view"),
    "render_host_selection_view": ("paraping.ui_render", "render_host_selection_view"),
    "render_fullscreen_rtt_graph": ("paraping.ui_render", "render_fullscreen_rtt_graph"),
    "render_status_box": ("paraping.ui_render", "render_status_box"),
    "build_display_lines": ("paraping.ui_render", "build_display_lines"),
    "render_display": ("paraping.ui_render", "render_display"),
    "format_timezone_label": ("paraping.ui_render", "format_timezone_label"),
    "format_timestamp": ("paraping.ui_render", "format_timestamp"),
    "flash_screen": ("paraping.ui_render", "flash_screen"),
    "ring_bell": ("paraping.ui_render", "ring_bell"),
    "should_flash_on_fail": ("paraping.ui_render", "should_flash_on_fail"),
    "toggle_panel_visibility": ("paraping.ui_render", "toggle_panel_visibility"),
    "cycle_panel_position": ("paraping.ui_render", "cycle_panel_position"),
    "format_display_name": ("paraping.ui_render", "format_display_name"),
    "build_display_names": ("paraping.ui_render", "build_display_names"),
}


def __getattr__(name):
    """Lazily resolve backward-compatible exports."""
    if name in _LAZY_EXPORTS:
        module_name, attr_name = _LAZY_EXPORTS[name]
        module = __import__(module_name, fromlist=[attr_name])
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    """Include lazy exports in module introspection."""
    return sorted(set(globals().keys()) | set(_LAZY_EXPORTS.keys()) | set(__all__))


def handle_options():
    """Compatibility wrapper that lazily imports CLI option parsing."""
    from paraping.cli import handle_options as _handle_options

    return _handle_options()


def run(args):
    """Compatibility wrapper that lazily imports CLI runtime."""
    from paraping.cli import run as _run

    return _run(args)


def cli_main():
    """Compatibility wrapper that lazily imports CLI main entrypoint."""
    from paraping.cli import main as _cli_main

    return _cli_main()


def parse_escape_sequence(seq):
    """Compatibility wrapper for escape-sequence parsing."""
    from paraping.input_keys import parse_escape_sequence as _parse_escape_sequence

    return _parse_escape_sequence(seq)


def read_key():
    """Compatibility wrapper for key reading."""
    from paraping.input_keys import read_key as _read_key

    return _read_key()


# Explicitly define eagerly-bound exports for backward compatibility.
_EAGER_EXPORTS = [
    # CLI/core compatibility
    "handle_options",
    "main",
    "run",
    "cli_main",
    "read_input_file",
    "parse_host_file_line",
    "compute_history_page_step",
    "get_cached_page_step",
    "build_host_infos",
    "MAX_HOST_THREADS",
    "HISTORY_DURATION_MINUTES",
    "SNAPSHOT_INTERVAL_SECONDS",
    # Input
    "parse_escape_sequence",
    "read_key",
]

# Expose full compatibility surface, including lazy exports.
__all__ = _EAGER_EXPORTS + list(_LAZY_EXPORTS.keys())


# Backward compatibility: main(args) is now run(args), but keep main alias
main = run


if __name__ == "__main__":
    cli_main()
