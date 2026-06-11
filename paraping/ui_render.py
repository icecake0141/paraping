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

import time  # noqa: F401  # Backward-compatible patch target for pulse animation tests.
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from paraping import ui_display_entries as _ui_display_entries
from paraping import ui_graph as _ui_graph
from paraping import ui_layout as _ui_layout
from paraping import ui_main_header as _ui_main_header
from paraping import ui_panels as _ui_panels
from paraping import ui_pulse as _ui_pulse
from paraping import ui_status as _ui_status
from paraping import ui_summary_sources as _ui_summary_sources
from paraping import ui_terminal as _ui_terminal
from paraping import ui_text as _ui_text
from paraping import ui_timeline as _ui_timeline
from paraping.ui_text import colorize_text, rjust_visible, strip_ansi

ANSI_ESCAPE_RE = _ui_text.ANSI_ESCAPE_RE
truncate_visible = _ui_text.truncate_visible
visible_len = _ui_text.visible_len
visible_cell_width = _ui_text.visible_cell_width
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
build_main_header = _ui_main_header.build_main_header
can_render_full_summary = _ui_panels.can_render_full_summary
compute_activity_indicator_width = _ui_pulse.compute_activity_indicator_width
_parse_positive_float = _ui_status._parse_positive_float
_find_safe_diff_start = _ui_terminal._find_safe_diff_start
_rewind_to_escape_boundary = _ui_terminal._rewind_to_escape_boundary
build_status_line = _ui_status.build_status_line
build_status_metrics = _ui_status.build_status_metrics
cycle_panel_position = _ui_terminal.cycle_panel_position
estimate_ping_rate = _ui_status.estimate_ping_rate
format_asn_label = _ui_display_entries.format_asn_label
format_display_name = _ui_display_entries.format_display_name
format_status_line = _ui_timeline.format_status_line
format_summary_line = _ui_panels.format_summary_line
format_timestamp = _ui_terminal.format_timestamp
format_timezone_label = _ui_terminal.format_timezone_label
flash_screen = _ui_terminal.flash_screen
get_terminal_size = _ui_terminal.get_terminal_size
host_label_status = _ui_timeline.host_label_status
latest_non_pending_status_from_timeline = _ui_timeline.latest_non_pending_status_from_timeline
latest_status_from_timeline = _ui_timeline.latest_status_from_timeline
pad_lines = _ui_panels.pad_lines
prepare_summary_sources = _ui_summary_sources.prepare_summary_sources
prepare_terminal_for_exit = _ui_terminal.prepare_terminal_for_exit
render_fullscreen_rtt_graph = _ui_graph.render_fullscreen_rtt_graph
render_help_view = _ui_panels.render_help_view
render_kitt_bottom_band = _ui_pulse.render_kitt_bottom_band
render_pulse_panel = _ui_pulse.render_pulse_panel
render_status_box = _ui_panels.render_status_box
render_summary_view = _ui_panels.render_summary_view
_summary_render_width = _ui_layout.summary_render_width
render_terminal_frame = _ui_terminal.render_terminal_frame
ring_bell = _ui_terminal.ring_bell
resolve_display_name = _ui_display_entries.resolve_display_name
resolve_group_header_lines = _ui_display_entries.resolve_group_header_lines
resolve_host_label_status = _ui_timeline.resolve_host_label_status
resample_values = _ui_graph.resample_values
resolve_boxed_dimensions = _ui_panels.resolve_boxed_dimensions
should_flash_on_fail = _ui_terminal.should_flash_on_fail
should_show_asn = _ui_layout.should_show_asn
status_from_symbol = _ui_timeline.status_from_symbol
toggle_panel_visibility = _ui_terminal.toggle_panel_visibility

# Display constants
ACTIVITY_INDICATOR_WIDTH = _ui_pulse.ACTIVITY_INDICATOR_WIDTH
ACTIVITY_INDICATOR_HEIGHT = _ui_pulse.ACTIVITY_INDICATOR_HEIGHT
ACTIVITY_INDICATOR_SPEED_HZ = _ui_pulse.ACTIVITY_INDICATOR_SPEED_HZ
STATUS_METRICS_SEPARATOR = _ui_status.STATUS_METRICS_SEPARATOR
STATUS_METRICS_TEMPLATE = _ui_status.STATUS_METRICS_TEMPLATE

# Global state for rendering
LAST_RENDER_LINES: Optional[List[str]] = None
KITT_SCANNER_STATE = _ui_pulse.KITT_SCANNER_STATE


