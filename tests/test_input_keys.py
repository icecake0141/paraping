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
Unit tests for input_keys module - cross-platform keyboard input handling.

Tests cover arrow key escape sequence parsing across different operating systems
and terminal emulators to ensure consistent behavior on Windows, Mac, and Linux.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path to import input_keys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from input_keys import parse_escape_sequence, read_key


class TestParseEscapeSequence(unittest.TestCase):
    """Test escape sequence parsing for cross-platform compatibility."""

    def test_standard_arrow_keys(self):
        """Test standard ANSI arrow key sequences (Linux, Mac, most terminals)."""
        self.assertEqual(parse_escape_sequence("[A"), "arrow_up")
        self.assertEqual(parse_escape_sequence("[B"), "arrow_down")
        self.assertEqual(parse_escape_sequence("[C"), "arrow_right")
        self.assertEqual(parse_escape_sequence("[D"), "arrow_left")

    def test_application_cursor_mode(self):
        """Test application cursor mode sequences (used in some terminal modes)."""
        self.assertEqual(parse_escape_sequence("OA"), "arrow_up")
        self.assertEqual(parse_escape_sequence("OB"), "arrow_down")
        self.assertEqual(parse_escape_sequence("OC"), "arrow_right")
        self.assertEqual(parse_escape_sequence("OD"), "arrow_left")

    def test_modified_arrow_keys(self):
        """Test arrow keys with modifiers (Ctrl, Shift, Alt combinations)."""
        # Ctrl+Arrow sequences
        self.assertEqual(parse_escape_sequence("[1;5A"), "arrow_up")
        self.assertEqual(parse_escape_sequence("[1;5B"), "arrow_down")
        self.assertEqual(parse_escape_sequence("[1;5C"), "arrow_right")
        self.assertEqual(parse_escape_sequence("[1;5D"), "arrow_left")
        
        # Shift+Arrow sequences
        self.assertEqual(parse_escape_sequence("[1;2A"), "arrow_up")
        self.assertEqual(parse_escape_sequence("[1;2B"), "arrow_down")

    def test_putty_windows_sequences(self):
        """Test PuTTY/Windows-specific arrow key sequences."""
        # Some Windows terminals may use different sequences
        self.assertEqual(parse_escape_sequence("[A"), "arrow_up")
        self.assertEqual(parse_escape_sequence("[B"), "arrow_down")

    def test_macos_terminal_sequences(self):
        """Test macOS Terminal.app specific sequences."""
        # macOS typically uses standard sequences, but test application mode
        self.assertEqual(parse_escape_sequence("OA"), "arrow_up")
        self.assertEqual(parse_escape_sequence("OB"), "arrow_down")

    def test_empty_sequence(self):
        """Test handling of empty escape sequence."""
        self.assertIsNone(parse_escape_sequence(""))

    def test_unknown_sequence(self):
        """Test handling of unknown/invalid escape sequences."""
        self.assertIsNone(parse_escape_sequence("[Z"))
        self.assertIsNone(parse_escape_sequence("X"))

    def test_partial_sequence_single_bracket(self):
        """Test handling of partial/incomplete sequence - just bracket."""
        # If only '[' is read, should not match
        result = parse_escape_sequence("[")
        # This will be None because seq[0] is '[' but seq[-1] is also '['
        # which is not in arrow_map
        self.assertIsNone(result)

    def test_generic_arrow_sequences(self):
        """Test generic sequences that should still be recognized."""
        # Sequences with extra modifiers should still work via fallback logic
        self.assertEqual(parse_escape_sequence("[1A"), "arrow_up")
        self.assertEqual(parse_escape_sequence("[1B"), "arrow_down")
        self.assertEqual(parse_escape_sequence("O1A"), "arrow_up")


