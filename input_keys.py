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
Keyboard input handling for ParaPing.

This module provides functions for reading keyboard input and parsing
escape sequences, particularly for arrow key navigation.
"""

import select
import sys
import time


# Constants for arrow key reading
# Increased from 0.05 to 0.1 seconds to handle slow terminals/remote connections
# where escape sequence bytes may arrive with delays (e.g., SSH, RDP, VMs)
ARROW_KEY_READ_TIMEOUT = 0.1  # Timeout for reading arrow key escape sequences


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
    """
    if not sys.stdin.isatty():
        return None
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return None
    char = sys.stdin.read(1)
    # Check for escape sequence (arrow keys start with ESC)
    if char == "\x1b":
        seq = ""
        deadline = time.monotonic() + ARROW_KEY_READ_TIMEOUT
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            ready, _, _ = select.select([sys.stdin], [], [], remaining)
            if not ready:
                break
            seq += sys.stdin.read(1)
            if seq and seq[-1] in ("A", "B", "C", "D"):
                break
        parsed = parse_escape_sequence(seq)
        return parsed if parsed is not None else char
    return char
