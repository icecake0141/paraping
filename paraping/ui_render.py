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
import re
import sys
import time
from collections import deque
from datetime import datetime, timezone, tzinfo
from typing import Any, Dict, List, Optional, Sequence, Tuple

from paraping.stats import (
    build_summary_all_suffix,
    build_summary_suffix,
    compute_fail_streak,
    compute_summary_data,
    latest_rtt_value,
)

# ANSI and display constants (imported from main)
ANSI_RESET = "\x1b[0m"
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
STATUS_COLORS = {
    "success": "\x1b[37m",  # White
    "slow": "\x1b[33m",  # Yellow
    "fail": "\x1b[31m",  # Red
    "pending": "\x1b[90m",  # Dark gray (bright black)
}
ACTIVITY_INDICATOR_WIDTH = 10
ACTIVITY_INDICATOR_EXPANDED_WIDTH = 20
ACTIVITY_INDICATOR_HEIGHT = 4
ACTIVITY_INDICATOR_SPEED_HZ = 8
STATUS_METRICS_SEPARATOR = " | "
STATUS_METRICS_TEMPLATE = STATUS_METRICS_SEPARATOR.join(
    ["Hosts: {hosts}", "Success: {success}", "Errors: {errors}", "Rate: {rate}"]
)

# Global state for rendering
LAST_RENDER_LINES: Optional[List[str]] = None


# ============================================================================
# ANSI/Text Utility Functions
# ============================================================================


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return ANSI_ESCAPE_RE.sub("", text)


def visible_len(text: str) -> int:
    """Get the visible length of text (excluding ANSI codes)."""
    return len(strip_ansi(text))


def truncate_visible(text: str, width: int) -> Tuple[str, int]:
    """
    Truncate text to a visible width, preserving ANSI codes.

    Returns:
        Tuple of (truncated_text, visible_count)
    """
    result = []
    visible_count = 0
    index = 0
    while index < len(text) and visible_count < width:
        if text[index] == "\x1b":
            match = ANSI_ESCAPE_RE.match(text, index)
            if match:
                result.append(match.group(0))
                index = match.end()
                continue
        result.append(text[index])
        index += 1
        visible_count += 1
    truncated = "".join(result)
    if "\x1b[" in truncated and not truncated.endswith(ANSI_RESET):
        truncated += ANSI_RESET
    return truncated, visible_count


def pad_visible(text: str, width: int) -> str:
    """Pad text to a visible width, preserving ANSI codes."""
    truncated, visible_count = truncate_visible(text, width)
    if visible_count < width:
        truncated += " " * (width - visible_count)
    return truncated


def rjust_visible(text: str, width: int) -> str:
    """Right-justify text to a visible width, preserving ANSI codes."""
    padding = width - visible_len(text)
    if padding <= 0:
        return text
    return f"{' ' * padding}{text}"


def colorize_text(text: str, status: Optional[str], use_color: bool) -> str:
    """Apply color to text based on status."""
    if not use_color or not status:
        return text
    color = STATUS_COLORS.get(status)
    if not color:
        return text
    return f"{color}{text}{ANSI_RESET}"


def status_from_symbol(symbol: str, symbols: Dict[str, str]) -> Optional[str]:
    """Get status name from symbol character."""
    for status, status_symbol in symbols.items():
        if symbol == status_symbol:
            return status
    return None


def latest_status_from_timeline(timeline: Sequence[str], symbols: Dict[str, str]) -> Optional[str]:
    """Get the latest status from a timeline."""
    if not timeline:
        return None
    return status_from_symbol(timeline[-1], symbols)


# ============================================================================
# Color/Timeline Building Functions
# ============================================================================


def build_colored_timeline(timeline: Sequence[str], symbols: Dict[str, str], use_color: bool) -> str:
    """Build a colored timeline string from symbols."""
    return "".join(colorize_text(symbol, status_from_symbol(symbol, symbols), use_color) for symbol in timeline)


def build_colored_sparkline(
    sparkline: str,
    status_symbols: Sequence[str],
    symbols: Dict[str, str],
    use_color: bool,
) -> str:
    """Build a colored sparkline from characters and status symbols."""
    if not use_color:
        return sparkline
    colored = []
    for char, symbol in zip(sparkline, status_symbols):
        status = status_from_symbol(symbol, symbols)
        colored.append(colorize_text(char, status, use_color))
    return "".join(colored)


def build_activity_indicator(
    now_utc: datetime,
    width: int = ACTIVITY_INDICATOR_WIDTH,
    max_height: int = ACTIVITY_INDICATOR_HEIGHT,
    speed_hz: int = ACTIVITY_INDICATOR_SPEED_HZ,
) -> str:
    """Build an animated activity indicator sparkline."""
    if width <= 0:
        return ""
    tick = int(now_utc.timestamp() * speed_hz)
    span = max(1, width - 1)
    cycle = span * 2
    position = tick % cycle
    if position > span:
        position = cycle - position
    spark_chars = "▁▂▃▄▅▆▇█"
    peak = min(max_height, len(spark_chars) - 1)
    levels = []
    for index in range(width):
        height = max(0, peak - abs(index - position))
        levels.append(spark_chars[height] if height > 0 else spark_chars[0])
    return "".join(levels)


