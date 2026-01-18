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
Unit tests for user interaction, keyboard handling, and UI controls
"""

import unittest
from unittest.mock import patch, MagicMock
import argparse
import os
import queue
import sys
from collections import deque
from datetime import datetime, timezone

# Add parent directory to path to import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import (
    parse_escape_sequence,
    toggle_panel_visibility,
    cycle_panel_position,
    flash_screen,
    ring_bell,
    should_flash_on_fail,
    read_key,
    create_state_snapshot,
    update_history_buffer,
    compute_history_page_step,
    get_cached_page_step,
    render_help_view,
    handle_options,
    main,
    render_fullscreen_rtt_graph,
)  # noqa: E402


class TestEscapeSequenceParsing(unittest.TestCase):
    """Test escape sequence parsing for arrow keys."""

    def test_parse_escape_sequence_basic_arrows(self):
        self.assertEqual(parse_escape_sequence("[A"), "arrow_up")
        self.assertEqual(parse_escape_sequence("[B"), "arrow_down")
        self.assertEqual(parse_escape_sequence("[C"), "arrow_right")
        self.assertEqual(parse_escape_sequence("[D"), "arrow_left")

    def test_parse_escape_sequence_application_cursor(self):
        self.assertEqual(parse_escape_sequence("OA"), "arrow_up")
        self.assertEqual(parse_escape_sequence("OB"), "arrow_down")
        self.assertEqual(parse_escape_sequence("OC"), "arrow_right")
        self.assertEqual(parse_escape_sequence("OD"), "arrow_left")

    def test_parse_escape_sequence_extended_arrows(self):
        self.assertEqual(parse_escape_sequence("[1;5A"), "arrow_up")
        self.assertEqual(parse_escape_sequence("[1;5B"), "arrow_down")
        self.assertEqual(parse_escape_sequence("[1;5C"), "arrow_right")
        self.assertEqual(parse_escape_sequence("[1;5D"), "arrow_left")

    def test_parse_escape_sequence_unknown(self):
        self.assertIsNone(parse_escape_sequence("[Z"))

    def test_render_fullscreen_rtt_graph_contains_header(self):
        """Fullscreen RTT graph should include host label and RTT range."""
        lines = render_fullscreen_rtt_graph(
            "host1",
            [0.01, 0.02],
            [1000.0, 1002.0],
            40,
            10,
            "timeline",
            False,
            "2025-01-01 00:00:00 (UTC)",
        )
        combined = "\n".join(lines)
        self.assertIn("host1", combined)
        self.assertIn("RTT range", combined)
        self.assertIn("seconds ago", combined)
        self.assertIn("ESC: back", combined)


class TestPanelToggle(unittest.TestCase):
    """Test summary panel toggle behavior"""

    def test_toggle_hides_and_restores(self):
        """Toggle hides panel and restores previous position."""
        position, last_visible = toggle_panel_visibility("right", None)
        self.assertEqual(position, "none")
        self.assertEqual(last_visible, "right")

        position, last_visible = toggle_panel_visibility(position, last_visible)
        self.assertEqual(position, "right")
        self.assertEqual(last_visible, "right")

    def test_toggle_defaults_when_no_previous(self):
        """Toggle restores to default when no previous position exists."""
        position, last_visible = toggle_panel_visibility("none", None, "bottom")
        self.assertEqual(position, "bottom")
        self.assertEqual(last_visible, "bottom")

    def test_cycle_panel_position(self):
        """Cycle moves through the available summary positions."""
        self.assertEqual(cycle_panel_position("left"), "right")
        self.assertEqual(cycle_panel_position("right"), "top")
        self.assertEqual(cycle_panel_position("top"), "bottom")
        self.assertEqual(cycle_panel_position("bottom"), "left")
        self.assertEqual(cycle_panel_position("none", default_position="right"), "right")


class TestQuitHotkey(unittest.TestCase):
    """Test quit hotkey functionality"""

    @patch("paraping.cli.queue.Queue")
    @patch("paraping.cli.sys.stdin")
    @patch("ui_render.get_terminal_size")
    @patch("paraping.cli.ThreadPoolExecutor")
    @patch("paraping.cli.threading.Thread")
    @patch("paraping.cli.read_key")
    def test_quit_key_exits_immediately(
        self, mock_read_key, mock_thread, mock_executor, mock_term_size, mock_stdin, mock_queue
    ):
        """Test that pressing 'q' key exits the program immediately"""
        # Mock terminal properties
        mock_stdin.isatty.return_value = True
        mock_term_size.return_value = os.terminal_size((80, 24))

        # Mock stdin for terminal setup
        mock_stdin.fileno.return_value = 0

        # Mock queue to simulate completion
        result_queue = MagicMock()
        # Always raise Empty to simulate no results
        result_queue.get_nowait.side_effect = queue.Empty
        empty_queue = MagicMock()
        empty_queue.get_nowait.side_effect = queue.Empty
        # Queue instances: result_queue, rdns_request_queue, rdns_result_queue, asn_request_queue, asn_result_queue
        mock_queue.side_effect = [
            result_queue,  # result_queue
            MagicMock(),   # rdns_request_queue
            empty_queue,   # rdns_result_queue
            MagicMock(),   # asn_request_queue
            empty_queue,   # asn_result_queue
        ]

        # Mock read_key to return 'q' after a few iterations
        mock_read_key.side_effect = [None, None, "q"]

        args = argparse.Namespace(
            timeout=1,
            count=0,  # Infinite count to ensure it would run forever without 'q'
            interval=1.0,
            slow_threshold=0.5,
            verbose=False,
            color=False,
            hosts=["host1.com"],
            input=None,
            panel_position="right",
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
            flash_on_fail=False,
            bell_on_fail=False,
            ping_helper="./ping_helper",
        )

        # Mock executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_executor.return_value.__exit__.return_value = False
        mock_executor_instance.submit.return_value = MagicMock()

        mock_thread.return_value = MagicMock()

        # Mock termios functions
        with patch("main.termios.tcgetattr", return_value=MagicMock()):
            with patch("main.termios.tcsetattr"):
                with patch("main.tty.setcbreak"):
                    # Should exit without raising exception when 'q' is pressed
                    main(args)

    @patch("paraping.cli.queue.Queue")
    @patch("paraping.cli.sys.stdin")
    @patch("ui_render.get_terminal_size")
    @patch("paraping.cli.ThreadPoolExecutor")
    @patch("paraping.cli.threading.Thread")
    @patch("paraping.cli.read_key")
    def test_quit_key_uppercase_exits_immediately(
        self, mock_read_key, mock_thread, mock_executor, mock_term_size, mock_stdin, mock_queue
    ):
        """Test that pressing 'Q' key (uppercase) exits the program immediately"""
        # Mock terminal properties
        mock_stdin.isatty.return_value = True
        mock_term_size.return_value = os.terminal_size((80, 24))

        # Mock stdin for terminal setup
        mock_stdin.fileno.return_value = 0

        # Mock queue to simulate completion
        result_queue = MagicMock()
        # Always raise Empty to simulate no results
        result_queue.get_nowait.side_effect = queue.Empty
        empty_queue = MagicMock()
        empty_queue.get_nowait.side_effect = queue.Empty
        # Queue instances: result_queue, rdns_request_queue, rdns_result_queue, asn_request_queue, asn_result_queue
        mock_queue.side_effect = [
            result_queue,  # result_queue
            MagicMock(),   # rdns_request_queue
            empty_queue,   # rdns_result_queue
            MagicMock(),   # asn_request_queue
            empty_queue,   # asn_result_queue
        ]

        # Mock read_key to return 'Q' (uppercase) after a few iterations
        mock_read_key.side_effect = [None, None, "Q"]

        args = argparse.Namespace(
            timeout=1,
            count=0,  # Infinite count to ensure it would run forever without 'Q'
            interval=1.0,
            slow_threshold=0.5,
            verbose=False,
            color=False,
            hosts=["host1.com"],
            input=None,
            panel_position="right",
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
            flash_on_fail=False,
            bell_on_fail=False,
            ping_helper="./ping_helper",
        )

        # Mock executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_executor.return_value.__exit__.return_value = False
        mock_executor_instance.submit.return_value = MagicMock()

        mock_thread.return_value = MagicMock()

        # Mock termios functions
        with patch("main.termios.tcgetattr", return_value=MagicMock()):
            with patch("main.termios.tcsetattr"):
                with patch("main.tty.setcbreak"):
                    # Should exit without raising exception when 'Q' is pressed
                    main(args)

    @patch("paraping.cli.queue.Queue")
    @patch("paraping.cli.sys.stdin")
    @patch("ui_render.get_terminal_size")
    @patch("paraping.cli.ThreadPoolExecutor")
    @patch("paraping.cli.threading.Thread")
    @patch("paraping.cli.read_key")
    def test_quit_key_exits_from_help_screen(
        self, mock_read_key, mock_thread, mock_executor, mock_term_size, mock_stdin, mock_queue
    ):
        """Test that pressing 'q' key exits even when help screen is showing"""
        # Mock terminal properties
        mock_stdin.isatty.return_value = True
        mock_term_size.return_value = os.terminal_size((80, 24))

        # Mock stdin for terminal setup
        mock_stdin.fileno.return_value = 0

        # Mock queue to simulate completion
        result_queue = MagicMock()
        # Always raise Empty to simulate no results
        result_queue.get_nowait.side_effect = queue.Empty
        empty_queue = MagicMock()
        empty_queue.get_nowait.side_effect = queue.Empty
        # Queue instances: result_queue, rdns_request_queue, rdns_result_queue, asn_request_queue, asn_result_queue
        mock_queue.side_effect = [
            result_queue,  # result_queue
            MagicMock(),   # rdns_request_queue
            empty_queue,   # rdns_result_queue
            MagicMock(),   # asn_request_queue
            empty_queue,   # asn_result_queue
        ]

        # Mock read_key to open help screen with 'H', then press 'q' to quit
        mock_read_key.side_effect = [None, "H", "q"]

        args = argparse.Namespace(
            timeout=1,
            count=0,  # Infinite count
            interval=1.0,
            slow_threshold=0.5,
            verbose=False,
            color=False,
            hosts=["host1.com"],
            input=None,
            panel_position="right",
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
            flash_on_fail=False,
            bell_on_fail=False,
            ping_helper="./ping_helper",
        )

        # Mock executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_executor.return_value.__exit__.return_value = False
        mock_executor_instance.submit.return_value = MagicMock()

        mock_thread.return_value = MagicMock()

        # Mock termios functions
        with patch("main.termios.tcgetattr", return_value=MagicMock()):
            with patch("main.termios.tcsetattr"):
                with patch("main.tty.setcbreak"):
                    # Should exit when 'q' is pressed, even with help screen open
                    main(args)


class TestFlashAndBell(unittest.TestCase):
    """Test flash and bell notification features"""

    def test_handle_options_flash_on_fail(self):
        """Test --flash-on-fail option parsing"""
        with patch("sys.argv", ["main.py", "--flash-on-fail", "example.com"]):
            args = handle_options()
            self.assertTrue(args.flash_on_fail)

    def test_handle_options_bell_on_fail(self):
        """Test --bell-on-fail option parsing"""
        with patch("sys.argv", ["main.py", "--bell-on-fail", "example.com"]):
            args = handle_options()
            self.assertTrue(args.bell_on_fail)

    def test_handle_options_both_flags(self):
        """Test both flash and bell options together"""
        with patch("sys.argv", ["main.py", "--flash-on-fail", "--bell-on-fail", "example.com"]):
            args = handle_options()
            self.assertTrue(args.flash_on_fail)
            self.assertTrue(args.bell_on_fail)

    def test_handle_options_default_false(self):
        """Test that flash and bell options default to False"""
        with patch("sys.argv", ["main.py", "example.com"]):
            args = handle_options()
            self.assertFalse(args.flash_on_fail)
            self.assertFalse(args.bell_on_fail)

    @patch("paraping.cli.sys.stdout")
    @patch("paraping.cli.time.sleep")
    def test_flash_screen(self, mock_sleep, mock_stdout):
        """Test flash_screen function"""
        flash_screen()
        # Should have called write to send escape sequences
        self.assertGreaterEqual(mock_stdout.write.call_count, 2)
        first_write = mock_stdout.write.call_args_list[0][0][0]
        self.assertIn("\x1b[47m", first_write)
        self.assertIn("\x1b[30m", first_write)
        # Should have slept for ~0.1 seconds
        mock_sleep.assert_called_once_with(0.1)
        # Should have called flush
        self.assertGreaterEqual(mock_stdout.flush.call_count, 2)

    @patch("paraping.cli.sys.stdout")
    def test_ring_bell(self, mock_stdout):
        """Test ring_bell function"""
        ring_bell()
        # Should write the bell character
        mock_stdout.write.assert_called_once_with("\a")
        # Should flush the output
        mock_stdout.flush.assert_called_once()

    def test_should_flash_on_fail(self):
        """Test helper for flash-on-fail decision"""
        self.assertTrue(should_flash_on_fail("fail", True, False))
        self.assertFalse(should_flash_on_fail("fail", True, True))
        self.assertFalse(should_flash_on_fail("success", True, False))
        self.assertFalse(should_flash_on_fail("fail", False, False))


if __name__ == "__main__":
    unittest.main()
