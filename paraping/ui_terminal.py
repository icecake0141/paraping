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
from typing import List, Optional, Sequence, Tuple

from paraping.ui_text import ANSI_RESET, strip_ansi, visible_cell_width


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


def render_terminal_frame(previous_lines: Optional[Sequence[str]], current_lines: List[str]) -> List[str]:
    """Render current frame lines with a full redraw or safe incremental diff."""
    if previous_lines is None:
        sys.stdout.write("\x1b[2J\x1b[H")
        output_chunks = [f"\x1b[{index + 1};1H\x1b[2K{line}" for index, line in enumerate(current_lines)]
        sys.stdout.write("".join(output_chunks))
        sys.stdout.flush()
        return current_lines

    max_lines = max(len(previous_lines), len(current_lines))
    pulse_start = _find_pulse_start(current_lines)
    if pulse_start is None:
        pulse_start = _find_pulse_start(previous_lines)
    output_chunks = []
    for index in range(max_lines):
        previous_line = previous_lines[index] if index < len(previous_lines) else None
        current_line = current_lines[index] if index < len(current_lines) else ""
        if previous_line == current_line and index < len(current_lines):
            continue
        output_chunks.append(_build_line_update(index, previous_line, current_line, pulse_start))

    if output_chunks:
        sys.stdout.write("".join(output_chunks))
        sys.stdout.flush()
    return current_lines


def _build_line_update(index: int, previous_line: Optional[str], current_line: str, pulse_start: Optional[int]) -> str:
    """Build the ANSI update sequence for one changed terminal row."""
    line_number = index + 1
    if previous_line is None:
        return f"\x1b[{line_number};1H\x1b[2K{current_line}"
    if not current_line:
        return f"\x1b[{line_number};1H\x1b[2K"
    if pulse_start is not None and index >= pulse_start:
        return f"\x1b[{line_number};1H\x1b[2K{current_line}"

    diff_start = _find_safe_diff_start(previous_line, current_line)
    if diff_start <= 0:
        return f"\x1b[{line_number};1H{current_line}\x1b[K"
    col = visible_cell_width(current_line[:diff_start]) + 1
    return f"\x1b[{line_number};{col}H{current_line[diff_start:]}\x1b[K"


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