def compute_activity_indicator_width(
    panel_width: int,
    header_text: str,
    default_width: int = ACTIVITY_INDICATOR_WIDTH,
    expanded_width: int = ACTIVITY_INDICATOR_EXPANDED_WIDTH,
) -> int:
    """Compute the width for the activity indicator based on available space."""
    if panel_width <= 0:
        return 0
    remaining = panel_width - visible_len(header_text) - 1
    if remaining <= 0:
        return 0
    if remaining >= expanded_width:
        return expanded_width
    if remaining >= default_width:
        return default_width
    return remaining


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


def compute_main_layout(
    host_labels: Sequence[str], width: int, height: int, header_lines: int = 2
) -> Tuple[int, int, int, int]:
    """Compute the main layout dimensions for the display."""
    max_host_len = max((len(host) for host in host_labels), default=4)
    label_width = min(max_host_len, max(10, width // 3))
    timeline_width = max(1, width - label_width - 3)
    visible_hosts = max(1, height - header_lines)

    return width, label_width, timeline_width, visible_hosts


def compute_panel_sizes(
    term_width: int,
    term_height: int,
    panel_position: str,
    min_panel_width: int = 30,
    min_panel_height: int = 5,
    min_main_width: int = 20,
    min_main_height: int = 5,
    gap: int = 1,
) -> Tuple[int, int, int, int, str]:
    """Compute the sizes for main and summary panels based on position."""
    if panel_position == "none":
        return term_width, term_height, 0, 0, "none"

    if term_width < min_main_width or term_height < min_main_height:
        return term_width, term_height, 0, 0, "none"

    if panel_position in ("left", "right"):
        summary_width = max(min_panel_width, term_width // 4)
        main_width = term_width - summary_width - gap
        if main_width < min_main_width or summary_width < min_panel_width:
            return term_width, term_height, 0, 0, "none"
        return main_width, term_height, summary_width, term_height, panel_position

    if panel_position in ("top", "bottom"):
        summary_height = max(min_panel_height, term_height // 4)
        main_height = term_height - summary_height - gap
        if main_height < min_main_height or summary_height < min_panel_height:
            return term_width, term_height, 0, 0, "none"
        return term_width, main_height, term_width, summary_height, panel_position

    return term_width, term_height, 0, 0, "none"


def resolve_boxed_dimensions(width: int, height: int, boxed: bool) -> Tuple[int, int, bool]:
    """Resolve dimensions for boxed content."""
    if not boxed or width < 2 or height < 3:
        return width, height, False
    return width - 2, height - 2, True


def should_show_asn(
    host_infos: Sequence[Dict[str, Any]],
    mode: str,
    show_asn: bool,
    term_width: int,
    min_timeline_width: int = 10,
    asn_width: int = 8,
) -> bool:
    """Determine if ASN should be shown based on available space."""
    if not show_asn:
        return False
    base_label_width = max((len(resolve_display_name(info, mode)) for info in host_infos), default=0)
    labels = [format_display_name(info, mode, True, asn_width, base_label_width) for info in host_infos]
    if not labels:
        return False
    label_width = max(len(label) for label in labels)
    timeline_width = term_width - label_width - 3
    return timeline_width >= min_timeline_width


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
    asn_width: int = 8,
    header_lines: int = 2,
) -> Tuple[int, int, int]:
    """Compute the scroll bounds for the host list."""
    term_size = get_terminal_size(fallback=(80, 24))
    term_width = term_size.columns
    term_height = term_size.lines

    include_asn = should_show_asn(host_infos, mode_label, show_asn, term_width, asn_width=asn_width)
    display_names = build_display_names(host_infos, mode_label, include_asn, asn_width)
    main_width, main_height, _, _, _ = compute_panel_sizes(term_width, term_height, panel_position)
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
    _, _, _, visible_hosts = compute_main_layout(host_labels, main_width, main_height, header_lines)
    total_hosts = len(display_entries)
    max_offset = max(0, total_hosts - visible_hosts)
    return max_offset, visible_hosts, total_hosts


# ============================================================================
# Box/Padding Utilities
# ============================================================================


def pad_lines(lines: Sequence[str], width: int, height: int) -> List[str]:
    """Pad lines to fill the specified width and height."""
    padded = [pad_visible(line, width) for line in lines[:height]]
    while len(padded) < height:
        padded.append("".ljust(width))
    return padded


def box_lines(lines: Sequence[str], width: int, height: int) -> List[str]:
    """Draw a box around lines."""
    inner_width, inner_height, can_box = resolve_boxed_dimensions(width, height, True)
    if not can_box:
        return pad_lines(lines, width, height)
    inner_lines = pad_lines(lines, inner_width, inner_height)
    border = "-" * inner_width
    boxed = [f"+{border}+"]
    boxed.extend(f"|{line}|" for line in inner_lines)
    boxed.append(f"+{border}+")
    return boxed


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
# Graph Utilities
# ============================================================================


def build_sparkline(rtt_values: Sequence[Optional[float]], status_symbols: Sequence[str], fail_symbol: str) -> str:
    """Build a sparkline from RTT values."""
    spark_chars = "▁▂▃▄▅▆▇█"
    if rtt_values:
        numeric_values = [value for value in rtt_values if value is not None]
    else:
        numeric_values = []

    if numeric_values:
        min_val = min(numeric_values)
        max_val = max(numeric_values)
        span = max_val - min_val
        if span == 0:
            span = 1
        indices = []
        for value in rtt_values:
            if value is None:
                indices.append(0)
            else:
                idx = round((value - min_val) / span * (len(spark_chars) - 1))
                indices.append(max(0, min(len(spark_chars) - 1, idx)))
    else:
        indices = []
        for symbol in status_symbols:
            if symbol == fail_symbol:
                indices.append(0)
            else:
                indices.append(len(spark_chars) - 1)

    return "".join(spark_chars[idx] for idx in indices)


def build_ascii_graph(values: Sequence[Optional[float]], width: int, height: int, style: str = "line") -> List[str]:
    """Build an ASCII graph from values."""
    if width <= 0 or height <= 0:
        return []

    trimmed_values: List[Optional[float]] = list(values[-width:]) if values else []
    if len(trimmed_values) < width:
        padding: List[Optional[float]] = [None] * (width - len(trimmed_values))
        trimmed_values = padding + trimmed_values

    numeric_values = [value for value in trimmed_values if value is not None]
    if not numeric_values:
        return [" " * width for _ in range(height)]

    min_val = min(numeric_values)
    max_val = max(numeric_values)
    span = max_val - min_val
    if span == 0:
        span = 1.0

    grid = [[" " for _ in range(width)] for _ in range(height)]
    for x, value in enumerate(trimmed_values):
        if value is None:
            grid[height - 1][x] = "x"
            continue
        scaled = int(round((value - min_val) / span * (height - 1)))
        y = height - 1 - scaled
        if style == "bar":
            for y_fill in range(y, height):
                grid[y_fill][x] = "#"
        else:
            grid[y][x] = "*"

    return ["".join(row) for row in grid]


def resample_values(values: Sequence[Optional[float]], target_width: int) -> List[Optional[float]]:
    """Resample values to fit a target width."""
    if target_width <= 0:
        return []
    if not values:
        return [None] * target_width
    if target_width == 1:
        return [values[-1]]
    if len(values) == 1:
        return [values[0]] * target_width
    if len(values) == target_width:
        return list(values)

    last_index = len(values) - 1
    return [values[round(i * last_index / (target_width - 1))] for i in range(target_width)]


# ============================================================================
# Display Building Functions
# ============================================================================


def resolve_display_name(host_info: Dict[str, Any], mode: str) -> str:
    """Resolve the display name for a host based on mode."""
    if mode == "ip":
        return str(host_info["ip"])
    if mode == "rdns":
        if host_info.get("rdns_pending"):
            return "resolving..."
        rdns_value = host_info.get("rdns")
        return str(rdns_value) if rdns_value is not None else str(host_info["ip"])
    if mode == "alias":
        alias_value = host_info.get("alias") or host_info.get("host")
        return str(alias_value) if alias_value is not None else str(host_info["ip"])
    return str(host_info["ip"])


def format_asn_label(host_info: Dict[str, Any], asn_width: int) -> str:
    """Format the ASN label for display."""
    if host_info.get("asn_pending"):
        label = "resolving..."
    else:
        asn_value = host_info.get("asn")
        label = str(asn_value) if asn_value is not None else ""
    return f"{label[:asn_width]:<{asn_width}}"


def format_display_name(
    host_info: Dict[str, Any],
    mode: str,
    include_asn: bool,
    asn_width: int,
    base_label_width: int = 0,
) -> str:
    """Format the complete display name including optional ASN."""
    base_label = resolve_display_name(host_info, mode)
    if not include_asn:
        return base_label
    padded_label = f"{base_label:<{base_label_width}}" if base_label_width else base_label
    asn_label = format_asn_label(host_info, asn_width)
    return f"{padded_label} {asn_label}"


def build_display_names(host_infos: Sequence[Dict[str, Any]], mode: str, include_asn: bool, asn_width: int) -> Dict[int, str]:
    """Build display names for all hosts."""
    base_label_width = 0
    if include_asn:
        base_label_width = max((len(resolve_display_name(info, mode)) for info in host_infos), default=0)
    return {info["id"]: format_display_name(info, mode, include_asn, asn_width, base_label_width) for info in host_infos}


def build_display_entries(
    host_infos: Sequence[Dict[str, Any]],
    display_names: Dict[int, str],
    buffers: Dict[int, Dict[str, Any]],
    stats: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    sort_mode: str,
    filter_mode: str,
    slow_threshold: float,
) -> List[Tuple[int, str]]:
    """Build and sort display entries based on current filter and sort modes."""
    entries = []
    for info in host_infos:
        host_id = info["id"]
        timeline = buffers[host_id]["timeline"]
        latest_rtt = latest_rtt_value(buffers[host_id]["rtt_history"])
        fail_streak = compute_fail_streak(timeline, symbols["fail"])
        fail_count = stats[host_id]["fail"]

        include = True
        if filter_mode == "failures":
            include = fail_count > 0
        elif filter_mode == "latency":
            include = latest_rtt is not None and latest_rtt >= slow_threshold

        if include:
            entries.append(
                {
                    "host_id": host_id,
                    "label": display_names.get(host_id, info["alias"]),
                    "fail_count": fail_count,
                    "fail_streak": fail_streak,
                    "latest_rtt": latest_rtt,
                }
            )

    if sort_mode == "config":
        # Sort by host_id to maintain configuration file order
        entries.sort(key=lambda item: item["host_id"])
    elif sort_mode == "failures":
        entries.sort(key=lambda item: (item["fail_count"], item["label"]), reverse=True)
    elif sort_mode == "streak":
        entries.sort(key=lambda item: (item["fail_streak"], item["label"]), reverse=True)
    elif sort_mode == "latency":
        entries.sort(
            key=lambda item: ((item["latest_rtt"] or -1.0), item["label"]),
            reverse=True,
        )
    elif sort_mode == "host":
        entries.sort(key=lambda item: item["label"])

    return [(entry["host_id"], entry["label"]) for entry in entries]


def can_render_full_summary(summary_data: Sequence[Dict[str, Any]], width: int) -> bool:
    """Check if we can render the full summary with all information."""
    if not summary_data:
        return False
    max_suffix_len = max(len(build_summary_all_suffix(entry)) for entry in summary_data)
    return width >= max_suffix_len + 1


def format_summary_line(entry: Dict[str, Any], width: int, summary_mode: str, prefer_all: bool = False) -> str:
    """Format a single summary line."""
    status_suffix = None
    if prefer_all:
        all_suffix = build_summary_all_suffix(entry)
        if width >= len(all_suffix) + 1:
            status_suffix = all_suffix
    if status_suffix is None:
        status_suffix = build_summary_suffix(entry, summary_mode)

    available_for_host = width - len(status_suffix)
    if available_for_host > 0:
        host_display = entry["host"][:available_for_host]
    else:
        host_display = entry["host"]

    full_line = f"{host_display}{status_suffix}"
    return full_line[:width]


def build_time_axis(
    timeline_width: int,
    label_width: int,
    interval_seconds: float = 1.0,
    label_period_seconds: float = 10.0,
) -> str:
    """
    Build a time axis string for the timeline/sparkline view.

    The axis shows time labels (e.g., "10", "20", "30") at regular intervals,
    representing seconds from the leftmost (oldest) to rightmost (newest) column.

    Args:
        timeline_width: Width of the timeline area in characters
        label_width: Width of the label column (for alignment with timeline)
        interval_seconds: Ping interval in seconds (time per column)
        label_period_seconds: Time between axis labels in seconds

    Returns:
        Formatted axis string with padding and labels
    """
    if timeline_width <= 0:
        return ""

    # Build the axis from left to right with increasing time values
    # The leftmost column represents the oldest time, rightmost is newest (now)
    axis_chars = [" "] * timeline_width

    # Place labels at regular intervals, checking for overlaps
    for i in range(timeline_width):
        # Time from left (for label purposes)
        time_from_left = i * interval_seconds

        # Check if this position should have a label
        # We want labels at 0, label_period, 2*label_period, etc. from the left
        if i > 0 and abs(time_from_left % label_period_seconds) < interval_seconds:
            label_value = int(time_from_left)
            label_str = str(label_value)

            # Check if label fits and doesn't overlap with existing labels
            if i + len(label_str) <= timeline_width:
                # Check for overlap: ensure all positions (plus a one-char gap) are empty
                overlap = False
                start_index = max(0, i - 1)
                end_index = min(timeline_width, i + len(label_str) + 1)
                for j in range(start_index, end_index):
                    if axis_chars[j] != " ":
                        overlap = True
                        break

                # Place label only if no overlap
                if not overlap:
                    for j, char in enumerate(label_str):
                        if i + j < timeline_width:
                            axis_chars[i + j] = char

    axis_timeline = "".join(axis_chars)
    # Add label padding and separator to match timeline format
    return f"{' ' * label_width} | {axis_timeline}"


def format_status_line(host: str, timeline: str, label_width: int) -> str:
    """Format a status line with host and timeline."""
    return f"{pad_visible(host, label_width)} | {timeline}"


def _parse_positive_float(value: Optional[str]) -> Optional[float]:
    """Parse a strictly positive float from a string, returning None if invalid.

    Handles None or empty values and invalid string conversions from environment variables.
    """
    if not value:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def estimate_ping_rate(host_count: int, interval_seconds: float) -> Optional[float]:
    """Estimate the ping rate using environment variables when provided.

    Returns None when the interval value is invalid.
    """
    rate_env = _parse_positive_float(os.getenv("PARAPING_PING_RATE"))
    if rate_env is not None:
        return rate_env
    # Allow PARAPING_PING_INTERVAL to override the provided interval for rate estimation.
    interval_env = _parse_positive_float(os.getenv("PARAPING_PING_INTERVAL"))
    interval_value = interval_env if interval_env is not None else interval_seconds
    # Defensive guard in case an unexpected non-positive interval is provided.
    if interval_value <= 0:
        return None
    return host_count / interval_value


def build_status_metrics(
    host_infos: Optional[Sequence[Dict[str, Any]]],
    stats: Optional[Dict[int, Dict[str, Any]]],
    interval_seconds: float = 1.0,
) -> str:
    """Build a status metrics string for hosts, counts, and estimated rate."""
    host_count = len(host_infos) if host_infos else 0
    successful_pings = 0
    error_count = 0
    stats_map = stats or {}
    for info in host_infos or []:
        stat_entry = stats_map.get(info["id"], {})
        # Slow pings still represent successful responses for aggregate success counts.
        total_successful = stat_entry.get("success", 0) + stat_entry.get("slow", 0)
        successful_pings += total_successful
        error_count += stat_entry.get("fail", 0)
    estimated_rate = estimate_ping_rate(host_count, interval_seconds)
    rate_label = f"{estimated_rate:.1f}/s" if estimated_rate is not None else "n/a"
    return STATUS_METRICS_TEMPLATE.format(
        hosts=host_count,
        success=successful_pings,
        errors=error_count,
        rate=rate_label,
    )


def build_status_line(
    sort_mode: str,
    filter_mode: str,
    summary_mode: str,
    paused: bool,
    status_message: Optional[str] = None,
    summary_all: bool = False,
    summary_fullscreen: bool = False,
    dormant: bool = False,
) -> str:
    """Build the status line showing current modes and settings."""
    sort_labels = {
        "failures": "Failure Count",
        "streak": "Failure Streak",
        "latency": "Latest Latency",
        "host": "Host Name",
    }
    filter_labels = {
        "failures": "Failures Only",
        "latency": "High Latency Only",
        "all": "All Items",
    }
    summary_labels = {
        "rates": "Rates",
        "rtt": "Avg RTT",
        "ttl": "TTL",
        "streak": "Streak",
    }
    sort_label = sort_labels.get(sort_mode, sort_mode)
    filter_label = filter_labels.get(filter_mode, filter_mode)
    summary_label = "All" if summary_all else summary_labels.get(summary_mode, summary_mode)
    status = f"Sort: {sort_label} | Filter: {filter_label} | Summary: {summary_label}"
    if summary_fullscreen:
        status += " | Summary View: Fullscreen"
    if dormant:
        status += " | DORMANT"
    elif paused:
        status += " | PAUSED"
    if status_message:
        status += f" | {status_message}"
    return status


# ============================================================================
# Rendering Functions
# ============================================================================


def render_timeline_view(
    display_entries: Sequence[Tuple[int, str]],
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
) -> List[str]:
    """Render the timeline view."""
    if width <= 0 or height <= 0:
        return []

    render_width, render_height, can_box = resolve_boxed_dimensions(width, height, boxed)
    host_labels = [entry[1] for entry in display_entries]
    # Account for time axis line when calculating visible hosts
    # header_lines + 1 for the time axis line
    render_width, label_width, timeline_width, visible_hosts = compute_main_layout(
        host_labels, render_width, render_height, header_lines + 1
    )
    max_offset = max(0, len(display_entries) - visible_hosts)
    scroll_offset = min(max(scroll_offset, 0), max_offset)
    truncated_entries = display_entries[scroll_offset : scroll_offset + visible_hosts]

    resize_buffers(buffers, timeline_width, symbols)

    lines = []
    lines.append(header)
    lines.append("".join("-" for _ in range(render_width)))
    for host, label in truncated_entries:
        timeline_symbols = list(buffers[host]["timeline"])
        timeline = build_colored_timeline(timeline_symbols, symbols, use_color)
        timeline = rjust_visible(timeline, timeline_width)
        status = latest_status_from_timeline(timeline_symbols, symbols)
        colored_label = colorize_text(label, status, use_color)
        lines.append(format_status_line(colored_label, timeline, label_width))

    # Add time axis at the bottom of the timeline area
    time_axis = build_time_axis(timeline_width, label_width, interval_seconds=interval_seconds)
    lines.append(time_axis)

    if len(display_entries) > len(truncated_entries) and len(lines) < height:
        remaining = len(display_entries) - len(truncated_entries)
        lines.append(f"... ({remaining} host(s) not shown)")

    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


def render_sparkline_view(
    display_entries: Sequence[Tuple[int, str]],
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
) -> List[str]:
    """Render the sparkline view."""
    if width <= 0 or height <= 0:
        return []

    render_width, render_height, can_box = resolve_boxed_dimensions(width, height, boxed)
    host_labels = [entry[1] for entry in display_entries]
    # Account for time axis line when calculating visible hosts
    # header_lines + 1 for the time axis line
    render_width, label_width, timeline_width, visible_hosts = compute_main_layout(
        host_labels, render_width, render_height, header_lines + 1
    )
    max_offset = max(0, len(display_entries) - visible_hosts)
    scroll_offset = min(max(scroll_offset, 0), max_offset)
    truncated_entries = display_entries[scroll_offset : scroll_offset + visible_hosts]

    resize_buffers(buffers, timeline_width, symbols)

    lines = []
    lines.append(header)
    lines.append("".join("-" for _ in range(render_width)))
    for host, label in truncated_entries:
        rtt_values = list(buffers[host]["rtt_history"])[-timeline_width:]
        status_symbols = list(buffers[host]["timeline"])[-timeline_width:]
        sparkline = build_sparkline(rtt_values, status_symbols, symbols["fail"])
        sparkline = build_colored_sparkline(sparkline, status_symbols, symbols, use_color)
        sparkline = rjust_visible(sparkline, timeline_width)
        status = latest_status_from_timeline(status_symbols, symbols)
        colored_label = colorize_text(label, status, use_color)
        lines.append(format_status_line(colored_label, sparkline, label_width))

    # Add time axis at the bottom of the sparkline area
    time_axis = build_time_axis(timeline_width, label_width, interval_seconds=interval_seconds)
    lines.append(time_axis)

    if len(display_entries) > len(truncated_entries) and len(lines) < height:
        remaining = len(display_entries) - len(truncated_entries)
        lines.append(f"... ({remaining} host(s) not shown)")

    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


def build_colored_square_timeline(timeline_symbols: Sequence[str], symbols: Dict[str, str], use_color: bool) -> str:
    """Build a colored timeline of squares from status symbols."""
    # Square view uses different colors than timeline view:
    # - Square view: green for OK (success/slow), red for fail, gray for pending
    # - Timeline view: white for success, yellow for slow, red for fail
    # Green is not in STATUS_COLORS because timeline uses white for success
    green_color = "\x1b[32m"  # Green for OK status
    gray_color = "\x1b[37m"  # Gray for pending/unknown

    squares = []
    for symbol in timeline_symbols:
        status = status_from_symbol(symbol, symbols)
        square = "■"

        # Determine square color based on status
        # OK = success or slow (green), NG = fail (red), pending = pending (gray)
        # In monochrome mode, use different symbols to distinguish statuses:
        # - fail: blank space (clearly shows failure)
        # - success/slow: solid square (shows success)
        # - pending: dash/hyphen (shows pending)
        if status == "fail":
            if use_color:
                colored_square = f"{STATUS_COLORS['fail']}{square}{ANSI_RESET}"
            else:
                colored_square = " "  # Blank for failed ping in monochrome
        elif status in ("success", "slow"):
            # success and slow both show green square (OK status)
            if use_color:
                colored_square = f"{green_color}{square}{ANSI_RESET}"
            else:
                colored_square = square  # Solid square for success in monochrome
        else:
            # pending or None status - show pending square
            if use_color:
                colored_square = f"{gray_color}{square}{ANSI_RESET}"
            else:
                colored_square = "-"  # Dash for pending in monochrome

        squares.append(colored_square)

    return "".join(squares)


def render_square_view(
    display_entries: Sequence[Tuple[int, str]],
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
) -> List[str]:
    """Render the square view as a time-series (horizontal sequence of colored squares)."""
    if width <= 0 or height <= 0:
        return []

    render_width, render_height, can_box = resolve_boxed_dimensions(width, height, boxed)
    host_labels = [entry[1] for entry in display_entries]
    # Account for time axis line when calculating visible hosts
    # header_lines + 1 for the time axis line
    render_width, label_width, timeline_width, visible_hosts = compute_main_layout(
        host_labels, render_width, render_height, header_lines + 1
    )
    max_offset = max(0, len(display_entries) - visible_hosts)
    scroll_offset = min(max(scroll_offset, 0), max_offset)
    truncated_entries = display_entries[scroll_offset : scroll_offset + visible_hosts]

    resize_buffers(buffers, timeline_width, symbols)

    lines = []
    lines.append(header)
    lines.append("".join("-" for _ in range(render_width)))

    for host, label in truncated_entries:
        timeline_symbols = list(buffers[host]["timeline"])
        # Build colored square timeline from all timeline symbols
        square_timeline = build_colored_square_timeline(timeline_symbols, symbols, use_color)
        square_timeline = rjust_visible(square_timeline, timeline_width)
        # Get the latest status for label colorization
        status = latest_status_from_timeline(timeline_symbols, symbols)
        colored_label = colorize_text(label, status, use_color)
        lines.append(format_status_line(colored_label, square_timeline, label_width))

    # Add time axis at the bottom of the square timeline area
    time_axis = build_time_axis(timeline_width, label_width, interval_seconds=interval_seconds)
    lines.append(time_axis)

    if len(display_entries) > len(truncated_entries) and len(lines) < height:
        remaining = len(display_entries) - len(truncated_entries)
        lines.append(f"... ({remaining} host(s) not shown)")

    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


def render_main_view(
    display_entries: Sequence[Tuple[int, str]],
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
) -> List[str]:
    """Render the main view (timeline, sparkline, or square)."""
    pause_label = "DORMANT" if dormant else ("PAUSED" if paused else "LIVE")
    header_base = f"ParaPing - {pause_label} results [{mode_label} | {display_mode}] {timestamp}"
    activity_indicator = ""
    if not paused:
        indicator_width = compute_activity_indicator_width(width, header_base)
        if indicator_width > 0:
            activity_indicator = build_activity_indicator(now_utc, width=indicator_width)
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
    )


def render_summary_view(
    summary_data: Sequence[Dict[str, Any]],
    width: int,
    height: int,
    summary_mode: str,
    prefer_all: bool = False,
    boxed: bool = False,
) -> List[str]:
    """Render the summary view."""
    if width <= 0 or height <= 0:
        return []

    render_width, _, can_box = resolve_boxed_dimensions(width, height, boxed)
    mode_labels = {
        "rates": "Rates",
        "rtt": "Avg RTT",
        "ttl": "TTL",
        "streak": "Streak",
    }
    allow_all = prefer_all and can_render_full_summary(summary_data, render_width)
    mode_label = "All" if allow_all else mode_labels.get(summary_mode, "Rates")
    lines = [f"Summary ({mode_label})", "-" * render_width]

    # Add legend for Rates mode explaining Snt/Rcv/Los
    # Show legend when displaying rates mode (standalone) or all mode (which includes rates)
    show_legend = (summary_mode == "rates" and not allow_all) or allow_all
    if show_legend and summary_data:
        legend = "Snt/Rcv/Los: Sent/Received/Lost packets"
        if len(legend) <= render_width:
            lines.append(legend)

    for entry in summary_data:
        lines.append(format_summary_line(entry, render_width, summary_mode, prefer_all=allow_all))

    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


def render_help_view(width: int, height: int, boxed: bool = False) -> List[str]:
    """Render the help view."""
    _, _, can_box = resolve_boxed_dimensions(width, height, boxed)
    lines = [
        "ParaPing - Help",
        "-" * width,
        "  n: cycle display mode (ip/rdns/alias)",
        "  v: toggle view (timeline/sparkline/square)",
        "  g: select host for fullscreen RTT graph",
        "  o: cycle sort (failures/streak/latency/host)",
        "  f: cycle filter (failures/latency/all)",
        "  a: toggle ASN display",
        "  m: cycle summary info (rates/rtt/ttl/streak)",
        "  c: toggle color output",
        "  b: toggle bell on ping failure",
        "  F: toggle summary fullscreen view",
        "  w/W: toggle/cycle summary panel (on/off, position)",
        "  p: pause/resume display",
        "  P: toggle Dormant Mode (pause ping + display)",
        "  s: save snapshot to file",
        "  <- / -> : navigate backward/forward in time (1 page)",
        "  up / down: scroll host list",
        "  ESC: exit fullscreen graph",
        "  H: show help (Press any key to close)",
        "  q: quit",
    ]
    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


def render_host_selection_view(
    display_entries: Sequence[Tuple[int, str]],
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
    status_line = "n/p: move | Enter: select | ESC: cancel"
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
        _host_id, label = display_entries[idx]
        prefix = "> " if idx == selected_index else "  "
        entry_label = f"{prefix}{label}"
        lines.append(entry_label[:width].ljust(width))

    if len(display_entries) > end_index:
        remaining = len(display_entries) - end_index
        lines.append(f"... ({remaining} more)".ljust(width)[:width])

    lines = pad_lines(lines, width, height)
    lines[-1] = status_line[:width].ljust(width)
    return lines


def render_fullscreen_rtt_graph(
    host_label: str,
    rtt_values: Sequence[Optional[float]],
    time_history: Sequence[Optional[float]],
    width: int,
    height: int,
    display_mode: str,
    paused: bool,
    timestamp: str,
    dormant: bool = False,
) -> List[str]:
    """Render a fullscreen RTT graph for a selected host."""
    if width <= 0 or height <= 0:
        return []

    graph_style = "bar" if display_mode == "sparkline" else "line"
    pause_label = "DORMANT" if dormant else ("PAUSED" if paused else "LIVE")
    graph_label = "Bar" if graph_style == "bar" else "Line"
    header = f"ParaPing - {pause_label} RTT Graph " f"[{host_label} | {graph_label}] {timestamp}"

    rtt_ms = [value * 1000 if value is not None else None for value in rtt_values]
    numeric_values = [value for value in rtt_ms if value is not None]
    if numeric_values:
        min_val = min(numeric_values)
        max_val = max(numeric_values)
        latest_val = numeric_values[-1]
        range_line = "RTT range (Y-axis, ms): " f"{min_val:.1f}-{max_val:.1f} | latest: {latest_val:.1f}"
    else:
        min_val = max_val = 0.0
        range_line = "RTT range (Y-axis, ms): n/a"

    status_line = "ESC: back | v: toggle graph | g: select host"

    y_tick_labels = [
        f"{max_val:.1f}",
        f"{(min_val + max_val) / 2:.1f}",
        f"{min_val:.1f}",
    ]
    y_axis_width = max(len(label) for label in y_tick_labels) if numeric_values else 1
    graph_width = max(1, width - y_axis_width - 3)

    graph_height = max(0, height - 5)
    resampled_values = resample_values(rtt_ms, graph_width)
    resampled_times = resample_values(time_history, graph_width)
    graph_lines = build_ascii_graph(resampled_values, graph_width, graph_height, style=graph_style)
    if not numeric_values and graph_height > 0:
        message = "No RTT samples yet"
        message_line = message[:graph_width].center(graph_width)
        mid = graph_height // 2
        graph_lines[mid] = message_line

    y_tick_positions = {
        0: y_tick_labels[0],
        max(0, graph_height // 2): y_tick_labels[1],
        max(0, graph_height - 1): y_tick_labels[2],
    }

    lines = [header[:width], range_line[:width], "-" * width]
    for idx, line in enumerate(graph_lines):
        label = y_tick_positions.get(idx, "")
        label_text = label.rjust(y_axis_width)
        lines.append(f"{label_text} | {line}".ljust(width)[:width])

    time_values = [value for value in resampled_times if value is not None]
    if time_values:
        oldest_time = next(value for value in resampled_times if value is not None)
        latest_time = next(value for value in reversed(resampled_times) if value is not None)
        oldest_age = max(0, int(round(latest_time - oldest_time)))
        x_axis_line = "X-axis (seconds ago, oldest→newest): " f"{oldest_age}s → 0s"
    else:
        x_axis_line = "X-axis (seconds ago): n/a"
    lines.append(x_axis_line[:width].ljust(width))
    lines = pad_lines(lines, width, height)
    lines[-1] = status_line[:width].ljust(width)
    return lines


def render_status_box(status_line: str, width: int) -> List[str]:
    """Render a status box around the status line."""
    if width <= 0:
        return []
    if width < 2:
        return [status_line[:width]]
    inner_width = width - 2
    content = pad_visible(status_line[:inner_width], inner_width)
    border = "-" * inner_width
    return [f"+{border}+", f"|{content}|", f"+{border}+"]


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
    )
    main_width, main_height, summary_width, summary_height, resolved_position = compute_panel_sizes(
        term_width,
        panel_height,
        panel_position,
        min_main_height=min_main_height,
    )
    if resolved_position in ("top", "bottom") and summary_height > 0:
        required_main_height = header_lines + len(display_entries)
        if use_panel_boxes:
            required_main_height += 2
        adjusted_main_height = max(min_main_height, min(main_height, required_main_height))
        if adjusted_main_height < main_height:
            main_height = adjusted_main_height
            summary_height = panel_height - main_height - gap_size
    summary_data = compute_summary_data(
        host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        ordered_host_ids=[host_id for host_id, _label in display_entries],
    )
    summary_all = False
    main_lines = []
    summary_lines = []
    if summary_fullscreen:
        summary_all = can_render_full_summary(summary_data, term_width)
        summary_lines = render_summary_view(
            summary_data,
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
        )
        summary_all = resolved_position in (
            "top",
            "bottom",
        ) and can_render_full_summary(summary_data, summary_width)
        summary_lines = render_summary_view(
            summary_data,
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
    elif resolved_position in ("left", "right"):
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

    status_metrics = build_status_metrics(host_infos, stats, interval_seconds=interval_seconds)
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


def render_display(
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
    output_chunks = []
    for index in range(max_lines):
        previous_line = LAST_RENDER_LINES[index] if index < len(LAST_RENDER_LINES) else None
        current_line = combined_lines[index] if index < len(combined_lines) else ""
        if previous_line == current_line and index < len(combined_lines):
            continue
        output_chunks.append(f"\x1b[{index + 1};1H\x1b[2K{current_line}")

    if output_chunks:
        sys.stdout.write("".join(output_chunks))
        sys.stdout.flush()

    LAST_RENDER_LINES = combined_lines


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
