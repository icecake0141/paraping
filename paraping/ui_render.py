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
ParaPing UI Rendering Module

This module contains all UI rendering and display-related functions for ParaPing,
including ANSI text utilities, color/timeline building, layout computation,
view rendering, graph utilities, formatting functions, and terminal utilities.
"""

import os
import sys
import time
from collections import deque
from datetime import datetime, timezone, tzinfo
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from paraping import ui_display_entries as _ui_display_entries
from paraping import ui_graph as _ui_graph
from paraping import ui_layout as _ui_layout
from paraping import ui_panels as _ui_panels
from paraping import ui_pulse as _ui_pulse
from paraping import ui_status as _ui_status
from paraping import ui_text as _ui_text
from paraping import ui_timeline as _ui_timeline
from paraping.stats import compute_group_summary_data, compute_summary_data, resolve_group_labels, resolve_primary_group_label
from paraping.ui_text import ANSI_RESET, colorize_text, rjust_visible, strip_ansi, visible_cell_width

ANSI_ESCAPE_RE = _ui_text.ANSI_ESCAPE_RE
truncate_visible = _ui_text.truncate_visible
visible_len = _ui_text.visible_len
pad_visible = _ui_text.pad_visible
_resolve_kitt_gradient_rings = _ui_pulse._resolve_kitt_gradient_rings
_resolve_kitt_scanner_speed_hz = _ui_pulse._resolve_kitt_scanner_speed_hz
build_ascii_graph = _ui_graph.build_ascii_graph
build_activity_indicator = _ui_pulse.build_activity_indicator
build_kitt_gradient_bar = _ui_pulse.build_kitt_gradient_bar
build_kitt_scanner_bar = _ui_pulse.build_kitt_scanner_bar
build_sparkline = _ui_graph.build_sparkline
build_time_axis = _ui_graph.build_time_axis
box_lines = _ui_panels.box_lines
compute_main_layout = _ui_layout.compute_main_layout
compute_panel_sizes = _ui_layout.compute_panel_sizes
compute_pulse_panel_sizes = _ui_layout.compute_pulse_panel_sizes
compute_summary_height_bounds = _ui_layout.compute_summary_height_bounds
build_colored_sparkline = _ui_timeline.build_colored_sparkline
build_colored_square_timeline = _ui_timeline.build_colored_square_timeline
build_colored_timeline = _ui_timeline.build_colored_timeline
build_display_entries = _ui_display_entries.build_display_entries
build_display_names = _ui_display_entries.build_display_names
build_group_header_line_map = _ui_display_entries.build_group_header_line_map
build_group_tree_label_map = _ui_display_entries.build_group_tree_label_map
can_render_full_summary = _ui_panels.can_render_full_summary
compute_activity_indicator_width = _ui_pulse.compute_activity_indicator_width
_parse_positive_float = _ui_status._parse_positive_float
build_status_line = _ui_status.build_status_line
build_status_metrics = _ui_status.build_status_metrics
estimate_ping_rate = _ui_status.estimate_ping_rate
format_asn_label = _ui_display_entries.format_asn_label
format_display_name = _ui_display_entries.format_display_name
format_status_line = _ui_timeline.format_status_line
format_summary_line = _ui_panels.format_summary_line
host_label_status = _ui_timeline.host_label_status
latest_non_pending_status_from_timeline = _ui_timeline.latest_non_pending_status_from_timeline
latest_status_from_timeline = _ui_timeline.latest_status_from_timeline
pad_lines = _ui_panels.pad_lines
render_fullscreen_rtt_graph = _ui_graph.render_fullscreen_rtt_graph
render_help_view = _ui_panels.render_help_view
render_kitt_bottom_band = _ui_pulse.render_kitt_bottom_band
render_pulse_panel = _ui_pulse.render_pulse_panel
render_status_box = _ui_panels.render_status_box
render_summary_view = _ui_panels.render_summary_view
_summary_render_width = _ui_layout.summary_render_width
resolve_display_name = _ui_display_entries.resolve_display_name
resolve_group_header_lines = _ui_display_entries.resolve_group_header_lines
resolve_host_label_status = _ui_timeline.resolve_host_label_status
resample_values = _ui_graph.resample_values
resolve_boxed_dimensions = _ui_panels.resolve_boxed_dimensions
should_show_asn = _ui_layout.should_show_asn
status_from_symbol = _ui_timeline.status_from_symbol

# Display constants
ACTIVITY_INDICATOR_WIDTH = _ui_pulse.ACTIVITY_INDICATOR_WIDTH
ACTIVITY_INDICATOR_HEIGHT = _ui_pulse.ACTIVITY_INDICATOR_HEIGHT
ACTIVITY_INDICATOR_SPEED_HZ = _ui_pulse.ACTIVITY_INDICATOR_SPEED_HZ
STATUS_METRICS_SEPARATOR = _ui_status.STATUS_METRICS_SEPARATOR
STATUS_METRICS_TEMPLATE = _ui_status.STATUS_METRICS_TEMPLATE

# Global state for rendering
LAST_RENDER_LINES: Optional[List[str]] = None
KITT_SCANNER_STATE = _ui_pulse.KITT_SCANNER_STATE


# ============================================================================
# Color/Timeline Building Functions
# ============================================================================


# ============================================================================
# Layout/Geometry Functions
# ============================================================================


def get_terminal_size(fallback: Tuple[int, int] = (80, 24)) -> os.terminal_size:
    """
    Get the terminal size by directly querying the terminal.

    This function uses os.get_terminal_size() which queries the actual
    terminal instead of checking COLUMNS/LINES environment variables
    first (like shutil does). This ensures the size updates when the
    terminal is resized.

    Args:
        fallback: Tuple of (columns, lines) to use if terminal size
                  cannot be determined

    Returns:
        os.terminal_size with columns and lines attributes
    """
    try:
        # Try stdout first
        if sys.stdout.isatty():
            return os.get_terminal_size(sys.stdout.fileno())
    except (AttributeError, ValueError, OSError):
        pass

    try:
        # Try stderr if stdout fails
        if sys.stderr.isatty():
            return os.get_terminal_size(sys.stderr.fileno())
    except (AttributeError, ValueError, OSError):
        pass

    try:
        # Try stdin as last resort
        if sys.stdin.isatty():
            return os.get_terminal_size(sys.stdin.fileno())
    except (AttributeError, ValueError, OSError):
        pass

    # Fall back to default size
    return os.terminal_size(fallback)


def compute_host_scroll_bounds(
    host_infos: Sequence[Dict[str, Any]],
    buffers: Dict[int, Dict[str, Any]],
    stats: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    panel_position: str,
    mode_label: str,
    sort_mode: str,
    filter_mode: str,
    slow_threshold: float,
    show_asn: bool,
    summary_mode: str = "rates",
    summary_scope: str = "host",
    group_by: str = "none",
    group_sort_enabled: bool = False,
    asn_width: int = 8,
    header_lines: int = 2,
    pulse_position: str = "none",
) -> Tuple[int, int, int]:
    """Compute the scroll bounds for the host list."""
    term_size = get_terminal_size(fallback=(80, 24))
    term_width = term_size.columns
    term_height = term_size.lines
    min_main_height = 5
    gap_size = 1
    use_panel_boxes = True
    status_box_height = 3 if term_height >= 4 and term_width >= 2 else 1
    panel_height = max(1, term_height - status_box_height)

    include_asn = should_show_asn(host_infos, mode_label, show_asn, term_width, asn_width=asn_width)
    display_names = build_display_names(host_infos, mode_label, include_asn, asn_width)
    main_width, main_height, _, _, _ = compute_panel_sizes(
        term_width,
        panel_height,
        panel_position,
        min_main_height=min_main_height,
    )
    main_width, main_height, _, _, _ = compute_pulse_panel_sizes(
        main_width,
        main_height,
        pulse_position,
        min_main_width=20,
        min_panel_height=3,
    )
    display_entries = build_display_entries(
        host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        sort_mode,
        filter_mode,
        slow_threshold,
        group_by=group_by,
        group_sort_enabled=group_sort_enabled,
    )
    active_host_infos = [info for info in host_infos if info.get("active", True)]
    active_host_ids = {info["id"] for info in active_host_infos}
    ordered_host_ids = [host_id for host_id, _label in display_entries if host_id in active_host_ids]
    summary_data = compute_summary_data(
        active_host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        ordered_host_ids=ordered_host_ids,
    )
    group_summary_data: List[Dict[str, Any]] = []
    if group_by != "none":
        group_order: List[str] = []
        host_group_labels = {info["id"]: resolve_primary_group_label(info, group_by) for info in active_host_infos}
        for host_id in ordered_host_ids:
            label = host_group_labels.get(host_id)
            if label and label not in group_order:
                group_order.append(label)
        group_summary_data = compute_group_summary_data(
            active_host_infos,
            display_names,
            buffers,
            stats,
            symbols,
            group_by=group_by,
            ordered_group_labels=group_order,
        )
    summary_source = group_summary_data if summary_scope == "group" and group_by != "none" else summary_data
    if panel_position in ("top", "bottom"):
        _, _, summary_width, summary_height, _ = compute_panel_sizes(
            term_width,
            panel_height,
            panel_position,
            min_main_height=min_main_height,
        )
        summary_render_width = _summary_render_width(summary_width, use_panel_boxes)
        summary_all = can_render_full_summary(summary_source, summary_render_width)
        content_height, minimal_height = compute_summary_height_bounds(
            summary_source,
            summary_mode,
            summary_all,
            summary_width,
            boxed=use_panel_boxes,
        )
        max_summary_height = max(0, panel_height - min_main_height - gap_size)
        summary_height = min(summary_height, content_height, max_summary_height)
        summary_height = max(summary_height, min(minimal_height, max_summary_height))
        main_height = max(min_main_height, panel_height - summary_height - gap_size)
    host_labels = [entry[1] for entry in display_entries]
    if not host_labels:
        host_labels = [info["alias"] for info in host_infos]
    _, _, _, visible_hosts = compute_main_layout(host_labels, main_width, main_height, header_lines)
    total_hosts = len(display_entries)
    max_offset = max(0, total_hosts - visible_hosts)
    return max_offset, visible_hosts, total_hosts


# ============================================================================
# Box/Padding Utilities
# ============================================================================


def extract_trailing_pulse_space(lines: Sequence[str], boxed: bool) -> Tuple[List[str], int]:
    """Return trimmed lines and Pulse height derived from trailing empty rows."""
    trimmed = list(lines)
    if not trimmed:
        return trimmed, 0

    empty_rows = 0
    if boxed and len(trimmed) >= 3:
        while len(trimmed) - 2 - empty_rows > 0:
            candidate = strip_ansi(trimmed[-2 - empty_rows])
            if candidate.startswith("|") and candidate.endswith("|") and not candidate[1:-1].strip():
                empty_rows += 1
                continue
            break
        if empty_rows <= 1:
            return trimmed, 0
        del trimmed[len(trimmed) - 1 - empty_rows : len(trimmed) - 1]
        return trimmed, empty_rows - 1

    while trimmed and not strip_ansi(trimmed[-1]).strip():
        empty_rows += 1
        trimmed.pop()
    if empty_rows <= 1:
        return list(lines), 0
    return trimmed, empty_rows - 1


def resize_buffers(buffers: Dict[int, Dict[str, Any]], timeline_width: int, symbols: Dict[str, str]) -> None:
    """Resize all buffers to match the timeline width."""
    for _, host_buffers in buffers.items():
        if host_buffers["timeline"].maxlen != timeline_width:
            host_buffers["timeline"] = deque(host_buffers["timeline"], maxlen=timeline_width)
        if host_buffers["rtt_history"].maxlen != timeline_width:
            host_buffers["rtt_history"] = deque(host_buffers["rtt_history"], maxlen=timeline_width)
        if host_buffers["time_history"].maxlen != timeline_width:
            host_buffers["time_history"] = deque(host_buffers["time_history"], maxlen=timeline_width)
        if host_buffers["ttl_history"].maxlen != timeline_width:
            host_buffers["ttl_history"] = deque(host_buffers["ttl_history"], maxlen=timeline_width)
        for status in symbols:
            if host_buffers["categories"][status].maxlen != timeline_width:
                host_buffers["categories"][status] = deque(host_buffers["categories"][status], maxlen=timeline_width)


# ============================================================================
# Display Building Functions
# ============================================================================


# ============================================================================
# Rendering Functions
# ============================================================================


def render_timeline_view(
    display_entries: Sequence[Tuple[Any, ...]],
    buffers: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    width: int,
    height: int,
    header: str,
    use_color: bool = False,
    scroll_offset: int = 0,
    header_lines: int = 2,
    boxed: bool = False,
    interval_seconds: float = 1.0,
    show_group_headers: bool = False,
    host_group_labels: Optional[Dict[int, str]] = None,
    host_tree_labels: Optional[Dict[int, str]] = None,
    group_header_lines: Optional[Mapping[str, Union[str, List[str]]]] = None,
    group_by: str = "none",
) -> List[str]:
    """Render the timeline view."""
    if width <= 0 or height <= 0:
        return []

    render_width, render_height, can_box = resolve_boxed_dimensions(width, height, boxed)
    label_overrides = build_group_tree_label_map(
        display_entries,
        show_group_headers=show_group_headers,
        host_group_labels=host_group_labels,
        host_tree_labels=host_tree_labels,
        group_by=group_by,
    )
    host_labels = [
        label_overrides.get(entry[0], str(entry[1]) if len(entry) >= 2 else str(entry[0])) for entry in display_entries
    ]
    # Account for time axis line when calculating visible hosts
    # header_lines + 1 for the time axis line
    render_width, label_width, timeline_width, visible_hosts = compute_main_layout(
        host_labels, render_width, render_height, header_lines + 1
    )
    reserve_overflow_line = len(display_entries) > visible_hosts
    host_capacity = max(1, visible_hosts - 1) if reserve_overflow_line else visible_hosts
    max_offset = max(0, len(display_entries) - host_capacity)
    scroll_offset = min(max(scroll_offset, 0), max_offset)
    truncated_entries = display_entries[scroll_offset : scroll_offset + host_capacity]

    resize_buffers(buffers, timeline_width, symbols)

    lines = []
    lines.append(header)
    lines.append("".join("-" for _ in range(render_width)))
    current_primary_group = None
    current_tree_group = None
    for entry in truncated_entries:
        host = entry[0]
        base_label = str(entry[1]) if len(entry) >= 2 else str(entry[0])
        label = label_overrides.get(host, base_label)
        is_removed = "[REMOVED]" in label
        if show_group_headers:
            header_stack, current_primary_group, current_tree_group = resolve_group_header_lines(
                host,
                group_by,
                current_primary_group,
                current_tree_group,
                host_group_labels,
                host_tree_labels,
                group_header_lines,
            )
            for header_line in header_stack:
                lines.append(header_line[:render_width])
        timeline_symbols = list(buffers[host]["timeline"])
        timeline = build_colored_timeline(timeline_symbols, symbols, use_color)
        timeline = rjust_visible(timeline, timeline_width)
        label_status = resolve_host_label_status(timeline_symbols, symbols, is_removed=is_removed)
        colored_label = colorize_text(label, label_status, use_color)
        lines.append(format_status_line(colored_label, timeline, label_width))

    # Add time axis at the bottom of the timeline area
    time_axis = build_time_axis(timeline_width, label_width, interval_seconds=interval_seconds)
    lines.append(time_axis)

    if len(display_entries) > len(truncated_entries):
        remaining = len(display_entries) - len(truncated_entries)
        lines.append(f"... ({remaining} host(s) not shown)")

    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


def render_sparkline_view(
    display_entries: Sequence[Tuple[Any, ...]],
    buffers: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    width: int,
    height: int,
    header: str,
    use_color: bool = False,
    scroll_offset: int = 0,
    header_lines: int = 2,
    boxed: bool = False,
    interval_seconds: float = 1.0,
    show_group_headers: bool = False,
    host_group_labels: Optional[Dict[int, str]] = None,
    host_tree_labels: Optional[Dict[int, str]] = None,
    group_header_lines: Optional[Mapping[str, Union[str, List[str]]]] = None,
    group_by: str = "none",
) -> List[str]:
    """Render the sparkline view."""
    if width <= 0 or height <= 0:
        return []

    render_width, render_height, can_box = resolve_boxed_dimensions(width, height, boxed)
    label_overrides = build_group_tree_label_map(
        display_entries,
        show_group_headers=show_group_headers,
        host_group_labels=host_group_labels,
        host_tree_labels=host_tree_labels,
        group_by=group_by,
    )
    host_labels = [
        label_overrides.get(entry[0], str(entry[1]) if len(entry) >= 2 else str(entry[0])) for entry in display_entries
    ]
    # Account for time axis line when calculating visible hosts
    # header_lines + 1 for the time axis line
    render_width, label_width, timeline_width, visible_hosts = compute_main_layout(
        host_labels, render_width, render_height, header_lines + 1
    )
    reserve_overflow_line = len(display_entries) > visible_hosts
    host_capacity = max(1, visible_hosts - 1) if reserve_overflow_line else visible_hosts
    max_offset = max(0, len(display_entries) - host_capacity)
    scroll_offset = min(max(scroll_offset, 0), max_offset)
    truncated_entries = display_entries[scroll_offset : scroll_offset + host_capacity]

    resize_buffers(buffers, timeline_width, symbols)

    lines = []
    lines.append(header)
    lines.append("".join("-" for _ in range(render_width)))
    current_primary_group = None
    current_tree_group = None
    for entry in truncated_entries:
        host = entry[0]
        base_label = str(entry[1]) if len(entry) >= 2 else str(entry[0])
        label = label_overrides.get(host, base_label)
        is_removed = "[REMOVED]" in label
        if show_group_headers:
            header_stack, current_primary_group, current_tree_group = resolve_group_header_lines(
                host,
                group_by,
                current_primary_group,
                current_tree_group,
                host_group_labels,
                host_tree_labels,
                group_header_lines,
            )
            for header_line in header_stack:
                lines.append(header_line[:render_width])
        rtt_values = list(buffers[host]["rtt_history"])[-timeline_width:]
        status_symbols = list(buffers[host]["timeline"])[-timeline_width:]
        sparkline = build_sparkline(rtt_values, status_symbols, symbols["fail"])
        sparkline = build_colored_sparkline(sparkline, status_symbols, symbols, use_color)
        sparkline = rjust_visible(sparkline, timeline_width)
        label_status = resolve_host_label_status(status_symbols, symbols, is_removed=is_removed)
        colored_label = colorize_text(label, label_status, use_color)
        lines.append(format_status_line(colored_label, sparkline, label_width))

    # Add time axis at the bottom of the sparkline area
    time_axis = build_time_axis(timeline_width, label_width, interval_seconds=interval_seconds)
    lines.append(time_axis)

    if len(display_entries) > len(truncated_entries):
        remaining = len(display_entries) - len(truncated_entries)
        lines.append(f"... ({remaining} host(s) not shown)")

    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


def render_square_view(
    display_entries: Sequence[Tuple[Any, ...]],
    buffers: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    width: int,
    height: int,
    header: str,
    use_color: bool = False,
    scroll_offset: int = 0,
    header_lines: int = 2,
    boxed: bool = False,
    interval_seconds: float = 1.0,
    show_group_headers: bool = False,
    host_group_labels: Optional[Dict[int, str]] = None,
    host_tree_labels: Optional[Dict[int, str]] = None,
    group_header_lines: Optional[Mapping[str, Union[str, List[str]]]] = None,
    group_by: str = "none",
) -> List[str]:
    """Render the square view as a time-series (horizontal sequence of colored squares)."""
    if width <= 0 or height <= 0:
        return []

    render_width, render_height, can_box = resolve_boxed_dimensions(width, height, boxed)
    label_overrides = build_group_tree_label_map(
        display_entries,
        show_group_headers=show_group_headers,
        host_group_labels=host_group_labels,
        host_tree_labels=host_tree_labels,
        group_by=group_by,
    )
    host_labels = [
        label_overrides.get(entry[0], str(entry[1]) if len(entry) >= 2 else str(entry[0])) for entry in display_entries
    ]
    # Account for time axis line when calculating visible hosts
    # header_lines + 1 for the time axis line
    render_width, label_width, timeline_width, visible_hosts = compute_main_layout(
        host_labels, render_width, render_height, header_lines + 1
    )
    reserve_overflow_line = len(display_entries) > visible_hosts
    host_capacity = max(1, visible_hosts - 1) if reserve_overflow_line else visible_hosts
    max_offset = max(0, len(display_entries) - host_capacity)
    scroll_offset = min(max(scroll_offset, 0), max_offset)
    truncated_entries = display_entries[scroll_offset : scroll_offset + host_capacity]

    resize_buffers(buffers, timeline_width, symbols)

    lines = []
    lines.append(header)
    lines.append("".join("-" for _ in range(render_width)))

    current_primary_group = None
    current_tree_group = None
    for entry in truncated_entries:
        host = entry[0]
        base_label = str(entry[1]) if len(entry) >= 2 else str(entry[0])
        label = label_overrides.get(host, base_label)
        is_removed = "[REMOVED]" in label
        if show_group_headers:
            header_stack, current_primary_group, current_tree_group = resolve_group_header_lines(
                host,
                group_by,
                current_primary_group,
                current_tree_group,
                host_group_labels,
                host_tree_labels,
                group_header_lines,
            )
            for header_line in header_stack:
                lines.append(header_line[:render_width])
        timeline_symbols = list(buffers[host]["timeline"])
        # Build colored square timeline from all timeline symbols
        square_timeline = build_colored_square_timeline(timeline_symbols, symbols, use_color)
        square_timeline = rjust_visible(square_timeline, timeline_width)
        label_status = resolve_host_label_status(timeline_symbols, symbols, is_removed=is_removed)
        colored_label = colorize_text(label, label_status, use_color)
        lines.append(format_status_line(colored_label, square_timeline, label_width))

    # Add time axis at the bottom of the square timeline area
    time_axis = build_time_axis(timeline_width, label_width, interval_seconds=interval_seconds)
    lines.append(time_axis)

    if len(display_entries) > len(truncated_entries):
        remaining = len(display_entries) - len(truncated_entries)
        lines.append(f"... ({remaining} host(s) not shown)")

    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


def render_main_view(
    display_entries: Sequence[Tuple[Any, ...]],
    buffers: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    width: int,
    height: int,
    mode_label: str,
    display_mode: str,
    paused: bool,
    timestamp: str,
    now_utc: datetime,
    use_color: bool = False,
    scroll_offset: int = 0,
    header_lines: int = 2,
    boxed: bool = False,
    interval_seconds: float = 1.0,
    dormant: bool = False,
    show_group_headers: bool = False,
    host_group_labels: Optional[Dict[int, str]] = None,
    host_tree_labels: Optional[Dict[int, str]] = None,
    group_header_lines: Optional[Mapping[str, Union[str, List[str]]]] = None,
    group_by: str = "none",
    kitt_mode_enabled: bool = False,
    kitt_style: str = "scanner",
) -> List[str]:
    """Render the main view (timeline, sparkline, or square)."""
    del kitt_style  # Main-panel style remains unchanged; bottom band handles style rendering.
    pause_label = "DORMANT" if dormant else ("PAUSED" if paused else "LIVE")
    header_base = f"ParaPing - {pause_label} results [{mode_label} | {display_mode}] {timestamp}"
    activity_indicator = ""
    if not paused:
        indicator_width = compute_activity_indicator_width(width, header_base)
        if indicator_width > 0:
            indicator_height = ACTIVITY_INDICATOR_HEIGHT + (2 if kitt_mode_enabled else 0)
            indicator_speed = ACTIVITY_INDICATOR_SPEED_HZ + (4 if kitt_mode_enabled else 0)
            activity_indicator = build_activity_indicator(
                now_utc,
                width=indicator_width,
                max_height=indicator_height,
                speed_hz=indicator_speed,
            )
    if activity_indicator:
        header = f"{header_base} {activity_indicator}"
    else:
        header = header_base
    if display_mode == "sparkline":
        return render_sparkline_view(
            display_entries,
            buffers,
            symbols,
            width,
            height,
            header,
            use_color,
            scroll_offset,
            header_lines,
            boxed,
            interval_seconds,
            show_group_headers=show_group_headers,
            host_group_labels=host_group_labels,
            host_tree_labels=host_tree_labels,
            group_header_lines=group_header_lines,
            group_by=group_by,
        )
    if display_mode == "square":
        return render_square_view(
            display_entries,
            buffers,
            symbols,
            width,
            height,
            header,
            use_color,
            scroll_offset,
            header_lines,
            boxed,
            interval_seconds,
            show_group_headers=show_group_headers,
            host_group_labels=host_group_labels,
            host_tree_labels=host_tree_labels,
            group_header_lines=group_header_lines,
            group_by=group_by,
        )
    return render_timeline_view(
        display_entries,
        buffers,
        symbols,
        width,
        height,
        header,
        use_color,
        scroll_offset,
        header_lines,
        boxed,
        interval_seconds,
        show_group_headers=show_group_headers,
        host_group_labels=host_group_labels,
        host_tree_labels=host_tree_labels,
        group_header_lines=group_header_lines,
        group_by=group_by,
    )


def render_host_selection_view(
    display_entries: Sequence[Tuple[Any, ...]],
    selected_index: int,
    width: int,
    height: int,
    mode_label: str,
) -> List[str]:
    """Render the host selection view for choosing a host for RTT graph."""
    if width <= 0 or height <= 0:
        return []

    title = f"Select Host for RTT Graph [{mode_label}]"
    lines = [title[:width], "-" * width]
    status_line = "j/k or ↑/↓: move | Enter: select | ESC: cancel"
    list_height = max(0, height - 3)

    if not display_entries:
        lines.append("No hosts match current filter."[:width])
        lines = pad_lines(lines, width, height)
        lines[-1] = status_line[:width].ljust(width)
        return lines

    max_index = len(display_entries) - 1
    selected_index = min(max(selected_index, 0), max_index)

    start_index = max(
        0,
        min(selected_index - list_height + 1, max_index - list_height + 1),
    )
    end_index = min(len(display_entries), start_index + list_height)

    for idx in range(start_index, end_index):
        entry = display_entries[idx]
        label = str(entry[1]) if len(entry) >= 2 else str(entry[0])
        prefix = "> " if idx == selected_index else "  "
        entry_label = f"{prefix}{label}"
        lines.append(entry_label[:width].ljust(width))

    if len(display_entries) > end_index:
        remaining = len(display_entries) - end_index
        lines.append(f"... ({remaining} more)".ljust(width)[:width])

    lines = pad_lines(lines, width, height)
    lines[-1] = status_line[:width].ljust(width)
    return lines


def build_display_lines(  # noqa: C901
    host_infos: Sequence[Dict[str, Any]],
    buffers: Dict[int, Dict[str, Any]],
    stats: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    panel_position: str,
    mode_label: str,
    display_mode: str,
    summary_mode: str,
    sort_mode: str,
    filter_mode: str,
    slow_threshold: float,
    show_help: bool,
    show_asn: bool,
    paused: bool,
    status_message: Optional[str],
    timestamp: str,
    now_utc: datetime,
    use_color: bool = False,
    host_scroll_offset: int = 0,
    summary_fullscreen: bool = False,
    asn_width: int = 8,
    header_lines: int = 2,
    interval_seconds: float = 1.0,
    dormant: bool = False,
    summary_scope: str = "host",
    group_by: str = "none",
    group_sort_enabled: bool = False,
    kitt_mode_enabled: bool = False,
    kitt_style: str = "scanner",
    pulse_position: str = "none",
) -> List[str]:
    """Build all display lines for the current state."""
    # Algorithm overview:
    # - Measure terminal size and derive main/summary panel geometry.
    # - Build sorted/filtered display entries, then render main + summary views.
    # - Stitch panels based on position (left/right/top/bottom/none) or help mode.
    # - Append status metrics and pad to the terminal height.
    # Key state/invariants:
    # - Timeline/sparkline columns are right-aligned so newest pings appear on the right.
    # - ANSI-aware padding keeps colored output aligned with terminal width calculations.
    # - panel_height excludes the status box; combined_lines are always padded to term_width.
    # Edge cases:
    # - Empty host list yields empty display_entries/summary_data but still renders headers.
    # - Small terminals force status_box_height=1 and may disable summary panels.
    term_size = get_terminal_size(fallback=(80, 24))
    term_width = term_size.columns
    term_height = term_size.lines
    min_main_height = 5
    gap_size = 1
    use_panel_boxes = True
    status_box_height = 3 if term_height >= 4 and term_width >= 2 else 1
    panel_height = max(1, term_height - status_box_height)

    include_asn = should_show_asn(host_infos, mode_label, show_asn, term_width, asn_width=asn_width)
    display_names = build_display_names(host_infos, mode_label, include_asn, asn_width)

    display_entries = build_display_entries(
        host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        sort_mode,
        filter_mode,
        slow_threshold,
        group_by=group_by,
        group_sort_enabled=group_sort_enabled,
    )
    main_width, main_height, summary_width, summary_height, resolved_position = compute_panel_sizes(
        term_width,
        panel_height,
        panel_position,
        min_main_height=min_main_height,
    )
    main_width, main_height, pulse_width, _pulse_height, resolved_pulse_position = compute_pulse_panel_sizes(
        main_width,
        main_height,
        pulse_position if kitt_mode_enabled else "none",
        min_main_width=20,
        min_panel_height=3,
    )
    active_host_infos = [info for info in host_infos if info.get("active", True)]
    active_host_ids = {info["id"] for info in active_host_infos}
    host_group_labels = {info["id"]: resolve_primary_group_label(info, group_by) for info in active_host_infos}
    host_tree_labels = (
        {info["id"]: resolve_group_labels(info, group_by)[0] for info in active_host_infos}
        if group_by == "site>tag1"
        else host_group_labels
    )
    ordered_host_ids = [host_id for host_id, _label in display_entries if host_id in active_host_ids]
    summary_data = compute_summary_data(
        active_host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        ordered_host_ids=ordered_host_ids,
    )
    group_summary_data: List[Dict[str, Any]] = []
    if group_by != "none":
        group_order: List[str] = []
        group_label_source = host_tree_labels if group_by == "site>tag1" else host_group_labels
        for host_id in ordered_host_ids:
            label = group_label_source.get(host_id)
            if label and label not in group_order:
                group_order.append(label)
        group_summary_data = compute_group_summary_data(
            active_host_infos,
            display_names,
            buffers,
            stats,
            symbols,
            group_by=group_by,
            ordered_group_labels=group_order,
        )
    summary_source = group_summary_data if summary_scope == "group" and group_by != "none" else summary_data
    if not summary_fullscreen and resolved_position in ("top", "bottom") and summary_height > 0:
        summary_render_width = _summary_render_width(summary_width, use_panel_boxes)
        summary_all_for_height = can_render_full_summary(summary_source, summary_render_width)
        content_height, minimal_height = compute_summary_height_bounds(
            summary_source,
            summary_mode,
            summary_all_for_height,
            summary_width,
            boxed=use_panel_boxes,
        )
        max_summary_height = max(0, panel_height - min_main_height - gap_size)
        summary_height = min(summary_height, content_height, max_summary_height)
        summary_height = max(summary_height, min(minimal_height, max_summary_height))
        main_height = max(min_main_height, panel_height - summary_height - gap_size)
    group_header_lines = build_group_header_line_map(active_host_infos, ordered_host_ids, group_by, group_summary_data)
    kitt_total_hosts = len(active_host_infos)
    fail_symbol = symbols.get("fail")
    kitt_error_hosts = 0
    if fail_symbol:
        for info in active_host_infos:
            timeline = buffers.get(info["id"], {}).get("timeline")
            if timeline and timeline[-1] == fail_symbol:
                kitt_error_hosts += 1
    summary_all = False
    main_lines = []
    summary_lines = []
    if summary_fullscreen:
        summary_all = can_render_full_summary(summary_source, term_width)
        summary_lines = render_summary_view(
            summary_source,
            term_width,
            panel_height,
            summary_mode,
            prefer_all=summary_all,
            boxed=use_panel_boxes,
        )
    else:
        main_lines = render_main_view(
            display_entries,
            buffers,
            symbols,
            main_width,
            main_height,
            mode_label,
            display_mode,
            paused,
            timestamp,
            now_utc,
            use_color,
            host_scroll_offset,
            header_lines,
            boxed=use_panel_boxes,
            interval_seconds=interval_seconds,
            dormant=dormant,
            show_group_headers=summary_scope == "group" and group_by != "none",
            host_group_labels=host_group_labels,
            host_tree_labels=host_tree_labels,
            group_header_lines=group_header_lines,
            kitt_mode_enabled=kitt_mode_enabled,
            kitt_style=kitt_style,
            group_by=group_by,
        )
        summary_render_width = _summary_render_width(summary_width, use_panel_boxes)
        summary_all = resolved_position in ("top", "bottom") and can_render_full_summary(summary_source, summary_render_width)
        summary_lines = render_summary_view(
            summary_source,
            summary_width,
            summary_height,
            summary_mode,
            prefer_all=summary_all,
            boxed=use_panel_boxes,
        )

    gap = " "
    combined_lines = []
    if show_help:
        combined_lines = render_help_view(term_width, panel_height, boxed=use_panel_boxes)
    elif summary_fullscreen:
        combined_lines = summary_lines
    else:
        pulse_lines: List[str] = []
        if kitt_mode_enabled and resolved_pulse_position in ("left", "right") and pulse_width > 0:
            pulse_lines = render_pulse_panel(
                pulse_width,
                main_height,
                kitt_style,
                now_utc,
                use_color,
                error_hosts=kitt_error_hosts,
                total_hosts=kitt_total_hosts,
            )
        elif kitt_mode_enabled and resolved_pulse_position in ("top", "bottom"):
            main_lines, pulse_height = extract_trailing_pulse_space(main_lines, boxed=use_panel_boxes)
            if pulse_height >= 3:
                pulse_lines = render_pulse_panel(
                    main_width,
                    pulse_height,
                    kitt_style,
                    now_utc,
                    use_color,
                    error_hosts=kitt_error_hosts,
                    total_hosts=kitt_total_hosts,
                )

        if resolved_position in ("left", "right"):
            for main_line, summary_line in zip(main_lines, summary_lines):
                if resolved_position == "left":
                    combined_lines.append(f"{summary_line}{gap}{main_line}")
                else:
                    combined_lines.append(f"{main_line}{gap}{summary_line}")
        elif resolved_position == "top":
            combined_lines = summary_lines + [""] + main_lines
        elif resolved_position == "bottom":
            combined_lines = main_lines + [""] + summary_lines
        else:
            combined_lines = main_lines

        if pulse_lines:
            if resolved_pulse_position in ("left", "right"):
                merged_lines = []
                for combined_line, pulse_line in zip(combined_lines, pulse_lines):
                    if resolved_pulse_position == "left":
                        merged_lines.append(f"{pulse_line}{gap}{combined_line}")
                    else:
                        merged_lines.append(f"{combined_line}{gap}{pulse_line}")
                combined_lines = merged_lines
            elif resolved_pulse_position == "top":
                combined_lines = pulse_lines + [""] + combined_lines
            elif resolved_pulse_position == "bottom":
                combined_lines = combined_lines + [""] + pulse_lines

    status_metrics = build_status_metrics(active_host_infos, stats, interval_seconds=interval_seconds)
    status_details = f"{status_metrics} | {status_message}" if status_message else status_metrics
    status_line = build_status_line(
        sort_mode,
        filter_mode,
        summary_mode,
        paused,
        status_details,
        summary_all=summary_all,
        summary_fullscreen=summary_fullscreen,
        dormant=dormant,
        summary_scope=summary_scope,
        group_by=group_by,
    )
    if panel_height > 0:
        combined_lines = pad_lines(combined_lines, term_width, panel_height)

    if status_box_height == 1:
        status_lines = [status_line[:term_width].ljust(term_width)]
    else:
        status_lines = render_status_box(status_line, term_width)

    if panel_height <= 0:
        return status_lines
    return combined_lines + status_lines


def render_display(  # noqa: C901
    host_infos: Sequence[Dict[str, Any]],
    buffers: Dict[int, Dict[str, Any]],
    stats: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    panel_position: str,
    mode_label: str,
    display_mode: str,
    summary_mode: str,
    sort_mode: str,
    filter_mode: str,
    slow_threshold: float,
    show_help: bool,
    show_asn: bool,
    paused: bool,
    status_message: Optional[str],
    display_tz: tzinfo,
    use_color: bool = False,
    host_scroll_offset: int = 0,
    summary_fullscreen: bool = False,
    asn_width: int = 8,
    header_lines: int = 2,
    override_lines: Optional[List[str]] = None,
    interval_seconds: float = 1.0,
    dormant: bool = False,
    summary_scope: str = "host",
    group_by: str = "none",
    group_sort_enabled: bool = False,
    kitt_mode_enabled: bool = False,
    kitt_style: str = "scanner",
    pulse_position: str = "none",
) -> None:
    """Render the complete display to the terminal."""
    global LAST_RENDER_LINES
    now_utc = datetime.now(timezone.utc)
    timestamp = format_timestamp(now_utc, display_tz)
    combined_lines = override_lines
    if combined_lines is None:
        combined_lines = build_display_lines(
            host_infos,
            buffers,
            stats,
            symbols,
            panel_position,
            mode_label,
            display_mode,
            summary_mode,
            sort_mode,
            filter_mode,
            slow_threshold,
            show_help,
            show_asn,
            paused,
            status_message,
            timestamp,
            now_utc,
            use_color,
            host_scroll_offset,
            summary_fullscreen,
            asn_width,
            header_lines,
            interval_seconds,
            dormant=dormant,
            summary_scope=summary_scope,
            group_by=group_by,
            group_sort_enabled=group_sort_enabled,
            kitt_mode_enabled=kitt_mode_enabled,
            kitt_style=kitt_style,
            pulse_position=pulse_position,
        )
    if not combined_lines:
        return

    if LAST_RENDER_LINES is None:
        sys.stdout.write("\x1b[2J\x1b[H")
        output_chunks = []
        for index, line in enumerate(combined_lines):
            output_chunks.append(f"\x1b[{index + 1};1H\x1b[2K{line}")
        sys.stdout.write("".join(output_chunks))
        sys.stdout.flush()
        LAST_RENDER_LINES = combined_lines
        return

    max_lines = max(len(LAST_RENDER_LINES), len(combined_lines))
    pulse_start = _find_pulse_start(combined_lines)
    if pulse_start is None:
        pulse_start = _find_pulse_start(LAST_RENDER_LINES)
    output_chunks = []
    for index in range(max_lines):
        previous_line = LAST_RENDER_LINES[index] if index < len(LAST_RENDER_LINES) else None
        current_line = combined_lines[index] if index < len(combined_lines) else ""
        if previous_line == current_line and index < len(combined_lines):
            continue
        if previous_line is None:
            output_chunks.append(f"\x1b[{index + 1};1H\x1b[2K{current_line}")
            continue
        if not current_line:
            output_chunks.append(f"\x1b[{index + 1};1H\x1b[2K")
            continue
        if pulse_start is not None and index >= pulse_start:
            output_chunks.append(f"\x1b[{index + 1};1H\x1b[2K{current_line}")
            continue
        diff_start = _find_safe_diff_start(previous_line, current_line)
        if diff_start <= 0:
            output_chunks.append(f"\x1b[{index + 1};1H{current_line}\x1b[K")
            continue
        col = visible_cell_width(current_line[:diff_start]) + 1
        output_chunks.append(f"\x1b[{index + 1};{col}H{current_line[diff_start:]}\x1b[K")

    if output_chunks:
        sys.stdout.write("".join(output_chunks))
        sys.stdout.flush()

    LAST_RENDER_LINES = combined_lines


def reset_render_cache() -> None:
    """Force the next render call to redraw the full frame."""
    global LAST_RENDER_LINES
    LAST_RENDER_LINES = None
    KITT_SCANNER_STATE["last_monotonic"] = -1.0
    KITT_SCANNER_STATE["scanner_phase"] = 0.0
    KITT_SCANNER_STATE["last_error_ratio"] = 0.0


def _find_pulse_start(lines: Sequence[str]) -> Optional[int]:
    """Return the first Pulse band line index if present."""
    for index, line in enumerate(lines):
        if strip_ansi(line).startswith("Pulse ["):
            return index
    return None


def _find_safe_diff_start(previous_line: str, current_line: str) -> int:
    """Return a safe raw-string offset where line contents diverge."""
    max_common = min(len(previous_line), len(current_line))
    index = 0
    while index < max_common and previous_line[index] == current_line[index]:
        index += 1
    if index <= 0:
        return 0
    safe_previous = _rewind_to_escape_boundary(previous_line, index)
    safe_current = _rewind_to_escape_boundary(current_line, index)
    return min(safe_previous, safe_current)


def _rewind_to_escape_boundary(text: str, index: int) -> int:
    """Rewind index if it points inside an ANSI escape sequence."""
    if index <= 0 or index > len(text):
        return max(0, min(index, len(text)))
    esc_index = text.rfind("\x1b", 0, index)
    if esc_index == -1:
        return index
    sequence_end = text.find("m", esc_index, index)
    if sequence_end == -1:
        return esc_index
    return index


# ============================================================================
# Formatting Functions
# ============================================================================


def format_timezone_label(now_utc: datetime, display_tz: tzinfo) -> str:
    """Format the timezone label for display."""
    tzinfo = now_utc.astimezone(display_tz).tzinfo
    tz_name = tzinfo.tzname(now_utc) if tzinfo else None
    if tz_name:
        return tz_name
    tz_key = getattr(display_tz, "key", None)
    if isinstance(tz_key, str):
        return tz_key
    return "UTC"


def format_timestamp(now_utc: datetime, display_tz: tzinfo) -> str:
    """Format a timestamp with timezone label."""
    timestamp = now_utc.astimezone(display_tz).strftime("%Y-%m-%d %H:%M:%S")
    tz_label = format_timezone_label(now_utc, display_tz)
    return f"{timestamp} ({tz_label})"


# ============================================================================
# Terminal Utilities
# ============================================================================


def prepare_terminal_for_exit() -> None:
    """Prepare the terminal for exit by clearing the screen area."""
    if not sys.stdout.isatty():
        return
    term_size = get_terminal_size(fallback=(80, 24))
    sys.stdout.write("\n" * term_size.lines)
    sys.stdout.flush()


def flash_screen() -> None:
    """Flash the screen with a white background for ~100ms."""
    if not sys.stdout.isatty():
        return
    # ANSI escape sequences for visual flash effect
    save_cursor = "\x1b7"  # Save cursor position
    set_white_bg = "\x1b[47m"  # White background
    set_black_fg = "\x1b[30m"  # Black foreground
    clear_screen = "\x1b[2J"  # Clear screen
    move_home = "\x1b[H"  # Move cursor to home position
    restore_cursor = "\x1b8"  # Restore cursor position
    flash_duration_seconds = 0.1  # Duration of flash effect

    # Apply white flash effect and clear screen
    sys.stdout.write(save_cursor + set_white_bg + set_black_fg + clear_screen + move_home)
    sys.stdout.flush()
    time.sleep(flash_duration_seconds)
    # Restore normal display
    sys.stdout.write(ANSI_RESET + restore_cursor)
    sys.stdout.flush()


def ring_bell() -> None:
    """Ring the terminal bell."""
    if not sys.stdout.isatty():
        return
    sys.stdout.write("\a")
    sys.stdout.flush()


def should_flash_on_fail(status: str, flash_on_fail: bool, show_help: bool) -> bool:
    """Return True when the failure flash should be displayed."""
    return status == "fail" and flash_on_fail and not show_help


# ============================================================================
# Panel Utilities
# ============================================================================


def toggle_panel_visibility(
    current_position: str,
    last_visible_position: Optional[str],
    default_position: str = "right",
) -> Tuple[str, str]:
    """Toggle panel visibility between 'none' and last visible position."""
    if current_position == "none":
        restored_position = last_visible_position or default_position
        return restored_position, restored_position
    return "none", current_position


def cycle_panel_position(current_position: str, default_position: str = "right") -> str:
    """Cycle through panel positions (left, right, top, bottom)."""
    positions = ["left", "right", "top", "bottom"]
    if current_position not in positions:
        return default_position if default_position in positions else positions[0]
    next_index = (positions.index(current_position) + 1) % len(positions)
    return positions[next_index]
