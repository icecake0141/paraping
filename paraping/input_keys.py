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

# DEBUG: Import debug logger for arrow key troubleshooting
# Remove this import after arrow key issue is resolved
try:
    from paraping.debug_logger import get_debug_logger
except ImportError:
    # Graceful fallback if debug_logger is not available
    def get_debug_logger():
        """Fallback when debug logger not available."""
        return None


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

    # DEBUG: Log parsing attempt
    debug_logger = get_debug_logger()
    fallback_used = False

    if not seq:
        result = None
    elif seq in ("[A", "OA"):
        result = "arrow_up"
    elif seq in ("[B", "OB"):
        result = "arrow_down"
    elif seq in ("[C", "OC"):
        result = "arrow_right"
    elif seq in ("[D", "OD"):
        result = "arrow_left"
    elif seq[0] in ("[", "O") and seq[-1] in arrow_map:
        # Fallback logic for modified arrow keys
        result = arrow_map[seq[-1]]
        fallback_used = True
    else:
        result = None

    # DEBUG: Log parse result
    if debug_logger:
        debug_logger.log_parse_result(seq, result, fallback_used)

    return result


def read_key():
    """
    Read a key from stdin, handling multi-byte sequences like arrow keys.

    Returns special strings for arrow keys: 'arrow_left', 'arrow_right',
    'arrow_up', 'arrow_down'. Returns the character for normal keys,
    or None if no input is available.
    """
    # DEBUG: Get debug logger if enabled
    debug_logger = get_debug_logger()

    if not sys.stdin.isatty():
        return None

    # DEBUG: Log select call for initial key check
    select_start = time.monotonic()
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    select_duration = time.monotonic() - select_start

    if debug_logger:
        debug_logger.log_select_call(0, bool(ready), select_duration)

    if not ready:
        return None

    char = sys.stdin.read(1)

    # Check for escape sequence (arrow keys start with ESC)
    if char == "\x1b":
        seq = ""
        seq_start = time.monotonic()
        deadline = time.monotonic() + ARROW_KEY_READ_TIMEOUT
        timeout_occurred = False

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timeout_occurred = True
                break

            # DEBUG: Log each select call during sequence reading
            select_start = time.monotonic()
            ready, _, _ = select.select([sys.stdin], [], [], remaining)
            select_duration = time.monotonic() - select_start

            if debug_logger:
                debug_logger.log_select_call(remaining, bool(ready), select_duration)

            if not ready:
                timeout_occurred = True
                break

            next_char = sys.stdin.read(1)
            seq += next_char

            if seq and seq[-1] in ("A", "B", "C", "D"):
                break

        seq_duration = time.monotonic() - seq_start

        # DEBUG: Log escape sequence reading result
        if debug_logger:
            debug_logger.log_escape_sequence(
                seq,
                complete=bool(seq),
                duration=seq_duration,
                timeout_occurred=timeout_occurred,
            )

        parsed = parse_escape_sequence(seq)
        result = parsed if parsed is not None else char

        # DEBUG: Log complete key event
        if debug_logger:
            raw_bytes = ("\x1b" + seq).encode("latin-1")
            debug_logger.log_key_event(
                raw_bytes=raw_bytes,
                char_read=result,
                parsed_result=parsed,
                timing_info={
                    "sequence_duration": seq_duration,
                    "timeout_used": ARROW_KEY_READ_TIMEOUT,
                },
                stdin_ready=True,
                notes=f"Escape sequence: {repr(seq)}",
            )

        return result

    # DEBUG: Log normal key press
    if debug_logger:
        debug_logger.log_key_event(
            raw_bytes=char.encode("latin-1"),
            char_read=char,
            parsed_result=None,
            timing_info={},
            stdin_ready=True,
            notes="Normal key press",
        )

    return char
