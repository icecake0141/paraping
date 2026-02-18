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
Unit tests for monitoring host enhancements:
1. Config sort mode (configuration order)
2. Alias as default display name
3. Monochrome square visualization improvements
"""

import os
import sys
import unittest
from collections import deque

# Add parent directory to path to import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import build_display_entries  # noqa: E402
from paraping.ui_render import build_colored_square_timeline  # noqa: E402


class TestConfigSortMode(unittest.TestCase):
    """Test configuration order sort mode"""

    def setUp(self):
        """Set up test data for sorting tests"""
        self.symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}

        # Create host_infos with specific IDs (config order)
        self.host_infos = [
            {"id": 0, "host": "host-a.com", "alias": "Host A", "ip": "1.1.1.1"},
            {"id": 1, "host": "host-b.com", "alias": "Host B", "ip": "2.2.2.2"},
            {"id": 2, "host": "host-c.com", "alias": "Host C", "ip": "3.3.3.3"},
        ]

        # Create buffers with different stats to test sorting
        self.buffers = {
            0: {
                "timeline": deque(["."] * 10, maxlen=10),
                "rtt_history": deque([10.0] * 10, maxlen=10),
            },
            1: {
                "timeline": deque(["x"] * 5 + ["."] * 5, maxlen=10),
                "rtt_history": deque([None] * 5 + [20.0] * 5, maxlen=10),
            },
            2: {
                "timeline": deque(["!"] * 10, maxlen=10),
                "rtt_history": deque([100.0] * 10, maxlen=10),
            },
        }

        self.stats = {
            0: {"success": 10, "fail": 0, "slow": 0},
            1: {"success": 5, "fail": 5, "slow": 0},
            2: {"success": 0, "fail": 0, "slow": 10},
        }

        self.display_names = {
            0: "Host A",
            1: "Host B",
            2: "Host C",
        }

    def test_config_sort_maintains_order(self):
        """Test that config sort mode maintains configuration file order"""
        entries = build_display_entries(
            self.host_infos,
            self.display_names,
            self.buffers,
            self.stats,
            self.symbols,
            sort_mode="config",
            filter_mode="all",
            slow_threshold=50.0,
        )

        # Should be in ID order: 0, 1, 2
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0][0], 0)  # host_id
        self.assertEqual(entries[1][0], 1)
        self.assertEqual(entries[2][0], 2)
        self.assertEqual(entries[0][1], "Host A")  # label
        self.assertEqual(entries[1][1], "Host B")
        self.assertEqual(entries[2][1], "Host C")

    def test_failures_sort_works_differently(self):
        """Test that failures sort mode sorts by fail count"""
        entries = build_display_entries(
            self.host_infos,
            self.display_names,
            self.buffers,
            self.stats,
            self.symbols,
            sort_mode="failures",
            filter_mode="all",
            slow_threshold=50.0,
        )

        # Should be sorted by failures: 1 (5 fails), then 0 and 2 (0 fails)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0][0], 1)  # Host B has failures
        # Host A and C have no failures, so alphabetical

    def test_latency_sort_works_differently(self):
        """Test that latency sort mode sorts by RTT"""
        entries = build_display_entries(
            self.host_infos,
            self.display_names,
            self.buffers,
            self.stats,
            self.symbols,
            sort_mode="latency",
            filter_mode="all",
            slow_threshold=50.0,
        )

        # Should be sorted by latency: 2 (100ms), 1 (20ms), 0 (10ms)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0][0], 2)  # Host C has highest latency


class TestMonochromeSquareVisualization(unittest.TestCase):
    """Test monochrome square visualization improvements"""

    def setUp(self):
        """Set up test symbols"""
        self.symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}

    def test_monochrome_fail_is_blank(self):
        """Test that failed pings show as blank in monochrome mode"""
        timeline = ["x", "x", "x"]
        result = build_colored_square_timeline(timeline, self.symbols, use_color=False)

        # All fails should be blank spaces
        self.assertEqual(result, "   ")  # 3 blank spaces

    def test_monochrome_success_is_square(self):
        """Test that successful pings show as solid square in monochrome mode"""
        timeline = [".", ".", "."]
        result = build_colored_square_timeline(timeline, self.symbols, use_color=False)

        # All successes should be solid squares
        self.assertEqual(result, "■■■")

    def test_monochrome_slow_is_square(self):
        """Test that slow pings show as solid square in monochrome mode"""
        timeline = ["!", "!", "!"]
        result = build_colored_square_timeline(timeline, self.symbols, use_color=False)

        # All slow should be solid squares (same as success)
        self.assertEqual(result, "■■■")

    def test_monochrome_pending_is_dash(self):
        """Test that pending pings show as dash in monochrome mode"""
        timeline = ["-", "-", "-"]
        result = build_colored_square_timeline(timeline, self.symbols, use_color=False)

        # All pending should be dashes
        self.assertEqual(result, "---")

    def test_monochrome_mixed_statuses(self):
        """Test mixed statuses in monochrome mode are distinguishable"""
        timeline = [".", "x", "!", "-"]
        result = build_colored_square_timeline(timeline, self.symbols, use_color=False)

        # Should be: square, blank, square, dash
        self.assertEqual(result, "■ ■-")

    def test_color_mode_uses_colors(self):
        """Test that color mode still uses ANSI colors"""
        timeline = [".", "x", "!"]
        result = build_colored_square_timeline(timeline, self.symbols, use_color=True)

        # Should contain ANSI escape codes
        self.assertIn("\x1b[", result)
        # Should still use square symbols
        self.assertIn("■", result)


if __name__ == "__main__":
    unittest.main()
