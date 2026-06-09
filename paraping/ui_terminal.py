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

"""Terminal and display control helpers for ParaPing UI rendering."""

import os
import sys
import time
from datetime import datetime, tzinfo
from typing import Optional, Sequence, Tuple

from paraping.ui_text import ANSI_RESET, strip_ansi


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


def _find_pulse_start(lines: Sequence[str]) -> Optional[int]:
    """Return the first Pulse band line index if present."""
    for index, line in enumerate(lines):
        if strip_ansi(line).startswith("Pulse ["):
            return index
    return None


def _find_safe_diff_start(previous_line: str, current_line: str) -> int:
    """Return a safe raw-string offset where line contents diverge."""
    max_common = min(len(previous_line), len(current_line))
    index = 0
    while index < max_common and previous_line[index] == current_line[index]:
        index += 1
    if index <= 0:
        return 0
    safe_previous = _rewind_to_escape_boundary(previous_line, index)
    safe_current = _rewind_to_escape_boundary(current_line, index)
    return min(safe_previous, safe_current)


def _rewind_to_escape_boundary(text: str, index: int) -> int:
    """Rewind index if it points inside an ANSI escape sequence."""
    if index <= 0 or index > len(text):
        return max(0, min(index, len(text)))
    esc_index = text.rfind("\x1b", 0, index)
    if esc_index == -1:
        return index
    sequence_end = text.find("m", esc_index, index)
    if sequence_end == -1:
        return esc_index
    return index


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