class TestReadKey(unittest.TestCase):
    """Test read_key function for cross-platform arrow key reading."""

    @patch("input_keys.select.select")
    @patch("input_keys.sys.stdin")
    def test_read_arrow_up_standard(self, mock_stdin, mock_select):
        """Test reading standard up arrow key sequence."""
        mock_stdin.isatty.return_value = True
        # First select for initial char, second for escape sequence chars
        mock_select.side_effect = [
            ([mock_stdin], [], []),  # ESC ready
            ([mock_stdin], [], []),  # '[' ready
            ([mock_stdin], [], []),  # 'A' ready
        ]
        # Simulate ESC [ A sequence
        mock_stdin.read.side_effect = ['\x1b', '[', 'A']

        result = read_key()
        self.assertEqual(result, 'arrow_up')

    @patch("input_keys.select.select")
    @patch("input_keys.sys.stdin")
    def test_read_arrow_down_standard(self, mock_stdin, mock_select):
        """Test reading standard down arrow key sequence."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
        ]
        mock_stdin.read.side_effect = ['\x1b', '[', 'B']

        result = read_key()
        self.assertEqual(result, 'arrow_down')

    @patch("input_keys.select.select")
    @patch("input_keys.sys.stdin")
    def test_read_arrow_left_standard(self, mock_stdin, mock_select):
        """Test reading standard left arrow key sequence."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
        ]
        mock_stdin.read.side_effect = ['\x1b', '[', 'D']

        result = read_key()
        self.assertEqual(result, 'arrow_left')

    @patch("input_keys.select.select")
    @patch("input_keys.sys.stdin")
    def test_read_arrow_right_standard(self, mock_stdin, mock_select):
        """Test reading standard right arrow key sequence."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
        ]
        mock_stdin.read.side_effect = ['\x1b', '[', 'C']

        result = read_key()
        self.assertEqual(result, 'arrow_right')

    @patch("input_keys.select.select")
    @patch("input_keys.sys.stdin")
    def test_read_application_mode_arrow_up(self, mock_stdin, mock_select):
        """Test reading application cursor mode up arrow."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
        ]
        mock_stdin.read.side_effect = ['\x1b', 'O', 'A']

        result = read_key()
        self.assertEqual(result, 'arrow_up')

    @patch("input_keys.select.select")
    @patch("input_keys.sys.stdin")
    def test_read_modified_arrow_ctrl_up(self, mock_stdin, mock_select):
        """Test reading Ctrl+Up arrow sequence."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
        ]
        # Sequence: ESC [ 1 ; 5 A
        mock_stdin.read.side_effect = ['\x1b', '[', '1', ';', '5', 'A']

        result = read_key()
        self.assertEqual(result, 'arrow_up')

    @patch("input_keys.select.select")
    @patch("input_keys.sys.stdin")
    def test_read_normal_character(self, mock_stdin, mock_select):
        """Test reading a normal character (not an arrow key)."""
        mock_stdin.isatty.return_value = True
        mock_select.return_value = ([mock_stdin], [], [])
        mock_stdin.read.return_value = 'q'

        result = read_key()
        self.assertEqual(result, 'q')

    @patch("input_keys.select.select")
    @patch("input_keys.sys.stdin")
    def test_read_timeout_on_incomplete_sequence(self, mock_stdin, mock_select):
        """Test behavior when escape sequence times out (incomplete read)."""
        mock_stdin.isatty.return_value = True
        # First select returns ready for ESC, subsequent ones timeout
        mock_select.side_effect = [
            ([mock_stdin], [], []),  # ESC ready
            ([], [], []),  # Timeout - no more data
        ]
        mock_stdin.read.side_effect = ['\x1b']  # Only ESC read

        result = read_key()
        # Should return ESC character when sequence incomplete/times out
        self.assertEqual(result, '\x1b')

    @patch("input_keys.select.select")
    @patch("input_keys.sys.stdin")
    def test_read_no_input_available(self, mock_stdin, mock_select):
        """Test reading when no input is available."""
        mock_stdin.isatty.return_value = True
        mock_select.return_value = ([], [], [])  # No data ready

        result = read_key()
        self.assertIsNone(result)

    @patch("input_keys.sys.stdin")
    def test_read_not_tty(self, mock_stdin):
        """Test reading when stdin is not a TTY."""
        mock_stdin.isatty.return_value = False

        result = read_key()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
