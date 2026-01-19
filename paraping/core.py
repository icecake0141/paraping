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
# Review for correctness and security.

"""
Core functionality for ParaPing.

This module contains core functions for parsing input, building host information,
managing state snapshots, and history navigation.
"""

import copy
import ipaddress
import socket
import sys
from collections import deque
from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, Union

import paraping.ui_render
from paraping.ui_render import (
    build_display_entries,
    build_display_names,
    compute_main_layout,
    compute_panel_sizes,
    should_show_asn,
)

# Constants for time navigation feature
HISTORY_DURATION_MINUTES = 30  # Store up to 30 minutes of history
SNAPSHOT_INTERVAL_SECONDS = 1.0  # Take snapshot every second
MAX_HOST_THREADS = 128  # Hard cap to avoid unbounded thread growth.
TIMELINE_LABEL_ESTIMATE_WIDTH = 15  # Estimated label column + spacing width.


def _build_term_size(columns_value: Any, lines_value: Any) -> Optional[SimpleNamespace]:
    """Build a terminal size namespace from column and line values."""
    try:
        columns = int(columns_value)
        lines = int(lines_value)
    except (ValueError, TypeError):
        return None
    if columns <= 0 or lines <= 0:
        return None
    return SimpleNamespace(columns=columns, lines=lines)


def _normalize_term_size(term_size: Any) -> Optional[SimpleNamespace]:
    """
    Normalize terminal size to an object with .columns and .lines attributes.

    Handles tuple-like sequences, dicts, and objects with columns/lines attributes.

    Args:
        term_size: Terminal size as tuple-like sequence, dict, or object with attributes

    Returns:
        Object with .columns and .lines attributes, or None if invalid
    """
    if term_size is None:
        return None
    if hasattr(term_size, "columns") and hasattr(term_size, "lines"):
        return _build_term_size(term_size.columns, term_size.lines)
    if isinstance(term_size, dict):
        return _build_term_size(term_size.get("columns"), term_size.get("lines"))
    if isinstance(term_size, Sequence) and not isinstance(term_size, (str, bytes)):
        if len(term_size) >= 2:
            try:
                return _build_term_size(term_size[0], term_size[1])
            except TypeError:
                return None
    return None


def _extract_timeline_width_from_layout(layout: Any, main_width: int) -> int:
    """
    Defensively extract timeline width from compute_main_layout result.

    Supports tuple/list indexing and attribute-style extraction with fallbacks.

    Args:
        layout: Result from compute_main_layout (tuple, list, or object)
        main_width: Main panel width for fallback calculation

    Returns:
        int: Timeline width (always >= 1)
    """
    timeline_width = None

    # Method 1: Try tuple/list indexing (expected case)
    if isinstance(layout, (tuple, list)) and len(layout) > 2:
        try:
            timeline_width = layout[2]
        except (TypeError, IndexError):
            timeline_width = None

    # Method 2: Try attribute access (for named tuples or objects)
    if timeline_width is None:
        timeline_width = getattr(layout, "timeline_width", None)

    # Method 3: Fallback to a conservative default based on main_width
    if timeline_width is None:
        # Estimate: main_width minus label column and spacing
        timeline_width = max(1, main_width - TIMELINE_LABEL_ESTIMATE_WIDTH)

    # Ensure timeline_width is a valid integer
    try:
        timeline_width = int(timeline_width)
    except (TypeError, ValueError):
        timeline_width = max(1, main_width - TIMELINE_LABEL_ESTIMATE_WIDTH)

    return max(1, timeline_width)


