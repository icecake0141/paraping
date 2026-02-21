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

"""
Keyboard input handling for ParaPing using the readchar library.

This module provides functions for reading keyboard input and parsing
escape sequences, particularly for arrow key navigation. It uses the
readchar library for improved cross-platform compatibility and reliability.
"""

import select
import sys
from typing import Optional

import readchar
import readchar.key


# Constants for arrow key reading
# Increased from 0.05 to 0.1 seconds to handle slow terminals/remote connections
# where escape sequence bytes may arrive with delays (e.g., SSH, RDP, VMs)
ARROW_KEY_READ_TIMEOUT = 0.1  # Timeout for reading arrow key escape sequences


def parse_escape_sequence(seq: str) -> Optional[str]:
    """
    Parse ANSI escape sequence to identify arrow keys.

    Args:
        seq: The escape sequence string (without the leading ESC)

    Returns:
        String identifier for arrow keys ('arrow_up', 'arrow_down', etc.)
        or None if sequence is not recognized
    """
    arrow_map = {
        "A": "arrow_up",
        "B": "arrow_down",
        "C": "arrow_right",
        "D": "arrow_left",
    }
    if not seq:
        return None
    if seq in ("[A", "OA"):
        return "arrow_up"
    if seq in ("[B", "OB"):
        return "arrow_down"
    if seq in ("[C", "OC"):
        return "arrow_right"
    if seq in ("[D", "OD"):
        return "arrow_left"
    if seq[0] in ("[", "O") and seq[-1] in arrow_map:
        return arrow_map[seq[-1]]
    return None


def _map_readchar_key(key_value: str) -> str:
    """
    Map readchar key constants to ParaPing arrow key names.

    Args:
        key_value: The key string returned by readchar.readkey()

    Returns:
        String identifier for arrow keys ('arrow_up', 'arrow_down', etc.)
        or the original key value if not an arrow key
    """
    # Map readchar arrow key constants to our naming convention
    key_map = {
        readchar.key.UP: "arrow_up",
        readchar.key.DOWN: "arrow_down",
        readchar.key.LEFT: "arrow_left",
        readchar.key.RIGHT: "arrow_right",
    }

    # First check if it's a standard readchar constant
    if key_value in key_map:
        return key_map[key_value]

    # For non-standard sequences, try to parse as escape sequence
    # readchar returns full escape sequences like "\x1b[A", "\x1bOA", "\x1b[1;5A", etc.
    if key_value and key_value[0] == "\x1b" and len(key_value) > 1:
        # Strip the ESC prefix and parse the rest
        seq = key_value[1:]
        parsed = parse_escape_sequence(seq)
        if parsed:
            return parsed

    return key_value


def read_key() -> Optional[str]:
    """
    Read a key from stdin, handling multi-byte sequences like arrow keys.

    Returns special strings for arrow keys: 'arrow_left', 'arrow_right',
    'arrow_up', 'arrow_down'. Returns the character for normal keys,
    or None if no input is available.

    This function uses readchar library for improved cross-platform support
    while maintaining non-blocking behavior through select() with timeout.
    """
    if not sys.stdin.isatty():
        return None

    # Use select to check if input is available (non-blocking)
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return None

    # Input is available, use readchar to read it
    try:
        key = readchar.readkey()
        return _map_readchar_key(key)
    except Exception:
        # Fallback to None if readchar fails
        return None
