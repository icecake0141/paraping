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
Unit tests for paraping CLI module.

This module tests the command-line interface parsing and entrypoint logic
without performing actual network operations.
"""

import os
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.cli import _handle_user_input, handle_options, main


class TestCLIArgumentParsing(unittest.TestCase):
    """Test command-line argument parsing in paraping.cli"""

    def test_handle_options_default_values(self):
        """Test that default option values are set correctly"""
        with patch("sys.argv", ["paraping", "example.com"]):
            args = handle_options()
            self.assertEqual(args.timeout, 1)
            self.assertEqual(args.count, 0)
            self.assertEqual(args.interval, 1.0)
            self.assertFalse(args.verbose)
            self.assertEqual(args.log_level, "INFO")
            self.assertIsNone(args.log_file)
            self.assertEqual(args.hosts, ["example.com"])
            self.assertEqual(args.panel_position, "right")
            self.assertEqual(args.pause_mode, "display")

    def test_handle_options_custom_timeout(self):
        """Test custom timeout option"""
        with patch("sys.argv", ["paraping", "-t", "5", "example.com"]):
            args = handle_options()
            self.assertEqual(args.timeout, 5)

    def test_handle_options_custom_count(self):
        """Test custom count option"""
        with patch("sys.argv", ["paraping", "-c", "10", "example.com"]):
            args = handle_options()
            self.assertEqual(args.count, 10)

    def test_handle_options_verbose_flag(self):
        """Test verbose flag"""
        with patch("sys.argv", ["paraping", "-v", "example.com"]):
            args = handle_options()
            self.assertTrue(args.verbose)

    def test_handle_options_log_level(self):
        """Test log level option"""
        with patch("sys.argv", ["paraping", "--log-level", "error", "example.com"]):
            args = handle_options()
            self.assertEqual(args.log_level, "ERROR")

    def test_handle_options_log_file(self):
        """Test log file option"""
        with patch("sys.argv", ["paraping", "--log-file", "/tmp/paraping.log", "example.com"]):
            args = handle_options()
            self.assertEqual(args.log_file, "/tmp/paraping.log")

    def test_handle_options_multiple_hosts(self):
        """Test parsing multiple hosts"""
        with patch("sys.argv", ["paraping", "host1.com", "host2.com", "host3.com"]):
            args = handle_options()
            self.assertEqual(len(args.hosts), 3)
            self.assertIn("host1.com", args.hosts)
            self.assertIn("host2.com", args.hosts)
            self.assertIn("host3.com", args.hosts)

    def test_handle_options_custom_interval(self):
        """Test custom interval option"""
        with patch("sys.argv", ["paraping", "-i", "2.5", "example.com"]):
            args = handle_options()
            self.assertEqual(args.interval, 2.5)

    def test_handle_options_slow_threshold(self):
        """Test slow threshold option"""
        with patch("sys.argv", ["paraping", "-s", "0.7", "example.com"]):
            args = handle_options()
            self.assertEqual(args.slow_threshold, 0.7)

    def test_handle_options_panel_position(self):
        """Test panel position option"""
        for position in ["right", "left", "top", "bottom", "none"]:
            with patch("sys.argv", ["paraping", "-P", position, "example.com"]):
                args = handle_options()
                self.assertEqual(args.panel_position, position)

    def test_handle_options_pause_mode(self):
        """Test pause mode option"""
        for mode in ["display", "ping"]:
            with patch("sys.argv", ["paraping", "-m", mode, "example.com"]):
                args = handle_options()
                self.assertEqual(args.pause_mode, mode)

    def test_handle_options_timezone(self):
        """Test timezone option"""
        with patch("sys.argv", ["paraping", "-z", "Asia/Tokyo", "example.com"]):
            args = handle_options()
            self.assertEqual(args.timezone, "Asia/Tokyo")

    def test_handle_options_snapshot_timezone(self):
        """Test snapshot timezone option"""
        for tz in ["utc", "display"]:
            with patch("sys.argv", ["paraping", "-Z", tz, "example.com"]):
                args = handle_options()
                self.assertEqual(args.snapshot_timezone, tz)

    def test_handle_options_flash_on_fail(self):
        """Test flash-on-fail flag"""
        with patch("sys.argv", ["paraping", "-F", "example.com"]):
            args = handle_options()
            self.assertTrue(args.flash_on_fail)

    def test_handle_options_bell_on_fail(self):
        """Test bell-on-fail flag"""
        with patch("sys.argv", ["paraping", "-B", "example.com"]):
            args = handle_options()
            self.assertTrue(args.bell_on_fail)

    def test_handle_options_color(self):
        """Test color flag"""
        with patch("sys.argv", ["paraping", "-C", "example.com"]):
            args = handle_options()
            self.assertTrue(args.color)

    def test_handle_options_ping_helper_path(self):
        """Test ping helper path option"""
        with patch("sys.argv", ["paraping", "-H", "/custom/path/ping_helper", "example.com"]):
            args = handle_options()
            self.assertEqual(args.ping_helper, "/custom/path/ping_helper")

    def test_handle_options_input_file(self):
        """Test input file option"""
        with patch("sys.argv", ["paraping", "-f", "hosts.txt"]):
            args = handle_options()
            self.assertEqual(args.input, "hosts.txt")

    def test_handle_options_combined_flags(self):
        """Test multiple options combined"""
        with patch(
            "sys.argv",
            [
                "paraping",
                "-t",
                "3",
                "-c",
                "5",
                "-i",
                "1.5",
                "-s",
                "0.8",
                "-v",
                "-P",
                "left",
                "-m",
                "ping",
                "-F",
                "-B",
                "-C",
                "host1.com",
                "host2.com",
            ],
        ):
            args = handle_options()
            self.assertEqual(args.timeout, 3)
            self.assertEqual(args.count, 5)
            self.assertEqual(args.interval, 1.5)
            self.assertEqual(args.slow_threshold, 0.8)
            self.assertTrue(args.verbose)
            self.assertEqual(args.panel_position, "left")
            self.assertEqual(args.pause_mode, "ping")
            self.assertTrue(args.flash_on_fail)
            self.assertTrue(args.bell_on_fail)
            self.assertTrue(args.color)
            self.assertEqual(len(args.hosts), 2)

    def test_handle_options_interval_validation_min(self):
        """Test interval validation - minimum value"""
        with patch("sys.argv", ["paraping", "-i", "0.05", "example.com"]):
            with self.assertRaises(SystemExit):
                handle_options()

    def test_handle_options_interval_validation_max(self):
        """Test interval validation - maximum value"""
        with patch("sys.argv", ["paraping", "-i", "61", "example.com"]):
            with self.assertRaises(SystemExit):
                handle_options()

    def test_handle_options_timeout_validation(self):
        """Test timeout validation - must be positive"""
        with patch("sys.argv", ["paraping", "-t", "0", "example.com"]):
            with self.assertRaises(SystemExit):
                handle_options()


class TestCLIMain(unittest.TestCase):
    """Test the main CLI entrypoint function"""

    @patch("paraping.cli.run")
    @patch("paraping.cli.handle_options")
    def test_main_calls_handle_options_and_run(self, mock_handle_options, mock_run):
        """Test that main() calls handle_options() and then run()"""
        mock_args = MagicMock()
        mock_handle_options.return_value = mock_args

        main()

        mock_handle_options.assert_called_once()
        mock_run.assert_called_once_with(mock_args)

    @patch("paraping.cli.run")
    def test_main_with_benign_arguments(self, mock_run):
        """Test main with benign arguments (no network/ping attempts)"""
        # Mock run to avoid actual execution
        mock_run.return_value = None

        # Test that main can be called with benign arguments via sys.argv
        with patch("sys.argv", ["paraping", "--help"]):
            # --help will cause argparse to exit, which is expected
            with self.assertRaises(SystemExit) as cm:
                main()
            # Exit code 0 means successful help display
            self.assertEqual(cm.exception.code, 0)


class TestCLIRateLimitValidation(unittest.TestCase):
    """Test rate limit validation in CLI run function"""

    @patch("paraping.cli.sys.stdin.isatty")
    def test_run_rate_limit_exactly_50_is_ok(self, mock_isatty):
        """Test that exactly 50 pings/sec is allowed"""
        mock_isatty.return_value = False  # Not in interactive mode

        # Create args with 50 hosts at 1.0s interval = 50 pings/sec
        args = MagicMock()
        args.count = 0
        args.timeout = 1
        args.interval = 1.0
        args.hosts = [f"host{i}.com" for i in range(50)]
        args.input = None
        args.timezone = None
        args.snapshot_timezone = "display"
        args.ping_helper = "./bin/ping_helper"
        args.panel_position = "right"
        args.slow_threshold = 0.5

        # This should NOT raise an exception or exit
        # We can't fully test the run function without mocking more,
        # but we can verify the validation function is called correctly
        from paraping.core import validate_global_rate_limit

        is_valid, rate, error = validate_global_rate_limit(50, 1.0)
        self.assertTrue(is_valid)

    def test_run_rate_limit_over_50_fails(self):
        """Test that exceeding 50 pings/sec causes exit"""
        # Create args with 51 hosts at 1.0s interval = 51 pings/sec
        args = MagicMock()
        args.count = 0
        args.timeout = 1
        args.interval = 1.0
        args.hosts = [f"host{i}.com" for i in range(51)]
        args.input = None
        args.log_level = "INFO"
        args.log_file = None

        # Import run function
        from paraping.cli import run

        # This should call sys.exit(1) due to rate limit
        with self.assertRaises(SystemExit) as cm:
            run(args)
        self.assertEqual(cm.exception.code, 1)

    def test_run_rate_limit_short_interval_fails(self):
        """Test that short interval with many hosts fails"""
        # Create args with 50 hosts at 0.5s interval = 100 pings/sec
        args = MagicMock()
        args.count = 0
        args.timeout = 1
        args.interval = 0.5
        args.hosts = [f"host{i}.com" for i in range(50)]
        args.input = None
        args.log_level = "INFO"
        args.log_file = None

        # Import run function
        from paraping.cli import run

        # This should call sys.exit(1) due to rate limit
        with self.assertRaises(SystemExit) as cm:
            run(args)
        self.assertEqual(cm.exception.code, 1)

    def test_run_rate_limit_25_hosts_at_half_second_is_ok(self):
        """Test that 25 hosts at 0.5s interval is exactly at limit"""
        # 25 hosts at 0.5s interval = 50 pings/sec
        from paraping.core import validate_global_rate_limit

        is_valid, rate, error = validate_global_rate_limit(25, 0.5)
        self.assertTrue(is_valid)
        self.assertEqual(rate, 50.0)


class TestCLIInputHandling(unittest.TestCase):
    """Test extracted keyboard input handler behavior."""

    def test_handle_user_input_quit_sets_running_false(self):
        """Pressing q should request shutdown."""
        state = {"running": True, "stop_event": threading.Event()}

        skip_iteration = _handle_user_input("q", MagicMock(slow_threshold=0.5), state)

        self.assertFalse(skip_iteration)
        self.assertFalse(state["running"])
        self.assertTrue(state["stop_event"].is_set())

    def test_handle_user_input_hides_help_and_skips_iteration(self):
        """Any key while help is visible should close help and skip the loop body."""
        state = {"show_help": True, "force_render": False, "updated": False}

        skip_iteration = _handle_user_input("x", MagicMock(slow_threshold=0.5), state)

        self.assertTrue(skip_iteration)
        self.assertFalse(state["show_help"])
        self.assertTrue(state["force_render"])
        self.assertTrue(state["updated"])

    def test_handle_user_input_toggle_display_pause(self):
        """`p` toggles display pause mode and pause event."""
        state = {
            "show_help": False,
            "host_select_active": False,
            "graph_host_id": None,
            "display_paused": False,
            "dormant": False,
            "pause_mode": "ping",
            "pause_event": threading.Event(),
            "status_message": None,
            "force_render": False,
            "updated": False,
            "paused": False,
        }

        skip_iteration = _handle_user_input("p", MagicMock(slow_threshold=0.5), state)

        self.assertFalse(skip_iteration)
        self.assertTrue(state["display_paused"])
        self.assertTrue(state["paused"])
        self.assertTrue(state["pause_event"].is_set())
        self.assertEqual(state["status_message"], "Display paused")


if __name__ == "__main__":
    unittest.main()