@dataclass(frozen=True)
class DisplayGeometry:
    """Resolved terminal and panel dimensions for one display frame."""

    term_width: int
    term_height: int
    panel_height: int
    status_box_height: int
    main_width: int
    main_height: int
    summary_width: int
    summary_height: int
    pulse_width: int
    resolved_position: str
    resolved_pulse_position: str

    @classmethod
    def resolve(
        cls,
        panel_position: str,
        pulse_position: str,
        *,
        kitt_mode_enabled: bool,
        min_main_height: int,
    ) -> "DisplayGeometry":
        """Resolve terminal, summary, main, and Pulse panel dimensions."""
        term_size = get_terminal_size(fallback=(80, 24))
        term_width = term_size.columns
        term_height = term_size.lines
        status_box_height = 3 if term_height >= 4 and term_width >= 2 else 1
        panel_height = max(1, term_height - status_box_height)
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
        return cls(
            term_width=term_width,
            term_height=term_height,
            panel_height=panel_height,
            status_box_height=status_box_height,
            main_width=main_width,
            main_height=main_height,
            summary_width=summary_width,
            summary_height=summary_height,
            pulse_width=pulse_width,
            resolved_position=resolved_position,
            resolved_pulse_position=resolved_pulse_position,
        )

    def with_summary_height(self, summary_height: int, *, min_main_height: int, gap_size: int) -> "DisplayGeometry":
        """Return geometry adjusted for a top/bottom summary panel height."""
        return DisplayGeometry(
            term_width=self.term_width,
            term_height=self.term_height,
            panel_height=self.panel_height,
            status_box_height=self.status_box_height,
            main_width=self.main_width,
            main_height=max(min_main_height, self.panel_height - summary_height - gap_size),
            summary_width=self.summary_width,
            summary_height=summary_height,
            pulse_width=self.pulse_width,
            resolved_position=self.resolved_position,
            resolved_pulse_position=self.resolved_pulse_position,
        )


# ============================================================================
# Color/Timeline Building Functions
# ============================================================================


