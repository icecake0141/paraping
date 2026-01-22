#!/usr/bin/env python3
# Copyright 2025, 2026 icecake0141
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
Keyboard input handling for ParaPing.

This module provides functions for reading keyboard input and parsing
escape sequences, particularly for arrow key navigation.

Updated to use always-on ESC buffering to handle split escape sequences
in environments like VSCode→WSL2, SSH with delays, etc.
"""

import os
import select
import sys

from paraping.escape_buffering import read_sequence_after_esc

# Constants for arrow key reading
# Note: Timeout handling is now managed by escape_buffering module
# with hardcoded timing: T_GAP=30ms, T_TOTAL=500ms
ARROW_KEY_READ_TIMEOUT = 0.1  # Kept for backward compatibility, but not actively used


def parse_escape_sequence(seq):
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


def read_key():
    """
    Read a key from stdin, handling multi-byte sequences like arrow keys.

    Returns special strings for arrow keys: 'arrow_left', 'arrow_right',
    'arrow_up', 'arrow_down'. Returns the character for normal keys,
    or None if no input is available.
    
    Uses always-on ESC buffering to handle split escape sequences in
    environments with inter-byte delays (VSCode→WSL2, SSH, etc.).
    """
    if not sys.stdin.isatty():
        return None
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return None
    
    # Read first character
    char = sys.stdin.read(1)
    
    # Check for escape sequence (arrow keys start with ESC)
    if char == "\x1b":
        # Use always-on buffering to reconstruct potentially split sequences
        stdin_fd = sys.stdin.fileno()
        seq_bytes, meta = read_sequence_after_esc(b"\x1b", stdin_fd)
        
        # Convert bytes back to string for parsing (skip the ESC byte)
        seq = seq_bytes[1:].decode('utf-8', errors='replace')
        
        # Parse the escape sequence
        parsed = parse_escape_sequence(seq)
        return parsed if parsed is not None else char
    
    return char
