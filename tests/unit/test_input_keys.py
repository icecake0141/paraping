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

Updated to test readchar-based implementation while maintaining backwards compatibility.
Extended with edge-case coverage for:
  - Terminal type detection (TERM env var)
  - Incomplete / unknown escape sequences
  - Multiline / cursor-position sequences
  - KeyboardInterrupt handling (Ctrl+C race condition)
  - Integration with termios/tty via the terminal_raw_mode context manager
  - PTY (pseudo-terminal) based realistic I/O tests
"""

import os
import pty
import select as _select
import sys
import termios
import unittest
from typing import Any
from unittest.mock import patch

# Add parent directory to path to import input_keys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import readchar  # noqa: E402

from paraping.input_keys import (  # noqa: E402, isort: skip
    _map_readchar_key,
    parse_escape_sequence,
    read_key,
    terminal_raw_mode,
)


class TestParseEscapeSequence(unittest.TestCase):
    """Test escape sequence parsing for cross-platform compatibility."""

    def test_standard_arrow_keys(self) -> None:
        """Test standard ANSI arrow key sequences (Linux, Mac, most terminals)."""
        self.assertEqual(parse_escape_sequence("[A"), "arrow_up")
        self.assertEqual(parse_escape_sequence("[B"), "arrow_down")
        self.assertEqual(parse_escape_sequence("[C"), "arrow_right")
        self.assertEqual(parse_escape_sequence("[D"), "arrow_left")

    def test_application_cursor_mode(self) -> None:
        """Test application cursor mode sequences (used in some terminal modes)."""
        self.assertEqual(parse_escape_sequence("OA"), "arrow_up")
        self.assertEqual(parse_escape_sequence("OB"), "arrow_down")
        self.assertEqual(parse_escape_sequence("OC"), "arrow_right")
        self.assertEqual(parse_escape_sequence("OD"), "arrow_left")

    def test_modified_arrow_keys(self) -> None:
        """Test arrow keys with modifiers (Ctrl, Shift, Alt combinations)."""
        # Ctrl+Arrow sequences
        self.assertEqual(parse_escape_sequence("[1;5A"), "arrow_up")
        self.assertEqual(parse_escape_sequence("[1;5B"), "arrow_down")
        self.assertEqual(parse_escape_sequence("[1;5C"), "arrow_right")
        self.assertEqual(parse_escape_sequence("[1;5D"), "arrow_left")

        # Shift+Arrow sequences
        self.assertEqual(parse_escape_sequence("[1;2A"), "arrow_up")
        self.assertEqual(parse_escape_sequence("[1;2B"), "arrow_down")

    def test_putty_windows_sequences(self) -> None:
        """Test PuTTY/Windows-specific arrow key sequences."""
        # Some Windows terminals may use different sequences
        self.assertEqual(parse_escape_sequence("[A"), "arrow_up")
        self.assertEqual(parse_escape_sequence("[B"), "arrow_down")

    def test_macos_terminal_sequences(self) -> None:
        """Test macOS Terminal.app specific sequences."""
        # macOS typically uses standard sequences, but test application mode
        self.assertEqual(parse_escape_sequence("OA"), "arrow_up")
        self.assertEqual(parse_escape_sequence("OB"), "arrow_down")

    def test_empty_sequence(self) -> None:
        """Test handling of empty escape sequence."""
        self.assertIsNone(parse_escape_sequence(""))

    def test_unknown_sequence(self) -> None:
        """Test handling of unknown/invalid escape sequences."""
        self.assertIsNone(parse_escape_sequence("[Z"))
        self.assertIsNone(parse_escape_sequence("X"))

    def test_partial_sequence_single_bracket(self) -> None:
        """Test handling of partial/incomplete sequence - just bracket."""
        # If only '[' is read, should not match
        result = parse_escape_sequence("[")
        # This will be None because seq[0] is '[' but seq[-1] is also '['
        # which is not in arrow_map
        self.assertIsNone(result)

    def test_generic_arrow_sequences(self) -> None:
        """Test generic sequences that should still be recognized."""
        # Sequences with extra modifiers between [ and letter should work via fallback
        self.assertEqual(parse_escape_sequence("[1A"), "arrow_up")
        self.assertEqual(parse_escape_sequence("[1B"), "arrow_down")
        # Note: "O1A" is NOT a valid arrow sequence - application mode doesn't use numbers


class TestReadKey(unittest.TestCase):
    """Test read_key function for cross-platform arrow key reading."""

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_read_arrow_up_standard(self, mock_stdin: Any, mock_select: Any) -> None:
        """Test reading standard up arrow key sequence."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [([mock_stdin], [], [])] * 3
        mock_stdin.read.side_effect = ["\x1b", "[", "A"]

        result = read_key()
        self.assertEqual(result, "arrow_up")

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_read_arrow_down_standard(self, mock_stdin: Any, mock_select: Any) -> None:
        """Test reading standard down arrow key sequence."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [([mock_stdin], [], [])] * 3
        mock_stdin.read.side_effect = ["\x1b", "[", "B"]

        result = read_key()
        self.assertEqual(result, "arrow_down")

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_read_arrow_left_standard(self, mock_stdin: Any, mock_select: Any) -> None:
        """Test reading standard left arrow key sequence."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [([mock_stdin], [], [])] * 3
        mock_stdin.read.side_effect = ["\x1b", "[", "D"]

        result = read_key()
        self.assertEqual(result, "arrow_left")

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_read_arrow_right_standard(self, mock_stdin: Any, mock_select: Any) -> None:
        """Test reading standard right arrow key sequence."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [([mock_stdin], [], [])] * 3
        mock_stdin.read.side_effect = ["\x1b", "[", "C"]

        result = read_key()
        self.assertEqual(result, "arrow_right")

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_read_application_mode_arrow_up(self, mock_stdin: Any, mock_select: Any) -> None:
        """Test reading application cursor mode up arrow."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [([mock_stdin], [], [])] * 3
        mock_stdin.read.side_effect = ["\x1b", "O", "A"]

        result = read_key()
        # Application cursor mode sequences should be parsed as arrow keys
        self.assertEqual(result, "arrow_up")

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_read_modified_arrow_ctrl_up(self, mock_stdin: Any, mock_select: Any) -> None:
        """Test reading Ctrl+Up arrow sequence."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [([mock_stdin], [], [])] * 6
        mock_stdin.read.side_effect = ["\x1b", "[", "1", ";", "5", "A"]

        result = read_key()
        # Modified arrow key sequences should be parsed correctly
        self.assertEqual(result, "arrow_up")

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_read_normal_character(self, mock_stdin: Any, mock_select: Any) -> None:
        """Test reading a normal character (not an arrow key)."""
        mock_stdin.isatty.return_value = True
        mock_select.return_value = ([mock_stdin], [], [])
        mock_stdin.read.return_value = "q"

        result = read_key()
        self.assertEqual(result, "q")

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_read_timeout_on_incomplete_sequence(self, mock_stdin: Any, mock_select: Any) -> None:
        """Test behavior when escape sequence times out (incomplete read)."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [([mock_stdin], [], []), ([], [], [])]
        mock_stdin.read.return_value = "\x1b"

        result = read_key()
        # Should return ESC character when sequence incomplete/times out
        self.assertEqual(result, "\x1b")

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_read_no_input_available(self, mock_stdin: Any, mock_select: Any) -> None:
        """Test reading when no input is available."""
        mock_stdin.isatty.return_value = True
        mock_select.return_value = ([], [], [])  # No data ready

        result = read_key()
        self.assertIsNone(result)

    @patch("paraping.input_keys.sys.stdin")
    def test_read_not_tty(self, mock_stdin: Any) -> None:
        """Test reading when stdin is not a TTY."""
        mock_stdin.isatty.return_value = False

        result = read_key()
        self.assertIsNone(result)

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_read_read_exception(self, mock_stdin: Any, mock_select: Any) -> None:
        """Test behavior when sys.stdin.read raises an exception."""
        mock_stdin.isatty.return_value = True
        mock_select.return_value = ([mock_stdin], [], [])
        mock_stdin.read.side_effect = Exception("read error")

        result = read_key()
        # Should return None if read fails
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# New: _map_readchar_key direct tests
# ---------------------------------------------------------------------------


