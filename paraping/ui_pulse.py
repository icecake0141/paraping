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

"""Pulse accent and activity indicator rendering for ParaPing."""

import math
import time
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from paraping.ui_panels import pad_lines
from paraping.ui_text import ANSI_RESET, pad_visible, visible_len

ACTIVITY_INDICATOR_WIDTH = 10
ACTIVITY_INDICATOR_HEIGHT = 4
ACTIVITY_INDICATOR_SPEED_HZ = 8

KITT_SCANNER_STATE: Dict[str, float] = {
    "last_monotonic": -1.0,
    "scanner_phase": 0.0,
    "last_error_ratio": 0.0,
}


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
) -> int:
    """Compute the width for the activity indicator based on available space."""
    del default_width
    if panel_width <= 0:
        return 0
    remaining = panel_width - visible_len(header_text) - 1
    if remaining <= 0:
        return 0
    return remaining


def _clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a float between inclusive lower/upper bounds."""
    return max(lower, min(upper, value))


def _resolve_kitt_speed_hz(error_ratio: float) -> float:
    """Resolve Pulse animation speed from error ratio."""
    bounded_ratio = _clamp(error_ratio, 0.0, 1.0)
    return 2.0 + 12.0 * bounded_ratio


def _resolve_kitt_scanner_speed_hz(error_ratio: float) -> float:
    """Resolve Scanner-only animation speed from error ratio."""
    bounded_ratio = _clamp(error_ratio, 0.0, 1.0)
    base_speed = 2.0 + 12.0 * bounded_ratio
    slowdown_blend = math.pow(bounded_ratio, 1.6)
    slowdown_factor = 0.7 + (0.3 * slowdown_blend)
    return base_speed * slowdown_factor


def _resolve_kitt_peak_level(error_ratio: float, levels: int) -> int:
    """Resolve the maximum drawable intensity level for the current severity."""
    bounded_ratio = _clamp(error_ratio, 0.0, 1.0)
    return min(levels, max(1, int(round(1 + (levels - 1) * bounded_ratio))))


def _resolve_kitt_palette(error_ratio: float) -> Tuple[str, str]:
    """Resolve strong/soft ANSI colors for Pulse severity."""
    if error_ratio <= 0.0:
        return "\x1b[32m", "\x1b[2;32m"
    if error_ratio <= 0.20:
        return "\x1b[33m", "\x1b[2;33m"
    if error_ratio <= 0.50:
        return "\x1b[38;5;208m", "\x1b[38;5;214m"
    return "\x1b[31m", "\x1b[2;31m"


def _resolve_kitt_core_color(error_ratio: float) -> str:
    """Resolve a stronger core ANSI color for the scanner center."""
    if error_ratio <= 0.0:
        return "\x1b[92m"
    if error_ratio <= 0.20:
        return "\x1b[93m"
    if error_ratio <= 0.50:
        return "\x1b[38;5;214m"
    return "\x1b[91m"


def _resolve_kitt_profile(body_height: int, preferred_rows: int = 8) -> Tuple[int, int]:
    """Resolve active scanner height and vertical start within the available band."""
    del preferred_rows
    active_rows = max(1, body_height)
    start_row = max(0, (body_height - active_rows) // 2)
    return active_rows, start_row


def _advance_kitt_scanner_phase(now_monotonic: float, error_ratio: float) -> float:
    """Advance the shared scanner phase while preserving continuity across speed changes."""
    last_monotonic = KITT_SCANNER_STATE["last_monotonic"]
    speed_hz = _resolve_kitt_scanner_speed_hz(error_ratio)
    if last_monotonic < 0.0 or now_monotonic < last_monotonic:
        KITT_SCANNER_STATE["last_monotonic"] = now_monotonic
        KITT_SCANNER_STATE["last_error_ratio"] = error_ratio
        return KITT_SCANNER_STATE["scanner_phase"]
    delta = max(0.0, now_monotonic - last_monotonic)
    KITT_SCANNER_STATE["scanner_phase"] += delta * speed_hz
    KITT_SCANNER_STATE["last_monotonic"] = now_monotonic
    KITT_SCANNER_STATE["last_error_ratio"] = error_ratio
    return KITT_SCANNER_STATE["scanner_phase"]


def _resolve_kitt_scanner_position(
    width: int,
    now_utc: datetime,
    error_ratio: float,
    phase_offset: int = 0,
    now_monotonic: Optional[float] = None,
) -> float:
    """Resolve the shared scanner center for the current frame."""
    del now_utc
    if width <= 1:
        return 0.0
    if now_monotonic is None:
        now_monotonic = time.monotonic()
    phase = _advance_kitt_scanner_phase(now_monotonic, error_ratio)
    center = (width - 1) / 2.0
    span = max(1.0, center)
    return center + math.sin(phase + (phase_offset * 0.008)) * span


def _scanner_row_profile(row_index: int, total_rows: int) -> float:
    """Return a 0..1 row-strength factor, highest in the vertical center."""
    if total_rows <= 1:
        return 1.0
    center = (total_rows - 1) / 2.0
    distance = abs(row_index - center)
    return max(0.25, 1.0 - (distance / max(1.0, center + 0.5)))


def _kitt_density_to_char(level: float) -> str:
    """Map normalized density to the drawable character used for the effect."""
    if level >= 0.85:
        return "█"
    if level >= 0.60:
        return "▓"
    if level >= 0.35:
        return "▒"
    if level >= 0.15:
        return "░"
    return " "


def _sample_kitt_density(samples: Sequence[float]) -> float:
    """Blend intensity samples to soften single-cell motion."""
    if not samples:
        return 0.0
    peak = max(samples)
    average = sum(samples) / len(samples)
    return _clamp((peak * 0.7) + (average * 0.3), 0.0, 1.0)


def _kitt_colorize(char: str, level: float, use_color: bool, strong_color: str, soft_color: str) -> str:
    """Colorize a drawable KITT character according to its intensity."""
    if not use_color or char == " ":
        return char
    color = strong_color if level >= 0.45 else soft_color
    return f"{color}{char}{ANSI_RESET}"


def _render_kitt_levels(
    levels: Sequence[float],
    use_color: bool,
    strong_color: str,
    soft_color: str,
    core_color: str = "",
) -> str:
    """Render a normalized intensity row into colored characters."""
    if not levels:
        return ""
    strong_threshold = max(0.3, max(levels, default=0.0) * 0.82)
    chars: List[str] = []
    for level in levels:
        char = _kitt_density_to_char(level)
        if not use_color or char == " ":
            chars.append(char)
        elif core_color and level >= 0.92:
            chars.append(f"{core_color}{char}{ANSI_RESET}")
        else:
            color = strong_color if level >= strong_threshold else soft_color
            chars.append(f"{color}{char}{ANSI_RESET}")
    return "".join(chars)


def _build_kitt_scanner_levels(
    width: int,
    now_utc: datetime,
    row_index: int,
    total_rows: int,
    error_ratio: float,
    center: Optional[float] = None,
) -> List[float]:
    """Build a smooth scanner intensity map for one row."""
    if width <= 0:
        return []
    row_strength = _scanner_row_profile(row_index, total_rows)
    if center is None:
        center = _resolve_kitt_scanner_position(width, now_utc, error_ratio, phase_offset=0)
    base_half_width = max(3.0, width * (0.08 + 0.14 * error_ratio))
    half_width = max(2.5, base_half_width * (0.75 + row_strength * 0.6))
    skirt_width = half_width * (1.45 + (1.0 - row_strength) * 0.2)
    vertical_emphasis = 0.55 + (row_strength * 0.75)
    levels: List[float] = []
    for index in range(width):
        sample_points = (index - 0.35, index, index + 0.35)
        samples = []
        for sample in sample_points:
            distance = abs(sample - center)
            if distance > skirt_width:
                samples.append(0.0)
                continue
            if distance <= half_width:
                core = 1.0 - (distance / max(half_width, 0.001))
                intensity = 0.45 + (core**0.55) * 0.75
            else:
                tail_distance = (distance - half_width) / max(skirt_width - half_width, 0.001)
                intensity = max(0.0, 0.32 * ((1.0 - tail_distance) ** 1.8))
            samples.append(intensity * vertical_emphasis)
        levels.append(_sample_kitt_density(samples))
    return levels


def _build_kitt_gradient_levels(
    width: int,
    body_height: int,
    row_index: int,
    now_utc: datetime,
    error_ratio: float,
) -> List[float]:
    """Build a smooth center-out ripple intensity map for one Pulse body row."""
    if width <= 0:
        return []
    del now_utc
    bounded_height = max(1, body_height)
    bounded_row_index = min(max(0, row_index), bounded_height - 1)
    center_x = (width - 1) / 2.0
    center_y = (bounded_height - 1) / 2.0
    max_radius = max(
        1.0,
        max(
            ((corner_x - center_x) ** 2 + (corner_y - center_y) ** 2) ** 0.5
            for corner_x in (0.0, float(width - 1))
            for corner_y in (0.0, float(bounded_height - 1))
        ),
    )
    phase_time = time.monotonic()
    rings = _resolve_kitt_gradient_rings(phase_time, max_radius, error_ratio)
    levels: List[float] = []
    for index in range(width):
        distance_x = index - center_x
        distance_y = bounded_row_index - center_y
        radius = (distance_x * distance_x + distance_y * distance_y) ** 0.5
        level = 0.0
        is_center_dot = abs(distance_x) <= 0.5 and abs(distance_y) <= 0.5
        if is_center_dot:
            pulse = 0.08 * (0.5 + 0.5 * math.sin(phase_time * 2.4))
            level = max(level, 0.72 + (0.18 * error_ratio) + pulse)
        for ring_radius, ring_width, freshness in rings:
            if ring_radius < 3.2 and radius < 3.2:
                continue
            distance = abs(radius - ring_radius)
            if distance > ring_width * 1.9:
                continue
            if distance <= ring_width:
                wave_strength = 1.0 - (distance / max(0.001, ring_width))
            elif radius > ring_radius:
                shoulder_ratio = (distance - ring_width) / max(0.001, ring_width * 0.9)
                wave_strength = max(0.0, (0.12 + 0.08 * error_ratio) * (1.0 - shoulder_ratio))
            else:
                tail_ratio = (distance - ring_width) / max(0.001, ring_width * 0.9)
                wave_strength = max(0.0, (0.18 + 0.12 * error_ratio) * (1.0 - tail_ratio))
            radial_decay = max(0.68, 1.0 - (radius / (max_radius + 1.2)))
            ring_decay = max(0.74, 1.0 - (ring_radius / (max_radius + ring_width + 1.8)))
            level = max(level, wave_strength * radial_decay * ring_decay * freshness)
        levels.append(_clamp(level, 0.0, 1.0))
    return levels


def build_kitt_scanner_bar(
    width: int,
    now_utc: datetime,
    use_color: bool,
    speed_hz: int = 12,
    trail_width: int = 6,
    phase_offset: int = 0,
    row_index: int = 0,
    total_rows: int = 1,
    error_hosts: int = 0,
    total_hosts: int = 0,
) -> str:
    """Build one row of the Pulse scanner effect."""
    if width <= 0:
        return ""
    del speed_hz
    del trail_width
    error_ratio = _compute_error_ratio(error_hosts, total_hosts)
    strong_color, soft_color = _resolve_kitt_palette(error_ratio)
    core_color = _resolve_kitt_core_color(error_ratio)
    center = _resolve_kitt_scanner_position(width, now_utc, error_ratio, phase_offset=phase_offset)
    levels = _build_kitt_scanner_levels(width, now_utc, row_index + phase_offset, total_rows, error_ratio, center=center)
    return _render_kitt_levels(levels, use_color, strong_color, soft_color, core_color=core_color)


def _compute_error_ratio(error_hosts: int, total_hosts: int) -> float:
    """Normalize fail-host count into a [0.0, 1.0] ratio."""
    if total_hosts <= 0:
        return 0.0
    bounded_error_hosts = min(max(0, error_hosts), total_hosts)
    return bounded_error_hosts / total_hosts


def _resolve_kitt_gradient_rings(phase_time: float, max_radius: float, error_ratio: float) -> List[Tuple[float, float, float]]:
    """Resolve outward-only ripple rings that expire after leaving the visible area."""
    spawn_interval = 1.0
    bounded_ratio = _clamp(error_ratio, 0.0, 1.0)
    ring_speed = max(6.5, max_radius * 0.7)
    visible_ring_count = 2 + int(math.ceil(bounded_ratio * 1.5))
    max_ring_width = 1.0 + (0.55 * bounded_ratio)
    ring_lifetime = (max_radius + max_ring_width + 0.8) / max(0.001, ring_speed)
    visible_ring_count = max(visible_ring_count, min(4, 1 + int(math.ceil(ring_lifetime / max(0.001, spawn_interval)))))
    rings: List[Tuple[float, float, float]] = []
    latest_spawn_time = math.floor(phase_time / spawn_interval) * spawn_interval
    for ring_index in range(visible_ring_count):
        spawn_time = latest_spawn_time - (ring_index * spawn_interval)
        age = phase_time - spawn_time
        if age < 0.0 or age > ring_lifetime:
            continue
        ring_radius = age * ring_speed
        if ring_radius < 0.1 or ring_radius > max_radius + max_ring_width:
            continue
        ring_width = max(
            1.1,
            max_ring_width + (ring_index * 0.08) + (ring_radius / max(6.0, max_radius)) * 0.35,
        )
        freshness = max(0.65, 1.0 - (age / max(0.001, ring_lifetime)))
        rings.append((ring_radius, ring_width, freshness))
    return rings


def build_kitt_gradient_bar(
    width: int,
    now_utc: datetime,
    use_color: bool,
    speed_hz: int = 10,
    band_width: int = 12,
    row_index: int = 0,
    body_height: int = 1,
    error_hosts: int = 0,
    total_hosts: int = 0,
) -> str:
    """Build one row of the center-out ripple Pulse effect."""
    if width <= 0:
        return ""
    del speed_hz
    del band_width
    error_ratio = _compute_error_ratio(error_hosts, total_hosts)
    strong_color, soft_color = _resolve_kitt_palette(error_ratio)
    levels = _build_kitt_gradient_levels(width, body_height, row_index, now_utc, error_ratio)
    return _render_kitt_levels(levels, use_color, strong_color, soft_color, core_color=strong_color)


def render_pulse_panel(
    width: int,
    height: int,
    style: str,
    now_utc: datetime,
    use_color: bool,
    error_hosts: int = 0,
    total_hosts: int = 0,
) -> List[str]:
    """Render the Pulse accent area."""
    if width <= 0 or height <= 0:
        return []
    if height < 3:
        return []

    normalized_style = style if style in ("scanner", "gradient") else "scanner"
    style_label = "Scanner" if normalized_style == "scanner" else "Gradient"
    lines = [f"Pulse [{style_label}]".ljust(width)[:width], "-" * width]
    body_height = max(1, height - 2)
    active_rows, start_row = _resolve_kitt_profile(body_height)
    scanner_center: Optional[float] = None
    if normalized_style == "scanner":
        error_ratio = _compute_error_ratio(error_hosts, total_hosts)
        scanner_center = _resolve_kitt_scanner_position(
            width,
            now_utc,
            error_ratio,
            phase_offset=0,
            now_monotonic=time.monotonic(),
        )
    for row in range(body_height):
        if normalized_style == "gradient":
            bar = build_kitt_gradient_bar(
                width,
                now_utc,
                use_color,
                row_index=row,
                body_height=body_height,
                error_hosts=error_hosts,
                total_hosts=total_hosts,
            )
        else:
            if row < start_row or row >= start_row + active_rows:
                bar = " " * width
            else:
                error_ratio = _compute_error_ratio(error_hosts, total_hosts)
                strong_color, soft_color = _resolve_kitt_palette(error_ratio)
                core_color = _resolve_kitt_core_color(error_ratio)
                levels = _build_kitt_scanner_levels(
                    width,
                    now_utc,
                    row - start_row,
                    active_rows,
                    error_ratio,
                    center=scanner_center,
                )
                bar = _render_kitt_levels(levels, use_color, strong_color, soft_color, core_color=core_color)
        lines.append(pad_visible(bar, width))
    return pad_lines(lines, width, height)


def render_kitt_bottom_band(
    width: int,
    height: int,
    style: str,
    now_utc: datetime,
    use_color: bool,
    error_hosts: int = 0,
    total_hosts: int = 0,
) -> List[str]:
    """Backward-compatible wrapper for the Pulse panel renderer."""
    return render_pulse_panel(
        width,
        height,
        style,
        now_utc,
        use_color,
        error_hosts=error_hosts,
        total_hosts=total_hosts,
    )
