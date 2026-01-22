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

"""
ESC-aware buffering helper for robust escape sequence reconstruction.

When the main input loop reads a first byte and it is ESC (b'\x1b'),
call read_sequence_after_esc(first_byte, stdin_fd) to gather subsequent bytes.

This helper uses select.select with a small inter-byte gap and a hard cap
to handle split escape sequences in VSCode→WSL2, SSH, and similar environments.
"""

import json
import os
import select
import sys
from time import monotonic, time
from typing import Any, Dict, Tuple

ESC = b"\x1b"
T_GAP_SECONDS = 0.03  # 30 ms inter-byte gap
T_TOTAL_SECONDS = 0.5  # 500 ms max accumulation


def looks_like_complete_sequence(buf: bytes) -> bool:
    """
    Determine if a byte buffer looks like a complete escape sequence.

    Uses heuristics to detect common terminal escape sequences:
    - CSI (Control Sequence Introducer): ESC [ ... final byte in range 64-126
    - SS3 (Single Shift 3): ESC O ... (application mode)
    - Function keys: ESC [ digits ~

    Args:
        buf: Byte buffer potentially containing an escape sequence

    Returns:
        True if buffer appears to be a complete escape sequence, False otherwise
    """
    if not buf:
        return False

    # CSI sequences: ESC [ ... final byte in 64-126 range (@-~)
    if buf.startswith(ESC + b"[") and len(buf) >= 3:
        last = buf[-1]
        # Final byte in CSI is typically 64-126 (letters, @, etc.)
        if 64 <= last <= 126:
            return True

    # SS3 sequences: ESC O ... (application cursor mode)
    # Typically ESC O followed by a single character (A, B, C, D for arrows)
    if buf.startswith(ESC + b"O") and len(buf) >= 3:
        return True

    # Function key sequences often end with ~ (e.g., ESC[15~)
    if buf.startswith(ESC + b"[") and buf.endswith(b"~"):
        return True

    return False


def read_sequence_after_esc(first_byte: bytes, stdin_fd: int) -> Tuple[bytes, Dict[str, Any]]:
    """
    Read and buffer bytes after an initial ESC to reconstruct escape sequences.

    This function implements always-on buffering when an ESC byte is detected,
    waiting for additional bytes with a short inter-byte gap timeout and a
    hard maximum accumulation time. This handles cases where escape sequence
    bytes arrive split across multiple reads.

    Args:
        first_byte: The initial ESC byte (must be b'\x1b')
        stdin_fd: File descriptor for stdin

    Returns:
        Tuple of (complete_sequence, metadata_dict) where:
        - complete_sequence: All bytes read including the initial ESC
        - metadata_dict: JSONL diagnostic information with timing data

    Metadata includes:
        - start_monotonic: Start time (monotonic clock)
        - end_monotonic: End time (monotonic clock)
        - elapsed: Total elapsed time in seconds
        - per_byte: List of (hex, ts_monotonic, ts_utc) for each byte
    """
    assert first_byte == ESC, f"Expected ESC byte, got {first_byte!r}"

    start_m = monotonic()
    start_utc = time()
    buf = bytearray()
    buf.extend(first_byte)
    per_byte = [(first_byte.hex(), start_m, start_utc)]

    while monotonic() - start_m < T_TOTAL_SECONDS:
        # Wait for input with inter-byte gap timeout
        rlist, _, _ = select.select([stdin_fd], [], [], T_GAP_SECONDS)

        if not rlist:
            # Timeout - no more bytes available
            break

        try:
            # Read available bytes (up to 1024 at once for efficiency)
            chunk = os.read(stdin_fd, 1024)
        except OSError:
            # Read error - stop buffering
            break

        if not chunk:
            # EOF - stop buffering
            break

        # Record timing for each byte in the chunk
        # Note: All bytes in a chunk share the same timestamp since they arrived
        # in a single read() call. This is a limitation but acceptable for debugging.
        # If more precise per-byte timing is needed, would require byte-by-byte reads
        # which would significantly impact performance.
        ts_m = monotonic()
        ts_utc = time()
        buf.extend(chunk)
        for b in chunk:
            per_byte.append((format(b, "02x"), ts_m, ts_utc))

        # Check if we have a complete sequence - early exit optimization
        if looks_like_complete_sequence(bytes(buf)):
            break

    end_m = monotonic()

    # Build metadata for diagnostic logging
    meta = {
        "start_monotonic": start_m,
        "end_monotonic": end_m,
        "elapsed": end_m - start_m,
        "per_byte": per_byte,
    }

    # Log diagnostic information to stderr in JSONL format
    # This helps with debugging split sequence issues in production
    # Note: In high-frequency input scenarios, consider rate-limiting this logging
    # For now, logging is minimal and only happens on ESC sequences (rare in normal use)
    try:
        log_entry = {
            "event": "esc_sequence_buffering",
            "timestamp_utc": start_utc,
            "elapsed_ms": round((end_m - start_m) * 1000, 2),
            "byte_count": len(per_byte),
            "sequence_hex": buf.hex(),
            "inter_byte_gaps_ms": (
                [round((per_byte[i][1] - per_byte[i - 1][1]) * 1000, 2) for i in range(1, len(per_byte))]
                if len(per_byte) > 1
                else []
            ),
        }
        # Only log if escape sequence debugging is needed
        # Uncomment the next line to enable diagnostic logging:
        # print(json.dumps(log_entry), file=sys.stderr, flush=True)
    except Exception:
        # Don't let logging errors affect input processing
        pass

    return (bytes(buf), meta)
