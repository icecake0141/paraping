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

"""Unit tests for terminal frame rendering helpers."""

import io
from unittest.mock import patch

from paraping.ui_terminal import render_terminal_frame


def test_render_terminal_frame_uses_cell_width_for_partial_updates():
    """Terminal frame writer should position partial updates by cell width."""
    stdout = io.StringIO()
    with patch("sys.stdout", new=stdout):
        result = render_terminal_frame(["A界X", "status"], ["A界Y", "status"])
    assert result == ["A界Y", "status"]
    assert "\x1b[1;4H" in stdout.getvalue()


def test_render_terminal_frame_fully_redraws_pulse_rows():
    """Terminal frame writer should fully redraw Pulse rows."""
    stdout = io.StringIO()
    previous = ["header", "Pulse [Scanner]", "----------", "  ░░░", "status"]
    current = ["header", "Pulse [Scanner]", "----------", "   ▓▓", "status"]
    with patch("sys.stdout", new=stdout):
        render_terminal_frame(previous, current)
    output = stdout.getvalue()
    assert "\x1b[4;1H\x1b[2K" in output
    assert "\x1b[4;2H" not in output
