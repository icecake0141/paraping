#!/usr/bin/env python3
# Copyright 2026 icecake0141
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

"""Graph helpers for ParaPing terminal rendering."""

from typing import List, Optional, Sequence

from paraping.ui_panels import pad_lines


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


def build_time_axis(
    timeline_width: int,
    label_width: int,
    interval_seconds: float = 1.0,
    label_period_seconds: float = 10.0,
) -> str:
    """
    Build a time axis string for the timeline/sparkline view.

    The axis shows time labels (e.g., "30", "20", "10") at regular intervals,
    representing seconds-ago values that decrease from left to right.
    """
    if timeline_width <= 0:
        return ""

    axis_chars = [" "] * timeline_width
    for i in range(timeline_width):
        time_from_right = (timeline_width - 1 - i) * interval_seconds
        if i > 0 and abs(time_from_right % label_period_seconds) < interval_seconds and time_from_right >= interval_seconds:
            label_value = int(time_from_right)
            label_str = str(label_value)

            if i + len(label_str) <= timeline_width:
                overlap = False
                start_index = max(0, i - 1)
                end_index = min(timeline_width, i + len(label_str) + 1)
                for j in range(start_index, end_index):
                    if axis_chars[j] != " ":
                        overlap = True
                        break

                if not overlap:
                    for j, char in enumerate(label_str):
                        if i + j < timeline_width:
                            axis_chars[i + j] = char

    axis_timeline = "".join(axis_chars)
    return f"{' ' * label_width} | {axis_timeline}"


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

    status_line = "ESC: back | v: toggle graph | x: select host"

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
