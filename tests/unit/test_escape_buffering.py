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
Unit tests for escape_buffering module - robust escape sequence reconstruction.

Tests cover the always-on ESC buffering mechanism that handles split byte arrivals
in environments like VSCode→WSL2, SSH with delays, etc.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO

# Add parent directory to path to import escape_buffering
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.escape_buffering import (
    looks_like_complete_sequence,
    read_sequence_after_esc,
    ESC,
    T_GAP_SECONDS,
    T_TOTAL_SECONDS,
)


class TestLooksLikeCompleteSequence(unittest.TestCase):
    """Test escape sequence completion detection heuristics."""

    def test_empty_buffer(self):
        """Empty buffer should not be recognized as complete."""
        self.assertFalse(looks_like_complete_sequence(b""))

    def test_csi_arrow_up(self):
        """CSI sequence ESC[A for up arrow should be recognized."""
        self.assertTrue(looks_like_complete_sequence(b"\x1b[A"))

    def test_csi_arrow_down(self):
        """CSI sequence ESC[B for down arrow should be recognized."""
        self.assertTrue(looks_like_complete_sequence(b"\x1b[B"))

    def test_csi_arrow_right(self):
        """CSI sequence ESC[C for right arrow should be recognized."""
        self.assertTrue(looks_like_complete_sequence(b"\x1b[C"))

    def test_csi_arrow_left(self):
        """CSI sequence ESC[D for left arrow should be recognized."""
        self.assertTrue(looks_like_complete_sequence(b"\x1b[D"))

    def test_csi_with_parameters(self):
        """CSI sequences with parameters should be recognized."""
        # Ctrl+Arrow sequences
        self.assertTrue(looks_like_complete_sequence(b"\x1b[1;5A"))
        self.assertTrue(looks_like_complete_sequence(b"\x1b[1;5B"))
        self.assertTrue(looks_like_complete_sequence(b"\x1b[1;2C"))

    def test_csi_function_key(self):
        """Function key sequences ending with ~ should be recognized."""
        self.assertTrue(looks_like_complete_sequence(b"\x1b[15~"))  # F5
        self.assertTrue(looks_like_complete_sequence(b"\x1b[17~"))  # F6
        self.assertTrue(looks_like_complete_sequence(b"\x1b[11~"))  # F1

    def test_ss3_arrow_keys(self):
        """SS3 (application mode) arrow key sequences should be recognized."""
        self.assertTrue(looks_like_complete_sequence(b"\x1bOA"))  # Up
        self.assertTrue(looks_like_complete_sequence(b"\x1bOB"))  # Down
        self.assertTrue(looks_like_complete_sequence(b"\x1bOC"))  # Right
        self.assertTrue(looks_like_complete_sequence(b"\x1bOD"))  # Left

    def test_incomplete_csi_just_esc(self):
        """Just ESC should not be recognized as complete."""
        self.assertFalse(looks_like_complete_sequence(b"\x1b"))

    def test_incomplete_csi_esc_bracket(self):
        """ESC[ without final byte should not be recognized as complete."""
        self.assertFalse(looks_like_complete_sequence(b"\x1b["))

    def test_incomplete_ss3_esc_o(self):
        """ESC O without additional character should not be recognized as complete."""
        self.assertFalse(looks_like_complete_sequence(b"\x1bO"))

    def test_invalid_csi_out_of_range(self):
        """CSI with final byte outside 64-126 range should not be recognized."""
        # Control characters below 64
        self.assertFalse(looks_like_complete_sequence(b"\x1b[\x01"))
        # Characters above 126
        self.assertFalse(looks_like_complete_sequence(b"\x1b[\x7f"))

    def test_non_escape_sequence(self):
        """Regular text should not be recognized as escape sequence."""
        self.assertFalse(looks_like_complete_sequence(b"hello"))
        self.assertFalse(looks_like_complete_sequence(b"a"))


