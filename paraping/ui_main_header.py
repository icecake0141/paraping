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

"""Main panel header composition for ParaPing UI rendering."""

from datetime import datetime

from paraping.ui_pulse import (
    ACTIVITY_INDICATOR_HEIGHT,
    ACTIVITY_INDICATOR_SPEED_HZ,
    build_activity_indicator,
    compute_activity_indicator_width,
)


def build_main_header(
    width: int,
    mode_label: str,
    display_mode: str,
    paused: bool,
    dormant: bool,
    timestamp: str,
    now_utc: datetime,
    *,
    kitt_mode_enabled: bool = False,
) -> str:
    """Build the main view header with live/paused state and optional activity."""
    pause_label = "DORMANT" if dormant else ("PAUSED" if paused else "LIVE")
    header_base = f"ParaPing - {pause_label} results [{mode_label} | {display_mode}] {timestamp}"
    if paused:
        return header_base

    indicator_width = compute_activity_indicator_width(width, header_base)
    if indicator_width <= 0:
        return header_base

    indicator_height = ACTIVITY_INDICATOR_HEIGHT + (2 if kitt_mode_enabled else 0)
    indicator_speed = ACTIVITY_INDICATOR_SPEED_HZ + (4 if kitt_mode_enabled else 0)
    activity_indicator = build_activity_indicator(
        now_utc,
        width=indicator_width,
        max_height=indicator_height,
        speed_hz=indicator_speed,
    )
    if not activity_indicator:
        return header_base
    return f"{header_base} {activity_indicator}"
