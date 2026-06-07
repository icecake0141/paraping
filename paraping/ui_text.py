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

"""ANSI and terminal text-width helpers for ParaPing rendering."""

import re
import unicodedata
from typing import Dict, Optional, Tuple

ANSI_RESET = "\x1b[0m"
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
STATUS_COLORS: Dict[str, str] = {
    "success": "\x1b[37m",  # White
    "slow": "\x1b[33m",  # Yellow
    "fail": "\x1b[31m",  # Red
    "pending": "\x1b[90m",  # Dark gray (bright black)
}


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return ANSI_ESCAPE_RE.sub("", text)


def visible_len(text: str) -> int:
    """Get the visible length of text, excluding ANSI codes."""
    return len(strip_ansi(text))


def visible_cell_width(text: str) -> int:
    """Get the terminal cell width of text, excluding ANSI codes."""
    width = 0
    index = 0
    while index < len(text):
        if text[index] == "\x1b":
            match = ANSI_ESCAPE_RE.match(text, index)
            if match:
                index = match.end()
                continue
        char = text[index]
        index += 1
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in ("F", "W") else 1
    return width


def truncate_visible(text: str, width: int) -> Tuple[str, int]:
    """Truncate text to a visible width, preserving ANSI codes."""
    result = []
    visible_count = 0
    index = 0
    while index < len(text) and visible_count < width:
        if text[index] == "\x1b":
            match = ANSI_ESCAPE_RE.match(text, index)
            if match:
                result.append(match.group(0))
                index = match.end()
                continue
        result.append(text[index])
        index += 1
        visible_count += 1
    truncated = "".join(result)
    if "\x1b[" in truncated and not truncated.endswith(ANSI_RESET):
        truncated += ANSI_RESET
    return truncated, visible_count


def pad_visible(text: str, width: int) -> str:
    """Pad text to a visible width, preserving ANSI codes."""
    truncated, visible_count = truncate_visible(text, width)
    if visible_count < width:
        truncated += " " * (width - visible_count)
    return truncated


def rjust_visible(text: str, width: int) -> str:
    """Right-justify text to a visible width, preserving ANSI codes."""
    padding = width - visible_len(text)
    if padding <= 0:
        return text
    return f"{' ' * padding}{text}"


def colorize_text(text: str, status: Optional[str], use_color: bool) -> str:
    """Apply color to text based on status."""
    if not use_color or not status:
        return text
    color = STATUS_COLORS.get(status)
    if not color:
        return text
    return f"{color}{text}{ANSI_RESET}"