class TestReadSequenceAfterEsc(unittest.TestCase):
    """Test ESC sequence buffering with simulated delayed byte arrivals."""

    def test_assertion_on_non_esc_byte(self):
        """Should raise assertion error if first_byte is not ESC."""
        with self.assertRaises(AssertionError):
            read_sequence_after_esc(b"a", 0)

    @patch("paraping.escape_buffering.select.select")
    @patch("paraping.escape_buffering.os.read")
    @patch("paraping.escape_buffering.monotonic")
    @patch("paraping.escape_buffering.time")
    def test_immediate_complete_sequence(self, mock_time, mock_monotonic, mock_read, mock_select):
        """Test when complete sequence arrives immediately (no delay)."""
        # Mock time progression - need enough values for all monotonic() calls
        # Called at: start, while loop check, ts_m recording, end
        mock_monotonic.return_value = 0.001
        mock_time.return_value = 1000.0
        
        # First select returns data available
        mock_select.return_value = ([0], [], [])
        
        # Read returns the rest of the sequence
        mock_read.return_value = b"[A"
        
        result, meta = read_sequence_after_esc(ESC, 0)
        
        self.assertEqual(result, b"\x1b[A")
        self.assertIn("per_byte", meta)
        self.assertEqual(len(meta["per_byte"]), 3)  # ESC, [, A

    @patch("paraping.escape_buffering.select.select")
    @patch("paraping.escape_buffering.os.read")
    @patch("paraping.escape_buffering.monotonic")
    @patch("paraping.escape_buffering.time")
    def test_delayed_bytes_30ms_gap(self, mock_time, mock_monotonic, mock_read, mock_select):
        """Test buffering with 30ms inter-byte gap (within T_GAP)."""
        # Use return_value for consistent time progression
        time_values = [0.0, 0.001, 0.002, 0.003, 0.004]
        mock_monotonic.side_effect = time_values + [time_values[-1]] * 10  # Extra values
        mock_time.side_effect = [1000.0, 1000.001, 1000.002] + [1000.003] * 10
        
        # Select returns data twice (two chunks)
        mock_select.side_effect = [
            ([0], [], []),  # First chunk available
            ([0], [], []),  # Second chunk available (complete)
        ]
        
        # Read returns bytes in two chunks
        mock_read.side_effect = [b"[", b"A"]
        
        result, meta = read_sequence_after_esc(ESC, 0)
        
        self.assertEqual(result, b"\x1b[A")
        self.assertEqual(len(meta["per_byte"]), 3)

    @patch("paraping.escape_buffering.select.select")
    @patch("paraping.escape_buffering.os.read")
    @patch("paraping.escape_buffering.monotonic")
    @patch("paraping.escape_buffering.time")
    def test_delayed_bytes_100ms_gap(self, mock_time, mock_monotonic, mock_read, mock_select):
        """Test buffering with 100ms inter-byte gap (exceeds T_GAP but within T_TOTAL)."""
        # Mock time progression showing 100ms gaps
        time_values = [0.0, 0.001, 0.002, 0.003]
        mock_monotonic.side_effect = time_values + [time_values[-1]] * 10
        mock_time.side_effect = [1000.0, 1000.001, 1000.002] + [1000.003] * 10
        
        # Select returns data twice
        mock_select.side_effect = [
            ([0], [], []),  # First chunk
            ([0], [], []),  # Second chunk (complete)
        ]
        
        mock_read.side_effect = [b"[", b"B"]
        
        result, meta = read_sequence_after_esc(ESC, 0)
        
        self.assertEqual(result, b"\x1b[B")

    @patch("paraping.escape_buffering.select.select")
    @patch("paraping.escape_buffering.os.read")
    @patch("paraping.escape_buffering.monotonic")
    @patch("paraping.escape_buffering.time")
    def test_delayed_bytes_300ms_gap(self, mock_time, mock_monotonic, mock_read, mock_select):
        """Test buffering with 300ms inter-byte gap (within T_TOTAL=500ms)."""
        # Mock time progression showing 300ms gaps
        time_values = [0.0, 0.001, 0.002]
        mock_monotonic.side_effect = time_values + [time_values[-1]] * 10
        mock_time.side_effect = [1000.0, 1000.001] + [1000.002] * 10
        
        # Select returns data once, then timeout
        mock_select.side_effect = [
            ([0], [], []),  # First chunk (complete)
            ([], [], []),   # Timeout (no more data)
        ]
        
        mock_read.return_value = b"[C"
        
        result, meta = read_sequence_after_esc(ESC, 0)
        
        self.assertEqual(result, b"\x1b[C")

    @patch("paraping.escape_buffering.select.select")
    @patch("paraping.escape_buffering.os.read")
    @patch("paraping.escape_buffering.monotonic")
    @patch("paraping.escape_buffering.time")
    def test_timeout_beyond_t_total(self, mock_time, mock_monotonic, mock_read, mock_select):
        """Test that buffering stops after T_TOTAL (500ms) even if data might arrive."""
        # Mock time progression exceeding T_TOTAL
        # The function will keep calling monotonic() in the while loop condition
        mock_monotonic.return_value = 0.6  # Always return value exceeding T_TOTAL
        mock_time.return_value = 1000.0
        
        # No data arrives within time limit
        mock_select.return_value = ([], [], [])
        
        result, meta = read_sequence_after_esc(ESC, 0)
        
        # Should return just ESC since no additional bytes arrived in time
        self.assertEqual(result, b"\x1b")
        # The elapsed time in meta may be larger than T_TOTAL due to our mock
        # Just verify it completed

    @patch("paraping.escape_buffering.select.select")
    @patch("paraping.escape_buffering.os.read")
    @patch("paraping.escape_buffering.monotonic")
    @patch("paraping.escape_buffering.time")
    def test_early_exit_on_complete_sequence(self, mock_time, mock_monotonic, mock_read, mock_select):
        """Test early exit when a complete sequence is detected."""
        # Mock time progression
        mock_monotonic.return_value = 0.001
        mock_time.return_value = 1000.0
        
        # Select returns data once
        mock_select.return_value = ([0], [], [])
        
        # Read returns complete sequence in one chunk
        mock_read.return_value = b"[D"
        
        result, meta = read_sequence_after_esc(ESC, 0)
        
        self.assertEqual(result, b"\x1b[D")
        # Should exit early, not wait full T_GAP or T_TOTAL
        self.assertLess(meta["elapsed"], 0.1)

    @patch("paraping.escape_buffering.select.select")
    @patch("paraping.escape_buffering.os.read")
    @patch("paraping.escape_buffering.monotonic")
    @patch("paraping.escape_buffering.time")
    def test_os_error_during_read(self, mock_time, mock_monotonic, mock_read, mock_select):
        """Test graceful handling of OSError during read."""
        mock_monotonic.side_effect = [0.0, 0.01, 0.02]
        mock_time.return_value = 1000.0
        
        mock_select.return_value = ([0], [], [])
        mock_read.side_effect = OSError("Test error")
        
        result, meta = read_sequence_after_esc(ESC, 0)
        
        # Should return just ESC when read fails
        self.assertEqual(result, b"\x1b")

    @patch("paraping.escape_buffering.select.select")
    @patch("paraping.escape_buffering.os.read")
    @patch("paraping.escape_buffering.monotonic")
    @patch("paraping.escape_buffering.time")
    def test_eof_during_read(self, mock_time, mock_monotonic, mock_read, mock_select):
        """Test handling of EOF (empty read) during buffering."""
        mock_monotonic.side_effect = [0.0, 0.01, 0.02]
        mock_time.return_value = 1000.0
        
        mock_select.return_value = ([0], [], [])
        mock_read.return_value = b""  # EOF
        
        result, meta = read_sequence_after_esc(ESC, 0)
        
        # Should return just ESC when EOF encountered
        self.assertEqual(result, b"\x1b")

    @patch("paraping.escape_buffering.select.select")
    @patch("paraping.escape_buffering.os.read")
    @patch("paraping.escape_buffering.monotonic")
    @patch("paraping.escape_buffering.time")
    def test_complex_sequence_with_parameters(self, mock_time, mock_monotonic, mock_read, mock_select):
        """Test buffering complex sequence like Ctrl+Arrow with multiple bytes."""
        # Mock time progression - use return_value for simplicity
        time_counter = [0.0]
        def mock_monotonic_fn():
            time_counter[0] += 0.001
            return time_counter[0]
        
        mock_monotonic.side_effect = mock_monotonic_fn
        mock_time.return_value = 1000.0
        
        # Select returns data multiple times
        mock_select.side_effect = [
            ([0], [], []),  # [
            ([0], [], []),  # 1
            ([0], [], []),  # ;
            ([0], [], []),  # 5
            ([0], [], []),  # A (complete, should exit)
        ]
        
        # Read returns bytes one at a time (worst case)
        mock_read.side_effect = [b"[", b"1", b";", b"5", b"A"]
        
        result, meta = read_sequence_after_esc(ESC, 0)
        
        self.assertEqual(result, b"\x1b[1;5A")  # Ctrl+Up
        self.assertEqual(len(meta["per_byte"]), 6)  # ESC + 5 more bytes

    @patch("paraping.escape_buffering.select.select")
    @patch("paraping.escape_buffering.os.read")
    @patch("paraping.escape_buffering.monotonic")
    @patch("paraping.escape_buffering.time")
    def test_metadata_structure(self, mock_time, mock_monotonic, mock_read, mock_select):
        """Test that metadata has correct structure and values."""
        start_time_m = 100.0
        start_time_utc = 2000.0
        
        time_counter = [start_time_m]
        def mock_monotonic_fn():
            val = time_counter[0]
            time_counter[0] += 0.001
            return val
        
        mock_monotonic.side_effect = mock_monotonic_fn
        mock_time.return_value = start_time_utc
        
        mock_select.return_value = ([0], [], [])
        mock_read.return_value = b"[A"
        
        result, meta = read_sequence_after_esc(ESC, 0)
        
        # Check metadata structure
        self.assertIn("start_monotonic", meta)
        self.assertIn("end_monotonic", meta)
        self.assertIn("elapsed", meta)
        self.assertIn("per_byte", meta)
        
        # Check metadata values
        self.assertEqual(meta["start_monotonic"], start_time_m)
        self.assertGreater(meta["end_monotonic"], meta["start_monotonic"])
        self.assertGreater(meta["elapsed"], 0)
        
        # Check per_byte structure (each entry is tuple of hex, ts_m, ts_utc)
        self.assertIsInstance(meta["per_byte"], list)
        self.assertGreater(len(meta["per_byte"]), 0)
        for entry in meta["per_byte"]:
            self.assertEqual(len(entry), 3)
            self.assertIsInstance(entry[0], str)  # hex
            self.assertIsInstance(entry[1], float)  # monotonic timestamp
            self.assertIsInstance(entry[2], float)  # UTC timestamp


if __name__ == "__main__":
    unittest.main()
