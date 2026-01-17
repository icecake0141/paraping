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
import os
import queue
import select
import socket
import sys
import termios
import threading
import tty
from concurrent.futures import ThreadPoolExecutor

# Import and re-export from the refactored modules
from paraping.cli import handle_options, main
from paraping.core import (
    read_input_file,
    parse_host_file_line,
    compute_history_page_step,
    get_cached_page_step,
    build_host_infos,
    create_state_snapshot,
    update_history_buffer,
    resolve_render_state,
    MAX_HOST_THREADS,
    HISTORY_DURATION_MINUTES,
    SNAPSHOT_INTERVAL_SECONDS,
)
from paraping.pinger import ping_host, worker_ping, resolve_rdns, rdns_worker

# Re-export symbols from other modules for backward compatibility
from ping_wrapper import ping_with_helper
from network_asn import resolve_asn, asn_worker, should_retry_asn
from input_keys import parse_escape_sequence, read_key
from stats import (
    compute_fail_streak,
    latest_ttl_value,
    latest_rtt_value,
    build_streak_label,
    build_summary_suffix,
    build_summary_all_suffix,
    compute_summary_data,
)
from ui_render import (
    strip_ansi,
    visible_len,
    truncate_visible,
    pad_visible,
    rjust_visible,
    colorize_text,
    status_from_symbol,
    latest_status_from_timeline,
    build_colored_timeline,
    build_colored_sparkline,
    build_activity_indicator,
    compute_activity_indicator_width,
    get_terminal_size,
    compute_main_layout,
    compute_panel_sizes,
    resolve_boxed_dimensions,
    compute_host_scroll_bounds,
    pad_lines,
    box_lines,
    resize_buffers,
    build_sparkline,
    build_ascii_graph,
    resample_values,
    can_render_full_summary,
    format_summary_line,
    format_status_line,
    build_status_line,
    build_display_entries,
    render_timeline_view,
    render_sparkline_view,
    render_main_view,
    render_summary_view,
    render_help_view,
    render_host_selection_view,
    render_fullscreen_rtt_graph,
    render_status_box,
    build_display_lines,
    render_display,
    format_timezone_label,
    format_timestamp,
    prepare_terminal_for_exit,
    flash_screen,
    ring_bell,
    should_flash_on_fail,
    toggle_panel_visibility,
    cycle_panel_position,
    should_show_asn,
    resolve_display_name,
    format_asn_label,
    format_display_name,
    build_display_names,
)

# Explicitly define what's exported for backward compatibility
__all__ = [
    # CLI functions
    "handle_options",
    "main",
    # Core functions
    "read_input_file",
    "parse_host_file_line",
    "compute_history_page_step",
    "get_cached_page_step",
    "build_host_infos",
    "create_state_snapshot",
    "update_history_buffer",
    "resolve_render_state",
    # Constants
    "MAX_HOST_THREADS",
    "HISTORY_DURATION_MINUTES",
    "SNAPSHOT_INTERVAL_SECONDS",
    # Pinger functions
    "ping_host",
    "worker_ping",
    "resolve_rdns",
    "rdns_worker",
    # Ping wrapper
    "ping_with_helper",
    # Network ASN
    "resolve_asn",
    "asn_worker",
    "should_retry_asn",
    # Input keys
    "parse_escape_sequence",
    "read_key",
    # Stats
    "compute_fail_streak",
    "latest_ttl_value",
    "latest_rtt_value",
    "build_streak_label",
    "build_summary_suffix",
    "build_summary_all_suffix",
    "compute_summary_data",
    # UI render
    "strip_ansi",
    "visible_len",
    "truncate_visible",
    "pad_visible",
    "rjust_visible",
    "colorize_text",
    "status_from_symbol",
    "latest_status_from_timeline",
    "build_colored_timeline",
    "build_colored_sparkline",
    "build_activity_indicator",
    "compute_activity_indicator_width",
    "get_terminal_size",
    "compute_main_layout",
    "compute_panel_sizes",
    "resolve_boxed_dimensions",
    "compute_host_scroll_bounds",
    "pad_lines",
    "box_lines",
    "resize_buffers",
    "build_sparkline",
    "build_ascii_graph",
    "resample_values",
    "can_render_full_summary",
    "format_summary_line",
    "format_status_line",
    "build_status_line",
    "build_display_entries",
    "render_timeline_view",
    "render_sparkline_view",
    "render_main_view",
    "render_summary_view",
    "render_help_view",
    "render_host_selection_view",
    "render_fullscreen_rtt_graph",
    "render_status_box",
    "build_display_lines",
    "render_display",
    "format_timezone_label",
    "format_timestamp",
    "prepare_terminal_for_exit",
    "flash_screen",
    "ring_bell",
    "should_flash_on_fail",
    "toggle_panel_visibility",
    "cycle_panel_position",
    "should_show_asn",
    "resolve_display_name",
    "format_asn_label",
    "format_display_name",
    "build_display_names",
]


if __name__ == "__main__":
    options = handle_options()
    main(options)
