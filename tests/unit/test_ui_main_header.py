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

"""Unit tests for main panel header composition."""

from datetime import datetime, timezone

from paraping.ui_main_header import build_main_header


def _now():
    return datetime.fromtimestamp(0, tz=timezone.utc)


def test_build_main_header_live_includes_activity_when_space_allows():
    """LIVE header should include an activity indicator when there is room."""
    header = build_main_header(
        80,
        "ip",
        "timeline",
        paused=False,
        dormant=False,
        timestamp="ts",
        now_utc=_now(),
    )
    assert "LIVE" in header
    assert len(header) > len("ParaPing - LIVE results [ip | timeline] ts")


def test_build_main_header_paused_omits_activity():
    """PAUSED header should not render an activity indicator."""
    header = build_main_header(
        80,
        "ip",
        "timeline",
        paused=True,
        dormant=False,
        timestamp="ts",
        now_utc=_now(),
    )
    assert header == "ParaPing - PAUSED results [ip | timeline] ts"


def test_build_main_header_dormant_takes_precedence():
    """DORMANT header should take precedence over PAUSED."""
    header = build_main_header(
        80,
        "ip",
        "timeline",
        paused=True,
        dormant=True,
        timestamp="ts",
        now_utc=_now(),
    )
    assert header == "ParaPing - DORMANT results [ip | timeline] ts"


def test_build_main_header_width_without_activity_space():
    """Header should fall back to text only when the panel is narrow."""
    header = build_main_header(
        10,
        "ip",
        "timeline",
        paused=False,
        dormant=False,
        timestamp="ts",
        now_utc=_now(),
    )
    assert header == "ParaPing - LIVE results [ip | timeline] ts"