# ============================================================================
# Layout/Geometry Functions
# ============================================================================


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
    min_main_height = 5
    gap_size = 1
    use_panel_boxes = True
    geometry = DisplayGeometry.resolve(
        panel_position,
        pulse_position,
        kitt_mode_enabled=pulse_position != "none",
        min_main_height=min_main_height,
    )

    include_asn = should_show_asn(host_infos, mode_label, show_asn, geometry.term_width, asn_width=asn_width)
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
    summary_source = prepare_summary_sources(
        host_infos,
        display_entries,
        display_names,
        buffers,
        stats,
        symbols,
        summary_scope,
        group_by,
    ).summary_source
    if geometry.resolved_position in ("top", "bottom"):
        summary_render_width = _summary_render_width(geometry.summary_width, use_panel_boxes)
        summary_all = can_render_full_summary(summary_source, summary_render_width)
        content_height, minimal_height = compute_summary_height_bounds(
            summary_source,
            summary_mode,
            summary_all,
            geometry.summary_width,
            boxed=use_panel_boxes,
        )
        max_summary_height = max(0, geometry.panel_height - min_main_height - gap_size)
        summary_height = geometry.summary_height
        summary_height = min(summary_height, content_height, max_summary_height)
        summary_height = max(summary_height, min(minimal_height, max_summary_height))
        geometry = geometry.with_summary_height(summary_height, min_main_height=min_main_height, gap_size=gap_size)
    host_labels = [entry[1] for entry in display_entries]
    if not host_labels:
        host_labels = [info["alias"] for info in host_infos]
    _, _, _, visible_hosts = compute_main_layout(host_labels, geometry.main_width, geometry.main_height, header_lines)
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
    header = build_main_header(
        width,
        mode_label,
        display_mode,
        paused,
        dormant,
        timestamp,
        now_utc,
        kitt_mode_enabled=kitt_mode_enabled,
    )
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
    min_main_height = 5
    gap_size = 1
    use_panel_boxes = True
    geometry = DisplayGeometry.resolve(
        panel_position,
        pulse_position,
        kitt_mode_enabled=kitt_mode_enabled,
        min_main_height=min_main_height,
    )

    include_asn = should_show_asn(host_infos, mode_label, show_asn, geometry.term_width, asn_width=asn_width)
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
    summary_sources = prepare_summary_sources(
        host_infos,
        display_entries,
        display_names,
        buffers,
        stats,
        symbols,
        summary_scope,
        group_by,
    )
    active_host_infos = summary_sources.active_host_infos
    host_group_labels = summary_sources.host_group_labels
    host_tree_labels = summary_sources.host_tree_labels
    ordered_host_ids = summary_sources.ordered_host_ids
    group_summary_data = summary_sources.group_summary_data
    summary_source = summary_sources.summary_source
    if not summary_fullscreen and geometry.resolved_position in ("top", "bottom") and geometry.summary_height > 0:
        summary_render_width = _summary_render_width(geometry.summary_width, use_panel_boxes)
        summary_all_for_height = can_render_full_summary(summary_source, summary_render_width)
        content_height, minimal_height = compute_summary_height_bounds(
            summary_source,
            summary_mode,
            summary_all_for_height,
            geometry.summary_width,
            boxed=use_panel_boxes,
        )
        max_summary_height = max(0, geometry.panel_height - min_main_height - gap_size)
        summary_height = geometry.summary_height
        summary_height = min(summary_height, content_height, max_summary_height)
        summary_height = max(summary_height, min(minimal_height, max_summary_height))
        geometry = geometry.with_summary_height(summary_height, min_main_height=min_main_height, gap_size=gap_size)
    group_header_lines = build_group_header_line_map(active_host_infos, ordered_host_ids, group_by, group_summary_data)
    kitt_total_hosts = summary_sources.kitt_total_hosts
    kitt_error_hosts = summary_sources.kitt_error_hosts
    summary_all = False
    main_lines = []
    summary_lines = []
    if summary_fullscreen:
        summary_all = can_render_full_summary(summary_source, geometry.term_width)
        summary_lines = render_summary_view(
            summary_source,
            geometry.term_width,
            geometry.panel_height,
            summary_mode,
            prefer_all=summary_all,
            boxed=use_panel_boxes,
        )
    else:
        main_lines = render_main_view(
            display_entries,
            buffers,
            symbols,
            geometry.main_width,
            geometry.main_height,
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
        summary_render_width = _summary_render_width(geometry.summary_width, use_panel_boxes)
        summary_all = geometry.resolved_position in ("top", "bottom") and can_render_full_summary(
            summary_source, summary_render_width
        )
        summary_lines = render_summary_view(
            summary_source,
            geometry.summary_width,
            geometry.summary_height,
            summary_mode,
            prefer_all=summary_all,
            boxed=use_panel_boxes,
        )

    gap = " "
    combined_lines = []
    if show_help:
        combined_lines = render_help_view(geometry.term_width, geometry.panel_height, boxed=use_panel_boxes)
    elif summary_fullscreen:
        combined_lines = summary_lines
    else:
        pulse_lines: List[str] = []
        if kitt_mode_enabled and geometry.resolved_pulse_position in ("left", "right") and geometry.pulse_width > 0:
            pulse_lines = render_pulse_panel(
                geometry.pulse_width,
                geometry.main_height,
                kitt_style,
                now_utc,
                use_color,
                error_hosts=kitt_error_hosts,
                total_hosts=kitt_total_hosts,
            )
        elif kitt_mode_enabled and geometry.resolved_pulse_position in ("top", "bottom"):
            main_lines, pulse_height = extract_trailing_pulse_space(main_lines, boxed=use_panel_boxes)
            if pulse_height >= 3:
                pulse_lines = render_pulse_panel(
                    geometry.main_width,
                    pulse_height,
                    kitt_style,
                    now_utc,
                    use_color,
                    error_hosts=kitt_error_hosts,
                    total_hosts=kitt_total_hosts,
                )

        if geometry.resolved_position in ("left", "right"):
            for main_line, summary_line in zip(main_lines, summary_lines):
                if geometry.resolved_position == "left":
                    combined_lines.append(f"{summary_line}{gap}{main_line}")
                else:
                    combined_lines.append(f"{main_line}{gap}{summary_line}")
        elif geometry.resolved_position == "top":
            combined_lines = summary_lines + [""] + main_lines
        elif geometry.resolved_position == "bottom":
            combined_lines = main_lines + [""] + summary_lines
        else:
            combined_lines = main_lines

        if pulse_lines:
            if geometry.resolved_pulse_position in ("left", "right"):
                merged_lines = []
                for combined_line, pulse_line in zip(combined_lines, pulse_lines):
                    if geometry.resolved_pulse_position == "left":
                        merged_lines.append(f"{pulse_line}{gap}{combined_line}")
                    else:
                        merged_lines.append(f"{combined_line}{gap}{pulse_line}")
                combined_lines = merged_lines
            elif geometry.resolved_pulse_position == "top":
                combined_lines = pulse_lines + [""] + combined_lines
            elif geometry.resolved_pulse_position == "bottom":
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
    if geometry.panel_height > 0:
        combined_lines = pad_lines(combined_lines, geometry.term_width, geometry.panel_height)

    if geometry.status_box_height == 1:
        status_lines = [status_line[: geometry.term_width].ljust(geometry.term_width)]
    else:
        status_lines = render_status_box(status_line, geometry.term_width)

    if geometry.panel_height <= 0:
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

    LAST_RENDER_LINES = render_terminal_frame(LAST_RENDER_LINES, combined_lines)


def reset_render_cache() -> None:
    """Force the next render call to redraw the full frame."""
    global LAST_RENDER_LINES
    LAST_RENDER_LINES = None
    KITT_SCANNER_STATE["last_monotonic"] = -1.0
    KITT_SCANNER_STATE["scanner_phase"] = 0.0
    KITT_SCANNER_STATE["last_error_ratio"] = 0.0
