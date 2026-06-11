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

"""Pure layout calculations for ParaPing terminal UI."""

from typing import Any, Dict, Sequence, Tuple

from paraping.types import HostInfo
from paraping.ui_display_entries import format_display_name, resolve_display_name
from paraping.ui_panels import can_render_full_summary


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


def compute_pulse_panel_sizes(
    term_width: int,
    term_height: int,
    pulse_position: str,
    min_panel_width: int = 20,
    min_panel_height: int = 3,
    min_main_width: int = 20,
    gap: int = 1,
) -> Tuple[int, int, int, int, str]:
    """Compute the main/pulse split for independent Pulse panel placement."""
    if pulse_position == "none":
        return term_width, term_height, 0, 0, "none"

    if term_width < min_main_width or term_height < min_panel_height:
        return term_width, term_height, 0, 0, "none"

    if pulse_position in ("left", "right"):
        pulse_width = max(min_panel_width, term_width // 4)
        main_width = term_width - pulse_width - gap
        if main_width < min_main_width or pulse_width < min_panel_width:
            return term_width, term_height, 0, 0, "none"
        return main_width, term_height, pulse_width, term_height, pulse_position

    if pulse_position in ("top", "bottom"):
        return term_width, term_height, term_width, 0, pulse_position

    return term_width, term_height, 0, 0, "none"


def summary_render_width(width: int, boxed: bool) -> int:
    """Compute summary render width accounting for boxed borders."""
    if width <= 0:
        return 0
    if boxed and width >= 2:
        return width - 2
    return width


def compute_summary_height_bounds(
    summary_data: Sequence[Dict[str, Any]],
    summary_mode: str,
    prefer_all: bool,
    width: int,
    boxed: bool,
) -> Tuple[int, int]:
    """Return (content_height, minimal_height) for the summary panel."""
    render_width = summary_render_width(width, boxed)
    if render_width <= 0:
        return 0, 0
    allow_all = prefer_all and can_render_full_summary(summary_data, render_width)
    show_legend = ((summary_mode == "rates" and not allow_all) or allow_all) and bool(summary_data)
    content_height = 2 + (1 if show_legend else 0) + len(summary_data)
    minimal_height = 2 + (1 if show_legend else 0) + (1 if summary_data else 0)
    if boxed and width >= 2:
        content_height += 2
        minimal_height = max(3, minimal_height + 2)
    return content_height, minimal_height


def should_show_asn(
    host_infos: Sequence[HostInfo],
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