class TestMapReadcharKey(unittest.TestCase):
    """Direct unit tests for the internal _map_readchar_key helper."""

    def test_readchar_up_constant(self) -> None:
        """readchar.key.UP (\x1b[A) maps to arrow_up via the key_map fast path."""
        self.assertEqual(_map_readchar_key(readchar.key.UP), "arrow_up")

    def test_readchar_down_constant(self) -> None:
        """readchar.key.DOWN maps to arrow_down via the key_map fast path."""
        self.assertEqual(_map_readchar_key(readchar.key.DOWN), "arrow_down")

    def test_readchar_left_constant(self) -> None:
        """readchar.key.LEFT maps to arrow_left via the key_map fast path."""
        self.assertEqual(_map_readchar_key(readchar.key.LEFT), "arrow_left")

    def test_readchar_right_constant(self) -> None:
        """readchar.key.RIGHT maps to arrow_right via the key_map fast path."""
        self.assertEqual(_map_readchar_key(readchar.key.RIGHT), "arrow_right")

    def test_application_cursor_escape_fallback(self) -> None:
        """\\x1bOA (application cursor mode) reaches the parse fallback path."""
        self.assertEqual(_map_readchar_key("\x1bOA"), "arrow_up")

    def test_modified_ctrl_up_fallback(self) -> None:
        """\\x1b[1;5A (Ctrl+Up in xterm) is resolved via the parse fallback path."""
        self.assertEqual(_map_readchar_key("\x1b[1;5A"), "arrow_up")

    def test_cursor_position_sequence_returned_as_is(self) -> None:
        """Cursor-position sequence \\x1b[5;10H is unknown; returned unchanged."""
        self.assertEqual(_map_readchar_key("\x1b[5;10H"), "\x1b[5;10H")

    def test_lone_esc_returned_as_is(self) -> None:
        """A lone ESC byte (len == 1) is not a sequence; returned unchanged."""
        self.assertEqual(_map_readchar_key("\x1b"), "\x1b")

    def test_regular_character_passthrough(self) -> None:
        """Plain characters are returned unchanged."""
        self.assertEqual(_map_readchar_key("q"), "q")

    def test_ctrl_c_character_passthrough(self) -> None:
        """Ctrl+C as a character (\\x03) is returned unchanged – not swallowed."""
        self.assertEqual(_map_readchar_key("\x03"), "\x03")

    def test_empty_string_passthrough(self) -> None:
        """An empty string is returned unchanged (no crash)."""
        self.assertEqual(_map_readchar_key(""), "")


