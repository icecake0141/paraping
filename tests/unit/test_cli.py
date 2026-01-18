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

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.cli import handle_options, main


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
        with patch("sys.argv", [
            "paraping",
            "-t", "3",
            "-c", "5",
            "-i", "1.5",
            "-s", "0.8",
            "-v",
            "-P", "left",
            "-m", "ping",
            "-F",
            "-B",
            "-C",
            "host1.com",
            "host2.com"
        ]):
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


if __name__ == "__main__":
    unittest.main()
