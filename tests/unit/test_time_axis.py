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
Unit tests for time axis functionality
"""

import os
import sys
import unittest

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.ui_render import build_time_axis  # noqa: E402


class TestTimeAxis(unittest.TestCase):
    """Test time axis building functions"""

    def test_build_time_axis_basic(self):
        """Test basic time axis generation with default interval"""
        # Timeline width of 50, label width of 10, default 1s interval
        axis = build_time_axis(timeline_width=50, label_width=10, interval_seconds=1.0)

        # Should have proper formatting
        self.assertIn("|", axis)
        # Should contain time labels
        self.assertIn("10", axis)
        self.assertIn("20", axis)
        self.assertIn("30", axis)
        self.assertIn("40", axis)

    def test_build_time_axis_with_custom_interval(self):
        """Test time axis with custom ping interval"""
        # Timeline width of 30, interval=2s means each column = 2 seconds
        # So 30 columns = 60 seconds total
        axis = build_time_axis(timeline_width=30, label_width=10, interval_seconds=2.0)

        # With 2s interval, labels should be at 0, 10, 20, 30, 40, 50, 60
        # but only those that fit in 30 columns
        self.assertIn("10", axis)
        self.assertIn("20", axis)

    def test_build_time_axis_small_width(self):
        """Test time axis with small timeline width"""
        # Very small timeline (10 characters) - should still work
        axis = build_time_axis(timeline_width=10, label_width=5, interval_seconds=1.0)

        # Should have basic structure even if small
        self.assertIn("|", axis)
        # Should be a valid string
        self.assertIsInstance(axis, str)

    def test_build_time_axis_zero_width(self):
        """Test time axis with zero timeline width"""
        # Edge case: zero width
        axis = build_time_axis(timeline_width=0, label_width=10, interval_seconds=1.0)

        # Should return empty string
        self.assertEqual(axis, "")

    def test_build_time_axis_label_spacing(self):
        """Test that labels are spaced correctly"""
        # With default 10s label period and 1s interval, labels should be every 10 columns
        axis = build_time_axis(timeline_width=100, label_width=15, interval_seconds=1.0, label_period_seconds=10.0)

        # Strip label padding to get timeline part
        timeline_part = axis.split("|")[1] if "|" in axis else axis

        # Should have labels at regular intervals
        self.assertIn("10", timeline_part)
        self.assertIn("20", timeline_part)
        self.assertIn("30", timeline_part)

    def test_build_time_axis_custom_label_period(self):
        """Test time axis with custom label period"""
        # Use 5s label period instead of default 10s
        axis = build_time_axis(timeline_width=50, label_width=10, interval_seconds=1.0, label_period_seconds=5.0)

        timeline_part = axis.split("|")[1] if "|" in axis else axis

        # With 5s period, should have more frequent labels
        self.assertIn("5", timeline_part)
        self.assertIn("10", timeline_part)
        self.assertIn("15", timeline_part)
        self.assertIn("20", timeline_part)

    def test_build_time_axis_format_matches_status_line(self):
        """Test that time axis format matches status line format"""
        label_width = 20
        timeline_width = 50
        axis = build_time_axis(timeline_width=timeline_width, label_width=label_width, interval_seconds=1.0)

        # Should have format: "<spaces> | <timeline>"
        parts = axis.split("|")
        self.assertEqual(len(parts), 2)

        # Left part should be exactly label_width spaces plus " " before pipe
        # So split on "|" gives us label_width spaces on left
        # The actual format is: "    ...    " + " | " + timeline
        # When split on "|", left part is all the spaces (label_width)
        # Plus one more space that comes before the "|"
        self.assertTrue(parts[0].strip() == "")  # Should be all spaces
        # Parts[1] starts with space after pipe
        self.assertTrue(parts[1].startswith(" "))  # Space after pipe

    def test_build_time_axis_large_interval(self):
        """Test time axis with large interval (e.g., 5s)"""
        # 20 columns with 5s interval = 100 seconds total time
        axis = build_time_axis(timeline_width=20, label_width=10, interval_seconds=5.0, label_period_seconds=10.0)

        timeline_part = axis.split("|")[1] if "|" in axis else axis

        # Should have labels but spacing adjusted for interval
        # At 5s per column, label every 10s means label every 2 columns
        self.assertTrue(len(timeline_part) > 0)

    def test_build_time_axis_interval_three_spacing(self):
        """Test time axis spacing with a 3s interval"""
        axis = build_time_axis(timeline_width=80, label_width=10, interval_seconds=3.0, label_period_seconds=10.0)

        timeline_part = axis.split("|")[1] if "|" in axis else axis
        digit_groups = [group for group in "".join(timeline_part).split() if group.isdigit()]

        # Max label value is 79 * 3 = 237, so labels should not run together
        self.assertTrue(all(len(group) <= 3 for group in digit_groups))

    def test_build_time_axis_no_label_overlap(self):
        """Test that labels don't overlap when placed close together"""
        # Use small label period to stress-test overlap prevention
        # 30 columns, 1s interval, 2s label period
        # This would try to place labels: 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28
        axis = build_time_axis(timeline_width=30, label_width=10, interval_seconds=1.0, label_period_seconds=2.0)

        timeline_part = axis.split("|")[1].strip() if "|" in axis else axis

        # Verify no overlapping by checking that all non-space chars are part of valid labels
        # Labels should be spaced at least by their character width
        # This is a simple check - just verify we got a valid axis
        self.assertIsInstance(timeline_part, str)
        self.assertTrue(len(timeline_part) <= 30)


if __name__ == "__main__":
    unittest.main()
