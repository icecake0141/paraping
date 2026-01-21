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
Debug logging module for arrow key input troubleshooting.

This module provides structured logging of keyboard input events to diagnose
arrow key non-responsiveness. It captures raw byte sequences, timing data,
terminal state, and parsing results for LLM-based root cause analysis.

DEBUG: This entire module is for temporary debugging and should be removed
after the arrow key issue is resolved.
"""

import json
import os
import sys
import termios
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class KeyInputDebugLogger:
    """
    Logger for capturing detailed keyboard input events.

    This logger captures:
    - Raw byte sequences (hex representation)
    - Timing information (monotonic and wall clock)
    - Terminal state (tty mode, stdin status)
    - Parsing results and errors

    All data is structured for easy LLM analysis.
    """

    def __init__(self, log_file_path: str = "paraping_debug_keys.log"):
        """
        Initialize debug logger.

        Args:
            log_file_path: Path to log file for writing debug events
        """
        self.log_file_path = log_file_path
        self.session_start = time.monotonic()
        self.events: List[Dict[str, Any]] = []
        self.log_file = None
        self.prompt_state: Dict[str, Any] = {
            "keys_tested": [],
            "arrows_tested": set(),
            "test_complete": False,
        }

    def start_session(self) -> None:
        """Start a new debug logging session."""
        try:
            # pylint: disable=consider-using-with
            self.log_file = open(self.log_file_path, "w", encoding="utf-8")
            self._write_session_header()
        except (IOError, OSError) as e:
            # Fall back to stderr if file can't be opened
            print(f"Warning: Could not open debug log file: {e}", file=sys.stderr)
            self.log_file = None

    def _write_session_header(self) -> None:
        """Write session metadata to log file."""
        if not self.log_file:
            return

        header = {
            "event_type": "SESSION_START",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "timestamp_monotonic": time.monotonic(),
            "python_version": sys.version,
            "platform": sys.platform,
            "terminal_type": os.environ.get("TERM", "unknown"),
            "ssh_session": "SSH_CONNECTION" in os.environ or "SSH_CLIENT" in os.environ,
            "log_format_version": "1.0",
        }

        # Add terminal state information
        if sys.stdin.isatty():
            try:
                attrs = termios.tcgetattr(sys.stdin.fileno())
                # Extract relevant flags for debugging
                header["terminal_state"] = {
                    "iflag": attrs[0],
                    "oflag": attrs[1],
                    "cflag": attrs[2],
                    "lflag": attrs[3],
                    "ispeed": attrs[4],
                    "ospeed": attrs[5],
                }
            except (termios.error, AttributeError):
                header["terminal_state"] = "unavailable"
        else:
            header["terminal_state"] = "not_a_tty"

        self._write_event(header)

    def log_key_event(
        self,
        raw_bytes: bytes,
        char_read: Optional[str],
        parsed_result: Optional[str],
        timing_info: Dict[str, float],
        stdin_ready: bool,
        notes: str = "",
    ) -> None:
        """
        Log a keyboard input event with comprehensive details.

        Args:
            raw_bytes: Raw bytes received from stdin
            char_read: Character(s) read by read_key()
            parsed_result: Result from parse_escape_sequence() if applicable
            timing_info: Dictionary with timing data (e.g., sequence_duration)
            stdin_ready: Whether stdin was ready for reading
            notes: Additional notes about this event
        """
        event = {
            "event_type": "KEY_INPUT",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "timestamp_monotonic": time.monotonic(),
            "elapsed_seconds": time.monotonic() - self.session_start,
            "raw_bytes_hex": raw_bytes.hex() if raw_bytes else "",
            "raw_bytes_repr": repr(raw_bytes),
            "char_read": char_read,
            "parsed_result": parsed_result,
            "stdin_ready": stdin_ready,
            "timing": timing_info,
            "notes": notes,
        }

        self.events.append(event)
        self._write_event(event)

        # Update prompt state for tracking
        if parsed_result and "arrow" in parsed_result:
            self.prompt_state["arrows_tested"].add(parsed_result)
        if char_read:
            self.prompt_state["keys_tested"].append(char_read)

    def log_escape_sequence(
        self,
        sequence: str,
        complete: bool,
        duration: float,
        timeout_occurred: bool,
    ) -> None:
        """
        Log escape sequence reading details.

        Args:
            sequence: The escape sequence read (without ESC)
            complete: Whether sequence reading completed normally
            duration: Time taken to read the sequence
            timeout_occurred: Whether a timeout occurred during reading
        """
        event = {
            "event_type": "ESCAPE_SEQUENCE",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "timestamp_monotonic": time.monotonic(),
            "sequence": sequence,
            "sequence_hex": sequence.encode().hex() if sequence else "",
            "complete": complete,
            "duration_seconds": duration,
            "timeout_occurred": timeout_occurred,
        }

        self.events.append(event)
        self._write_event(event)

    def log_select_call(
        self,
        timeout: float,
        ready: bool,
        duration: float,
    ) -> None:
        """
        Log select() system call for stdin monitoring.

        Args:
            timeout: Timeout value used in select()
            ready: Whether stdin was ready
            duration: Actual time spent in select()
        """
        event = {
            "event_type": "SELECT_CALL",
            "timestamp_monotonic": time.monotonic(),
            "timeout_requested": timeout,
            "stdin_ready": ready,
            "duration_seconds": duration,
        }

        self.events.append(event)
        self._write_event(event)

    def log_parse_result(
        self,
        input_sequence: str,
        parsed_result: Optional[str],
        fallback_used: bool,
    ) -> None:
        """
        Log parsing result from parse_escape_sequence().

        Args:
            input_sequence: Input to parse_escape_sequence()
            parsed_result: Result from parsing (or None)
            fallback_used: Whether fallback parsing logic was used
        """
        event = {
            "event_type": "PARSE_RESULT",
            "timestamp_monotonic": time.monotonic(),
            "input_sequence": input_sequence,
            "input_hex": input_sequence.encode().hex() if input_sequence else "",
            "parsed_result": parsed_result,
            "success": parsed_result is not None,
            "fallback_used": fallback_used,
        }

        self.events.append(event)
        self._write_event(event)

    def _write_event(self, event: Dict[str, Any]) -> None:
        """Write event to log file as JSON."""
        if self.log_file:
            try:
                self.log_file.write(json.dumps(event) + "\n")
                self.log_file.flush()  # Ensure immediate write
            except (IOError, OSError):
                pass  # Silently fail to avoid disrupting main program

    def get_prompt_message(self) -> str:
        """
        Generate prompt message to guide user testing.

        Returns:
            Prompt string for display in UI
        """
        arrows_needed = {"arrow_up", "arrow_down", "arrow_left", "arrow_right"}
        arrows_done = self.prompt_state["arrows_tested"]
        arrows_remaining = arrows_needed - arrows_done

        if not arrows_done:
            return (
                "DEBUG: Press arrow keys (↑↓←→) to test input. Logging to "
                + self.log_file_path
            )
        if arrows_remaining:
            arrow_names = {
                "arrow_up": "↑",
                "arrow_down": "↓",
                "arrow_left": "←",
                "arrow_right": "→",
            }
            remaining_symbols = [arrow_names[a] for a in arrows_remaining]
            return (
                f"DEBUG: Press {' '.join(remaining_symbols)} to complete test. "
                f"Already tested: {len(arrows_done)}/4"
            )
        self.prompt_state["test_complete"] = True
        return f"DEBUG: Arrow test complete ✓ Review {self.log_file_path} for analysis"

    def is_test_complete(self) -> bool:
        """Check if all arrow keys have been tested."""
        return self.prompt_state["test_complete"]

    def close(self) -> None:
        """Close the debug logging session."""
        if self.log_file:
            self._write_event(
                {
                    "event_type": "SESSION_END",
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "timestamp_monotonic": time.monotonic(),
                    "total_events": len(self.events),
                    "arrows_tested": list(self.prompt_state["arrows_tested"]),
                }
            )
            self.log_file.close()
            self.log_file = None


# Global debug logger instance (None when debugging is disabled)
# pylint: disable=invalid-name
_debug_logger: Optional[KeyInputDebugLogger] = None


def init_debug_logger(log_file_path: str = "paraping_debug_keys.log") -> None:
    """
    Initialize global debug logger.

    Args:
        log_file_path: Path to debug log file
    """
    # pylint: disable=global-statement
    global _debug_logger
    _debug_logger = KeyInputDebugLogger(log_file_path)
    _debug_logger.start_session()


def get_debug_logger() -> Optional[KeyInputDebugLogger]:
    """Get the global debug logger instance."""
    return _debug_logger


def shutdown_debug_logger() -> None:
    """Shutdown and close debug logger."""
    # pylint: disable=global-statement
    global _debug_logger
    if _debug_logger:
        _debug_logger.close()
        _debug_logger = None


def is_debug_enabled() -> bool:
    """Check if debug logging is enabled."""
    return _debug_logger is not None
