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

"""Timeline symbol status and color formatting helpers."""

from typing import Dict, Optional, Sequence

from paraping.ui_text import ANSI_RESET, STATUS_COLORS, colorize_text, pad_visible


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


def latest_non_pending_status_from_timeline(timeline: Sequence[str], symbols: Dict[str, str]) -> Optional[str]:
    """Get the latest non-pending status from a timeline."""
    for symbol in reversed(timeline):
        status = status_from_symbol(symbol, symbols)
        if status and status != "pending":
            return status
    return None


def host_label_status(status: Optional[str]) -> Optional[str]:
    """Map timeline status to host-label color status."""
    if status == "pending":
        return None
    return status


def build_colored_timeline(timeline: Sequence[str], symbols: Dict[str, str], use_color: bool) -> str:
    """Build a colored timeline string from symbols."""
    return "".join(colorize_text(symbol, status_from_symbol(symbol, symbols), use_color) for symbol in timeline)


def resolve_host_label_status(timeline: Sequence[str], symbols: Dict[str, str], is_removed: bool = False) -> Optional[str]:
    """Resolve host label status with pending fallback behavior."""
    if is_removed:
        return None
    status = latest_status_from_timeline(timeline, symbols)
    if status == "pending":
        status = latest_non_pending_status_from_timeline(timeline, symbols)
    return host_label_status(status)


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


def build_colored_square_timeline(timeline_symbols: Sequence[str], symbols: Dict[str, str], use_color: bool) -> str:
    """Build a colored timeline of squares from status symbols."""
    green_color = "\x1b[32m"
    gray_color = "\x1b[37m"

    squares = []
    for symbol in timeline_symbols:
        status = status_from_symbol(symbol, symbols)
        square = "■"

        if status == "fail":
            colored_square = f"{STATUS_COLORS['fail']}{square}{ANSI_RESET}" if use_color else " "
        elif status in ("success", "slow"):
            colored_square = f"{green_color}{square}{ANSI_RESET}" if use_color else square
        else:
            colored_square = f"{gray_color}{square}{ANSI_RESET}" if use_color else "-"

        squares.append(colored_square)

    return "".join(squares)


def format_status_line(host: str, timeline: str, label_width: int) -> str:
    """Format a status line with host and timeline."""
    return f"{pad_visible(host, label_width)} | {timeline}"