def parse_host_file_line(line: str, line_number: int, input_file: str) -> Optional[Dict[str, str]]:
    """
    Parse a single line from the host input file.

    Args:
        line: Line of text from the file
        line_number: Line number in the file
        input_file: Path to the input file (for error messages)

    Returns:
        Dict with keys 'host', 'alias', 'ip' or None if invalid/comment
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = [part.strip() for part in stripped.split(",")]
    if len(parts) != 2:
        print(
            f"Warning: Invalid host entry at {input_file}:{line_number}. " "Expected format 'IP,alias'.",
            file=sys.stderr,
        )
        return None
    ip_text, alias = parts
    if not ip_text or not alias:
        print(
            f"Warning: Invalid host entry at {input_file}:{line_number}. " "IP address and alias are required.",
            file=sys.stderr,
        )
        return None
    try:
        ip_obj = ipaddress.ip_address(ip_text)
    except ValueError:
        print(
            f"Warning: Invalid IP address at {input_file}:{line_number}: '{ip_text}'.",
            file=sys.stderr,
        )
        return None
    if ip_obj.version != 4:
        print(
            f"Warning: Unsupported IP version at {input_file}:{line_number}: '{ip_text}'.",
            file=sys.stderr,
        )
        return None
    return {"host": ip_text, "alias": alias, "ip": ip_text}


def read_input_file(input_file: str) -> List[Dict[str, str]]:
    """
    Read and parse hosts from an input file.

    Args:
        input_file: Path to the file containing host entries

    Returns:
        List of host info dictionaries
    """
    host_list = []
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                entry = parse_host_file_line(line, line_number, input_file)
                if entry is not None:
                    host_list.append(entry)
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        return []
    except PermissionError:
        print(f"Error: Permission denied reading file '{input_file}'.")
        return []
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error reading input file '{input_file}': {e}")
        return []

    return host_list


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
    """Compute the page step for history navigation based on timeline width."""
    term_size = paraping.ui_render.get_terminal_size(fallback=(80, 24))
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

    # Compute layout and extract timeline width defensively
    layout_result = compute_main_layout(host_labels, main_width, main_height, header_lines)
    timeline_width = _extract_timeline_width_from_layout(layout_result, main_width)

    return timeline_width


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

    Returns:
        tuple: (page_step, new_cached_page_step, new_last_term_size)
    """

    def should_recalculate_page_step(cached_value, last_size, current_size):
        """Check if page step needs recalculation due to cache miss or terminal resize"""
        if cached_value is None or last_size is None:
            return True  # First time - need to calculate
        # Normalize last_size to ensure we can access .columns and .lines
        normalized_last = _normalize_term_size(last_size)
        if normalized_last is None:
            return True  # Invalid last_size, recalculate
        if current_size.columns != normalized_last.columns:
            return True  # Terminal width changed
        if current_size.lines != normalized_last.lines:
            return True  # Terminal height changed
        return False

    current_term_size = paraping.ui_render.get_terminal_size(fallback=(80, 24))

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


def build_host_infos(hosts: List[Union[str, Dict[str, str]]]) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """Build host information structures from a list of hosts."""
    host_infos = []
    host_map = {}
    for index, entry in enumerate(hosts):
        if isinstance(entry, str):
            host = entry
            alias = entry
            ip_address = None
        else:
            host = entry.get("host") or entry.get("ip")
            alias = entry.get("alias") or host
            ip_address = entry.get("ip")
        if not ip_address:
            try:
                ip_address = socket.gethostbyname(host)
            except (socket.gaierror, OSError):
                ip_address = host
        info = {
            "id": index,
            "host": host,
            "alias": alias,
            "ip": ip_address,
            "rdns": None,
            "rdns_pending": False,
            "asn": None,
            "asn_pending": False,
        }
        host_infos.append(info)
        host_map.setdefault(host, []).append(info)
    return host_infos, host_map


def create_state_snapshot(buffers: Dict[int, Any], stats: Dict[int, Any], timestamp: float) -> Dict[str, Any]:
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
    history_buffer: "deque[Dict[str, Any]]",
    buffers: Dict[int, Any],
    stats: Dict[int, Any],
    now: float,
    last_snapshot_time: float,
    history_offset: int,
) -> Tuple[float, int]:
    """Update history buffer with new snapshot if enough time has elapsed."""
    if (now - last_snapshot_time) < SNAPSHOT_INTERVAL_SECONDS:
        return last_snapshot_time, history_offset

    snapshot = create_state_snapshot(buffers, stats, now)
    history_buffer.append(snapshot)
    last_snapshot_time = now
    if history_offset > 0:
        history_offset = min(history_offset + 1, len(history_buffer) - 1)
    return last_snapshot_time, history_offset


def resolve_render_state(
    history_offset: int,
    history_buffer: "deque[Dict[str, Any]]",
    buffers: Dict[int, Any],
    stats: Dict[int, Any],
    paused: bool,
) -> Tuple[Dict[int, Any], Dict[int, Any], bool]:
    """Resolve the current render state based on history offset."""
    if 0 < history_offset <= len(history_buffer):
        snapshot = history_buffer[-(history_offset + 1)]
        return snapshot["buffers"], snapshot["stats"], True
    return buffers, stats, paused
