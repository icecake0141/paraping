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
Unit tests for CLI option parsing and file input
"""

import os
import sys
import unittest
from unittest.mock import mock_open, patch

# Add parent directory to path to import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import handle_options, read_input_file  # noqa: E402


class TestHandleOptions(unittest.TestCase):
    """Test command line option parsing"""

    def test_default_options(self):
        """Test default option values"""
        with patch("sys.argv", ["main.py", "example.com"]):
            args = handle_options()
            self.assertEqual(args.timeout, 1)
            self.assertEqual(args.count, 0)
            self.assertEqual(args.interval, 1.0)
            self.assertEqual(args.verbose, False)
            self.assertEqual(args.hosts, ["example.com"])

    def test_custom_timeout(self):
        """Test custom timeout option"""
        with patch("sys.argv", ["main.py", "-t", "5", "example.com"]):
            args = handle_options()
            self.assertEqual(args.timeout, 5)

    def test_custom_count(self):
        """Test custom count option"""
        with patch("sys.argv", ["main.py", "-c", "10", "example.com"]):
            args = handle_options()
            self.assertEqual(args.count, 10)

    def test_verbose_flag(self):
        """Test verbose flag"""
        with patch("sys.argv", ["main.py", "-v", "example.com"]):
            args = handle_options()
            self.assertTrue(args.verbose)

    def test_multiple_hosts(self):
        """Test multiple hosts"""
        with patch("sys.argv", ["main.py", "host1.com", "host2.com", "host3.com"]):
            args = handle_options()
            self.assertEqual(len(args.hosts), 3)
            self.assertIn("host1.com", args.hosts)

    def test_custom_interval(self):
        """Test custom interval option"""
        with patch("sys.argv", ["main.py", "-i", "0.5", "example.com"]):
            args = handle_options()
            self.assertEqual(args.interval, 0.5)

    def test_infinite_count(self):
        """Test infinite count (count=0)"""
        with patch("sys.argv", ["main.py", "-c", "0", "example.com"]):
            args = handle_options()
            self.assertEqual(args.count, 0)

    def test_short_options_for_long_flags(self):
        """Test short options that mirror long-only flags"""
        with patch(
            "sys.argv",
            [
                "main.py",
                "-s",
                "0.7",
                "-P",
                "left",
                "-m",
                "ping",
                "-z",
                "Asia/Tokyo",
                "-Z",
                "display",
                "-F",
                "-B",
                "-C",
                "-H",
                "/tmp/ping_helper",
                "example.com",
            ],
        ):
            args = handle_options()
            self.assertEqual(args.slow_threshold, 0.7)
            self.assertEqual(args.panel_position, "left")
            self.assertEqual(args.pause_mode, "ping")
            self.assertEqual(args.timezone, "Asia/Tokyo")
            self.assertEqual(args.snapshot_timezone, "display")
            self.assertTrue(args.flash_on_fail)
            self.assertTrue(args.bell_on_fail)
            self.assertTrue(args.color)
            self.assertEqual(args.ping_helper, "/tmp/ping_helper")

    def test_interval_out_of_range(self):
        """Test interval range enforcement."""
        with patch("sys.argv", ["main.py", "-i", "0.01", "example.com"]):
            with self.assertRaises(SystemExit):
                handle_options()
        with patch("sys.argv", ["main.py", "-i", "61", "example.com"]):
            with self.assertRaises(SystemExit):
                handle_options()

    def test_timeout_must_be_positive(self):
        """Test timeout validation."""
        with patch("sys.argv", ["main.py", "-t", "0", "example.com"]):
            with self.assertRaises(SystemExit):
                handle_options()


class TestReadInputFile(unittest.TestCase):
    """Test input file reading functionality"""

    def test_read_valid_file(self):
        """Test reading a valid input file"""
        file_content = "192.168.0.1,host1\n192.168.0.2,host2\n192.168.0.3,host3\n"
        with patch("builtins.open", mock_open(read_data=file_content)):
            hosts = read_input_file("test.txt")
            self.assertEqual(len(hosts), 3)
            self.assertEqual(
                hosts,
                [
                    {"host": "192.168.0.1", "alias": "host1", "ip": "192.168.0.1"},
                    {"host": "192.168.0.2", "alias": "host2", "ip": "192.168.0.2"},
                    {"host": "192.168.0.3", "alias": "host3", "ip": "192.168.0.3"},
                ],
            )

    def test_read_file_with_comments(self):
        """Test reading file with comments"""
        file_content = "192.168.0.1,host1\n# This is a comment\n192.168.0.2,host2\n"
        with patch("builtins.open", mock_open(read_data=file_content)):
            hosts = read_input_file("test.txt")
            self.assertEqual(len(hosts), 2)
            self.assertEqual(
                hosts,
                [
                    {"host": "192.168.0.1", "alias": "host1", "ip": "192.168.0.1"},
                    {"host": "192.168.0.2", "alias": "host2", "ip": "192.168.0.2"},
                ],
            )

    def test_read_file_with_empty_lines(self):
        """Test reading file with empty lines"""
        file_content = "192.168.0.1,host1\n\n192.168.0.2,host2\n\n"
        with patch("builtins.open", mock_open(read_data=file_content)):
            hosts = read_input_file("test.txt")
            self.assertEqual(len(hosts), 2)
            self.assertEqual(
                hosts,
                [
                    {"host": "192.168.0.1", "alias": "host1", "ip": "192.168.0.1"},
                    {"host": "192.168.0.2", "alias": "host2", "ip": "192.168.0.2"},
                ],
            )

    def test_read_file_with_invalid_lines(self):
        """Test reading file with invalid lines"""
        file_content = "HOST1 192.168.0.1\n192.168.0.2,host2\ninvalid,alias\n"
        with patch("builtins.open", mock_open(read_data=file_content)):
            hosts = read_input_file("test.txt")
            self.assertEqual(len(hosts), 1)
            self.assertEqual(
                hosts,
                [{"host": "192.168.0.2", "alias": "host2", "ip": "192.168.0.2"}],
            )

    def test_file_not_found(self):
        """Test handling of missing file"""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            hosts = read_input_file("nonexistent.txt")
            self.assertEqual(hosts, [])

    def test_permission_denied(self):
        """Test handling of permission error"""
        with patch("builtins.open", side_effect=PermissionError()):
            hosts = read_input_file("restricted.txt")
            self.assertEqual(hosts, [])


if __name__ == "__main__":
    unittest.main()
