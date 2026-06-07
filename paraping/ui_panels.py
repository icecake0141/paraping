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

"""Reusable terminal panels for ParaPing UI rendering."""

import textwrap
from typing import Any, Dict, List, Sequence, Tuple

from paraping.keymap import build_help_items
from paraping.stats import build_summary_all_suffix, build_summary_suffix
from paraping.ui_text import pad_visible


def pad_lines(lines: Sequence[str], width: int, height: int) -> List[str]:
    """Pad lines to fill the specified width and height."""
    padded = [pad_visible(line, width) for line in lines[:height]]
    while len(padded) < height:
        padded.append("".ljust(width))
    return padded


def resolve_boxed_dimensions(width: int, height: int, boxed: bool) -> Tuple[int, int, bool]:
    """Resolve dimensions for boxed content."""
    if not boxed or width < 2 or height < 3:
        return width, height, False
    return width - 2, height - 2, True


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

    indent = "  " * max(0, int(entry.get("indent_level", 0)))
    host_text = f"{indent}{entry['host']}"
    available_for_host = width - len(status_suffix)
    if available_for_host > 0:
        host_display = host_text[:available_for_host]
    else:
        host_display = host_text

    full_line = f"{host_display}{status_suffix}"
    return full_line[:width]


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
    render_width, render_height, can_box = resolve_boxed_dimensions(width, height, boxed)
    header_lines = [
        "ParaPing - Help",
        "-" * render_width,
    ]
    help_items = build_help_items()

    def _wrap_items(items: Sequence[str], line_width: int) -> List[str]:
        wrapped: List[str] = []
        for item in items:
            chunks = textwrap.wrap(
                item,
                width=max(1, line_width),
                break_long_words=False,
                break_on_hyphens=False,
                subsequent_indent="    ",
            )
            wrapped.extend(chunks or [""])
        return wrapped

    lines = list(header_lines)
    body_height = max(0, render_height - len(header_lines))
    single_column = _wrap_items(help_items, render_width)
    if len(single_column) > body_height and render_width >= 72:
        gap = 3
        col_width = max(1, (render_width - gap) // 2)
        split_at = (len(help_items) + 1) // 2
        left_items = help_items[:split_at]
        right_items = help_items[split_at:]
        left_lines = _wrap_items(left_items, col_width)
        right_lines = _wrap_items(right_items, col_width)
        for row_index in range(max(len(left_lines), len(right_lines))):
            left = left_lines[row_index] if row_index < len(left_lines) else ""
            right = right_lines[row_index] if row_index < len(right_lines) else ""
            lines.append(f"{left.ljust(col_width)}{' ' * gap}{right}".rstrip())
    else:
        lines.extend(single_column)

    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


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