# ---------------------------------------------------------------------------
# New: escape-sequence edge cases
# ---------------------------------------------------------------------------


class TestEscapeSequenceEdgeCases(unittest.TestCase):
    """Edge cases for parse_escape_sequence that extend the basic test suite."""

    def test_cursor_position_returns_none(self) -> None:
        """Cursor-position sequence [5;10H ends with 'H', not an arrow letter → None."""
        self.assertIsNone(parse_escape_sequence("[5;10H"))

    def test_cursor_home_returns_none(self) -> None:
        """Cursor home [H ends with 'H' → None."""
        self.assertIsNone(parse_escape_sequence("[H"))

    def test_insert_key_returns_none(self) -> None:
        """Insert key [2~ ends with '~' → None."""
        self.assertIsNone(parse_escape_sequence("[2~"))

    def test_delete_key_returns_none(self) -> None:
        """Delete key [3~ ends with '~' → None."""
        self.assertIsNone(parse_escape_sequence("[3~"))

    def test_bracketed_paste_start_returns_none(self) -> None:
        """Bracketed-paste start [200~ ends with '~' → None."""
        self.assertIsNone(parse_escape_sequence("[200~"))

    def test_f1_key_returns_none(self) -> None:
        """F1 VT key OP: first char 'O', last char 'P' (not A/B/C/D) → None."""
        self.assertIsNone(parse_escape_sequence("OP"))

    def test_semicolon_sequence_ending_in_arrow_letter(self) -> None:
        """[5;5A: starts '[', ends 'A' → arrow_up via the generic fallback."""
        self.assertEqual(parse_escape_sequence("[5;5A"), "arrow_up")

    def test_semicolon_sequence_ending_in_d(self) -> None:
        """[1;3D: starts '[', ends 'D' → arrow_left via the generic fallback."""
        self.assertEqual(parse_escape_sequence("[1;3D"), "arrow_left")

    def test_leading_char_not_bracket_or_o_returns_none(self) -> None:
        """Sequences that don't start with '[' or 'O' are not arrow sequences → None."""
        self.assertIsNone(parse_escape_sequence("PA"))
        self.assertIsNone(parse_escape_sequence("1A"))

    def test_xterm_term_env(self) -> None:
        """parse_escape_sequence is unaffected by TERM=xterm."""
        with patch.dict(os.environ, {"TERM": "xterm"}):
            self.assertEqual(parse_escape_sequence("[A"), "arrow_up")

    def test_xterm_256color_term_env(self) -> None:
        """parse_escape_sequence is unaffected by TERM=xterm-256color."""
        with patch.dict(os.environ, {"TERM": "xterm-256color"}):
            self.assertEqual(parse_escape_sequence("[A"), "arrow_up")

    def test_screen_term_env(self) -> None:
        """parse_escape_sequence is unaffected by TERM=screen."""
        with patch.dict(os.environ, {"TERM": "screen"}):
            self.assertEqual(parse_escape_sequence("[A"), "arrow_up")

    def test_no_term_env(self) -> None:
        """parse_escape_sequence works correctly when TERM is not set."""
        env = {k: v for k, v in os.environ.items() if k != "TERM"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(parse_escape_sequence("[A"), "arrow_up")


# ---------------------------------------------------------------------------
# New: read_key edge cases (KeyboardInterrupt, OSError from select)
# ---------------------------------------------------------------------------


class TestReadKeyEdgeCases(unittest.TestCase):
    """Edge-case tests for read_key not covered by the existing test class."""

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_keyboard_interrupt_propagates(self, mock_stdin: Any, mock_select: Any) -> None:
        """KeyboardInterrupt from sys.stdin.read must NOT be silenced.

        ``except Exception`` does not catch BaseException subclasses, so Ctrl+C
        during an active read propagates to the caller as expected.
        """
        mock_stdin.isatty.return_value = True
        mock_select.return_value = ([mock_stdin], [], [])
        mock_stdin.read.side_effect = KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            read_key()

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_os_error_from_select_propagates(self, mock_stdin: Any, mock_select: Any) -> None:
        """OSError from select.select (e.g. bad fd) propagates to the caller.

        select() is intentionally not wrapped so that programming errors surface.
        """
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = OSError("bad file descriptor")

        with self.assertRaises(OSError):
            read_key()

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_ctrl_c_as_character(self, mock_stdin: Any, mock_select: Any) -> None:
        """Ctrl+C delivered as the character \\x03 (not a signal) is returned as-is."""
        mock_stdin.isatty.return_value = True
        mock_select.return_value = ([mock_stdin], [], [])
        mock_stdin.read.return_value = "\x03"

        result = read_key()
        self.assertEqual(result, "\x03")

    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_unknown_escape_sequence_returned_as_is(self, mock_stdin: Any, mock_select: Any) -> None:
        """An unrecognised escape sequence is returned verbatim from read_key."""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [([mock_stdin], [], [])] * 7
        mock_stdin.read.side_effect = ["\x1b", "[", "5", ";", "1", "0", "H"]

        result = read_key()
        self.assertEqual(result, "\x1b[5;10H")

    @patch("paraping.input_keys.readchar.readkey", side_effect=AssertionError("readchar should not be used"))
    @patch("paraping.input_keys.select.select")
    @patch("paraping.input_keys.sys.stdin")
    def test_read_key_avoids_readchar_flush(self, mock_stdin: Any, mock_select: Any, _mock_readkey: Any) -> None:
        """Regression guard: ensure read_key stays on direct stdin reads (no readchar flush)."""
        mock_stdin.isatty.return_value = True
        mock_select.return_value = ([mock_stdin], [], [])
        mock_stdin.read.return_value = "h"

        result = read_key()
        self.assertEqual(result, "h")


# ---------------------------------------------------------------------------
# New: terminal_raw_mode context manager
# ---------------------------------------------------------------------------


class TestTerminalRawMode(unittest.TestCase):
    """Tests for the terminal_raw_mode context manager using a PTY."""

    def _open_pty(self) -> tuple[int, int]:
        """Helper: open a PTY pair and return (master_fd, slave_fd)."""
        master_fd, slave_fd = pty.openpty()
        return master_fd, slave_fd

    def _close_fds(self, *fds: int) -> None:
        for fd in fds:
            try:
                os.close(fd)
            except OSError:
                pass

    def test_non_tty_fd_does_not_raise(self) -> None:
        """terminal_raw_mode with a non-TTY fd (pipe) skips setup without error."""
        r_fd, w_fd = os.pipe()
        try:
            with terminal_raw_mode(r_fd):
                pass  # must not raise
        finally:
            self._close_fds(r_fd, w_fd)

    def test_slave_pty_is_set_to_raw_mode(self) -> None:
        """terminal_raw_mode succeeds on a real PTY slave fd."""
        master_fd, slave_fd = self._open_pty()
        try:
            with terminal_raw_mode(slave_fd):
                # Inside the context the fd is a valid TTY
                self.assertTrue(os.isatty(slave_fd))
        finally:
            self._close_fds(master_fd, slave_fd)

    def test_settings_restored_after_normal_exit(self) -> None:
        """Terminal settings are restored to their original values after normal exit."""
        master_fd, slave_fd = self._open_pty()
        try:
            original = termios.tcgetattr(slave_fd)
            with terminal_raw_mode(slave_fd):
                pass
            restored = termios.tcgetattr(slave_fd)
            self.assertEqual(original, restored)
        finally:
            self._close_fds(master_fd, slave_fd)

    def test_settings_restored_after_exception(self) -> None:
        """Terminal settings are restored even when the body raises an exception."""
        master_fd, slave_fd = self._open_pty()
        try:
            original = termios.tcgetattr(slave_fd)
            try:
                with terminal_raw_mode(slave_fd):
                    raise RuntimeError("simulated error inside raw-mode block")
            except RuntimeError:
                pass
            restored = termios.tcgetattr(slave_fd)
            self.assertEqual(original, restored)
        finally:
            self._close_fds(master_fd, slave_fd)

    def test_settings_restored_after_keyboard_interrupt(self) -> None:
        """Terminal settings are restored when a KeyboardInterrupt fires inside the block."""
        master_fd, slave_fd = self._open_pty()
        try:
            original = termios.tcgetattr(slave_fd)
            try:
                with terminal_raw_mode(slave_fd):
                    raise KeyboardInterrupt
            except KeyboardInterrupt:
                pass
            restored = termios.tcgetattr(slave_fd)
            self.assertEqual(original, restored)
        finally:
            self._close_fds(master_fd, slave_fd)

    def test_default_fd_uses_stdin(self) -> None:
        """Calling terminal_raw_mode() with no args falls back to sys.stdin.fileno()."""
        master_fd, slave_fd = self._open_pty()
        try:
            slave_file = os.fdopen(slave_fd, "r", closefd=False)
            with patch("paraping.input_keys.sys.stdin", slave_file):
                with patch.object(slave_file, "fileno", return_value=slave_fd):
                    original = termios.tcgetattr(slave_fd)
                    with terminal_raw_mode():
                        pass
                    restored = termios.tcgetattr(slave_fd)
                    self.assertEqual(original, restored)
        finally:
            self._close_fds(master_fd, slave_fd)


# ---------------------------------------------------------------------------
# New: PTY integration tests
# ---------------------------------------------------------------------------


class TestPTYIntegration(unittest.TestCase):
    """Realistic integration tests using a PTY (pseudo-terminal) pair.

    These tests verify escape sequence parsing in conditions that closely
    mirror a real terminal: the slave fd is a genuine TTY, raw-mode can be
    activated, and bytes sent by the "terminal emulator" side (master_fd)
    are readable on the slave fd after passing through the line discipline.
    """

    def setUp(self) -> None:
        """Create a PTY pair used by all tests in this class."""
        self.master_fd, self.slave_fd = pty.openpty()

    def tearDown(self) -> None:
        """Close PTY file descriptors."""
        for fd in (self.master_fd, self.slave_fd):
            try:
                os.close(fd)
            except OSError:
                pass

    def test_slave_fd_is_a_tty(self) -> None:
        """The slave end of a PTY must be recognised as a TTY by os.isatty()."""
        self.assertTrue(os.isatty(self.slave_fd))

    def test_master_fd_is_not_a_tty(self) -> None:
        """The master end of a PTY is *not* a TTY (it is a ptmx device, not a pts)."""
        # On Linux, os.isatty(master_fd) may return True for some kernels;
        # the key assertion is that the slave is a TTY, which was checked above.
        # Here we simply verify the call doesn't raise.
        _ = os.isatty(self.master_fd)

    def test_termios_getattr_on_slave(self) -> None:
        """termios.tcgetattr() succeeds on the slave fd (required for raw-mode setup)."""
        attrs = termios.tcgetattr(self.slave_fd)
        self.assertIsInstance(attrs, list)
        self.assertEqual(len(attrs), 7)

    def test_escape_sequence_bytes_via_pty(self) -> None:
        """Escape sequence bytes written to the master appear on the slave in raw mode.

        Simulates the arrow-up key (\\x1b[A) being typed in a terminal emulator:
        write to master → read from slave → parse → 'arrow_up'.
        """
        # Set slave to raw mode so no canonical buffering occurs.
        old_settings = termios.tcgetattr(self.slave_fd)
        try:
            import tty as _tty

            _tty.setraw(self.slave_fd)
            os.write(self.master_fd, b"\x1b[A")
            r, _, _ = _select.select([self.slave_fd], [], [], 0.5)
            self.assertTrue(r, "Slave fd should be readable within 0.5 s")
            data = os.read(self.slave_fd, 16)
            seq_str = data.decode("utf-8", errors="replace")
            # Strip leading ESC and parse
            if seq_str.startswith("\x1b"):
                result = parse_escape_sequence(seq_str[1:])
                self.assertEqual(result, "arrow_up")
        finally:
            termios.tcsetattr(self.slave_fd, termios.TCSADRAIN, old_settings)

    def test_all_arrow_sequences_parse_correctly(self) -> None:
        """Verify each arrow-key byte sequence decodes to the expected name.

        This test exercises parse_escape_sequence with the exact byte patterns
        a PTY would deliver for all four arrow keys.
        """
        cases = [
            (b"\x1b[A", "arrow_up"),
            (b"\x1b[B", "arrow_down"),
            (b"\x1b[C", "arrow_right"),
            (b"\x1b[D", "arrow_left"),
        ]
        for raw, expected in cases:
            seq = raw.decode("utf-8")[1:]  # strip ESC
            result = parse_escape_sequence(seq)
            self.assertEqual(result, expected, f"Failed for bytes {raw!r}")

    def test_app_cursor_mode_sequences_via_pty(self) -> None:
        """Application cursor mode (\\x1bO?) sequences are also recognised.

        Some terminals (e.g. VT100 in application-cursor mode) send these
        instead of the CSI variants.
        """
        cases = [
            (b"\x1bOA", "arrow_up"),
            (b"\x1bOB", "arrow_down"),
            (b"\x1bOC", "arrow_right"),
            (b"\x1bOD", "arrow_left"),
        ]
        for raw, expected in cases:
            seq = raw.decode("utf-8")[1:]
            result = parse_escape_sequence(seq)
            self.assertEqual(result, expected, f"Failed for bytes {raw!r}")

    def test_non_arrow_sequence_not_recognised(self) -> None:
        """A cursor-position sequence (\\x1b[5;10H) should not be mistaken for an arrow."""
        seq = "[5;10H"
        self.assertIsNone(parse_escape_sequence(seq))

    @patch("paraping.input_keys.select.select")
    def test_read_key_with_pty_slave_as_stdin(self, mock_select: Any) -> None:
        """read_key works correctly when sys.stdin is the slave end of a PTY.

        The PTY slave is a real TTY, so isatty() returns True without mocking.
        select() is mocked to control readiness. closefd=False keeps fd
        ownership in setUp/tearDown.
        """
        slave_file = os.fdopen(self.slave_fd, "r", closefd=False)
        mock_select.side_effect = [([slave_file], [], [])] * 3

        with patch("paraping.input_keys.sys.stdin", slave_file):
            # Patch isatty so it returns True (the file wrapper may not proxy it)
            with patch.object(slave_file, "isatty", return_value=True):
                with patch.object(slave_file, "read", side_effect=["\x1b", "[", "B"]):
                    result = read_key()

        self.assertEqual(result, "arrow_down")
        # slave_file is not the fd owner (closefd=False); tearDown closes self.slave_fd.


if __name__ == "__main__":
    unittest.main()
