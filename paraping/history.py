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
History management for ParaPing.

This module provides functions for creating snapshots, managing history buffers,
and navigating through time to review past ping results.
"""

import copy
from collections import deque

# Constants for history feature
HISTORY_DURATION_MINUTES = 30  # Store up to 30 minutes of history
SNAPSHOT_INTERVAL_SECONDS = 1.0  # Take snapshot every second


def create_state_snapshot(buffers, stats, timestamp):
    """
    Create a deep copy snapshot of current buffers and stats.

    Args:
        buffers: Current buffer state
        stats: Current statistics
        timestamp: Timestamp for this snapshot

    Returns:
        Dict with snapshot data
    """
    # Deep copy buffers (deques and their contents)
    buffers_copy = {}
    for host_id, host_buffers in buffers.items():
        buffers_copy[host_id] = {
            "timeline": deque(host_buffers["timeline"], maxlen=host_buffers["timeline"].maxlen),
            "rtt_history": deque(host_buffers["rtt_history"], maxlen=host_buffers["rtt_history"].maxlen),
            "time_history": deque(host_buffers["time_history"], maxlen=host_buffers["time_history"].maxlen),
            "ttl_history": deque(host_buffers["ttl_history"], maxlen=host_buffers["ttl_history"].maxlen),
            "categories": {
                status: deque(cat_deque, maxlen=cat_deque.maxlen) for status, cat_deque in host_buffers["categories"].items()
            },
        }

    # Deep copy stats
    stats_copy = copy.deepcopy(stats)

    return {
        "timestamp": timestamp,
        "buffers": buffers_copy,
        "stats": stats_copy,
    }


def update_history_buffer(
    history_buffer,
    buffers,
    stats,
    now,
    last_snapshot_time,
    history_offset,
):
    """
    Update history buffer with periodic snapshots.

    Args:
        history_buffer: Deque holding historical snapshots
        buffers: Current buffer state
        stats: Current statistics
        now: Current timestamp
        last_snapshot_time: Last time a snapshot was taken
        history_offset: Current history navigation offset

    Returns:
        Tuple of (last_snapshot_time, history_offset) - updated values
    """
    if (now - last_snapshot_time) < SNAPSHOT_INTERVAL_SECONDS:
        return last_snapshot_time, history_offset

    snapshot = create_state_snapshot(buffers, stats, now)
    history_buffer.append(snapshot)
    last_snapshot_time = now
    if history_offset > 0:
        history_offset = min(history_offset + 1, len(history_buffer) - 1)
    return last_snapshot_time, history_offset


def resolve_render_state(history_offset, history_buffer, buffers, stats, paused):
    """
    Resolve which buffers/stats to use for rendering based on history offset.

    Args:
        history_offset: Current history navigation offset (0 = live)
        history_buffer: Deque of historical snapshots
        buffers: Current live buffers
        stats: Current live statistics
        paused: Whether display is paused

    Returns:
        Tuple of (render_buffers, render_stats, render_paused)
    """
    if history_offset > 0 and history_offset <= len(history_buffer):
        snapshot = history_buffer[-(history_offset + 1)]
        return snapshot["buffers"], snapshot["stats"], True
    return buffers, stats, paused


def compute_history_page_step(
    host_infos,
    buffers,
    stats,
    symbols,
    panel_position,
    mode_label,
    sort_mode,
    filter_mode,
    slow_threshold,
    show_asn,
    asn_width=8,
    header_lines=2,
):
    """
    Compute the page step size for history navigation.

    This determines how many timeline columns to skip when navigating
    backward/forward in history with arrow keys.

    Args:
        host_infos: List of host information dictionaries
        buffers: Current buffer state
        stats: Current statistics
        symbols: Dictionary mapping status to symbol
        panel_position: Position of summary panel
        mode_label: Display mode label
        sort_mode: Current sort mode
        filter_mode: Current filter mode
        slow_threshold: Threshold for slow pings
        show_asn: Whether to show ASN information
        asn_width: Width for ASN display
        header_lines: Number of header lines

    Returns:
        Page step size (int)
    """
    # Import here to avoid circular dependency
    from ui_render import (
        build_display_entries,
        build_display_names,
        compute_main_layout,
        compute_panel_sizes,
        get_terminal_size,
        should_show_asn,
    )

    term_size = get_terminal_size(fallback=(80, 24))
    term_width = term_size.columns
    term_height = term_size.lines
    status_box_height = 3 if term_height >= 4 and term_width >= 2 else 1
    panel_height = max(1, term_height - status_box_height)

    include_asn = should_show_asn(host_infos, mode_label, show_asn, term_width, asn_width=asn_width)
    display_names = build_display_names(host_infos, mode_label, include_asn, asn_width)
    main_width, main_height, _, _, _ = compute_panel_sizes(term_width, panel_height, panel_position)
    display_entries = build_display_entries(
        host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        sort_mode,
        filter_mode,
        slow_threshold,
    )
    host_labels = [entry[1] for entry in display_entries]
    if not host_labels:
        host_labels = [info["alias"] for info in host_infos]
    _, _, timeline_width, _ = compute_main_layout(host_labels, main_width, main_height, header_lines)
    return max(1, timeline_width)


def get_cached_page_step(
    cached_page_step,
    last_term_size,
    host_infos,
    buffers,
    stats,
    symbols,
    panel_position,
    mode_label,
    sort_mode,
    filter_mode,
    slow_threshold,
    show_asn,
):
    """
    Get the page step for history navigation, using cached value if available.

    The page step is only recalculated if the terminal size has changed.
    This prevents expensive recalculation on every arrow key press.

    Args:
        cached_page_step: Previously cached page step value
        last_term_size: Terminal size from last calculation
        host_infos: List of host information dictionaries
        buffers: Current buffer state
        stats: Current statistics
        symbols: Dictionary mapping status to symbol
        panel_position: Position of summary panel
        mode_label: Display mode label
        sort_mode: Current sort mode
        filter_mode: Current filter mode
        slow_threshold: Threshold for slow pings
        show_asn: Whether to show ASN information

    Returns:
        tuple: (page_step, new_cached_page_step, new_last_term_size)
    """
    from main import get_terminal_size

    def should_recalculate_page_step(cached_value, last_size, current_size):
        """Check if page step needs recalculation due to cache miss or terminal resize"""
        if cached_value is None or last_size is None:
            return True  # First time - need to calculate
        if current_size.columns != last_size.columns:
            return True  # Terminal width changed
        if current_size.lines != last_size.lines:
            return True  # Terminal height changed
        return False

    current_term_size = get_terminal_size(fallback=(80, 24))

    # Check if we need to recalculate
    if should_recalculate_page_step(cached_page_step, last_term_size, current_term_size):
        # Terminal size changed or first time - recalculate
        page_step = compute_history_page_step(
            host_infos,
            buffers,
            stats,
            symbols,
            panel_position,
            mode_label,
            sort_mode,
            filter_mode,
            slow_threshold,
            show_asn,
        )
        return page_step, page_step, current_term_size

    # Use cached value
    return cached_page_step, cached_page_step, last_term_size
