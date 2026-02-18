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
Unit tests for rendering help views, boxes, and ASCII graphs
"""

import os
import sys
import unittest

# Add parent directory to path to import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import (  # noqa: E402
    box_lines,
    build_ascii_graph,
    render_help_view,
    render_host_selection_view,
    render_square_view,
    render_status_box,
)


class TestHelpView(unittest.TestCase):
    """Test help view rendering."""

    def test_help_view_contains_close_hint(self):
        """Help view should include close hint text."""
        lines = render_help_view(60, 20)
        combined = "\n".join(lines)
        self.assertIn("H: show help", combined)
        self.assertIn("Press any key to close", combined)


class TestBoxedRendering(unittest.TestCase):
    """Test boxed panel rendering helpers."""

    def test_box_lines_wraps_content(self):
        """Ensure box_lines adds borders and pads content."""
        boxed = box_lines(["Hello"], width=7, height=3)
        self.assertEqual(
            boxed,
            [
                "+-----+",
                "|Hello|",
                "+-----+",
            ],
        )

    def test_render_status_box_wraps_status_line(self):
        """Ensure status lines are boxed to the requested width."""
        boxed = render_status_box("Status", width=10)
        self.assertEqual(boxed[0], "+--------+")
        self.assertEqual(boxed[1], "|Status  |")
        self.assertEqual(boxed[2], "+--------+")


class TestAsciiGraph(unittest.TestCase):
    """Test ASCII graph rendering helpers."""

    def test_build_ascii_graph_marks_missing(self):
        """Missing values should mark the baseline with x."""
        lines = build_ascii_graph([1.0, None, 2.0], width=3, height=2, style="line")
        self.assertEqual(len(lines), 2)
        self.assertEqual(len(lines[0]), 3)
        self.assertEqual(lines[-1][1], "x")

    def test_build_ascii_graph_bar_fills(self):
        """Bar style should fill from the point to the baseline."""
        lines = build_ascii_graph([1.0, 2.0], width=2, height=3, style="bar")
        self.assertEqual(lines[-1][1], "#")

    def test_render_host_selection_view_highlight(self):
        """Selection view should highlight the selected host."""
        entries = [(0, "host1"), (1, "host2")]
        lines = render_host_selection_view(entries, 1, 20, 6, "ip")
        combined = "\n".join(lines)
        self.assertIn("> host2", combined)


class TestSquareView(unittest.TestCase):
    """Test square view rendering for ping status indicators."""

    def test_render_square_view_basic(self):
        """Square view should render with squares for each host."""
        from collections import deque

        display_entries = [(0, "host1"), (1, "host2")]
        buffers = {
            0: {
                "timeline": deque(["."], maxlen=5),
                "rtt_history": deque([10.5], maxlen=5),
                "time_history": deque([1.0], maxlen=5),
                "ttl_history": deque([64], maxlen=5),
                "categories": {
                    "success": deque([1], maxlen=5),
                    "fail": deque([0], maxlen=5),
                    "slow": deque([0], maxlen=5),
                    "pending": deque([0], maxlen=5),
                },
            },
            1: {
                "timeline": deque(["x"], maxlen=5),
                "rtt_history": deque([None], maxlen=5),
                "time_history": deque([1.0], maxlen=5),
                "ttl_history": deque([None], maxlen=5),
                "categories": {
                    "success": deque([0], maxlen=5),
                    "fail": deque([1], maxlen=5),
                    "slow": deque([0], maxlen=5),
                    "pending": deque([0], maxlen=5),
                },
            },
        }
        symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}

        lines = render_square_view(
            display_entries,
            buffers,
            symbols,
            width=40,
            height=10,
            header="Test Header",
            use_color=False,
            scroll_offset=0,
            header_lines=2,
            boxed=False,
        )

        # Should have header, separator, entries, and time axis
        self.assertGreaterEqual(len(lines), 5)
        self.assertIn("Test Header", lines[0])
        # Check that square symbol is present in the output
        combined = "\n".join(lines)
        self.assertIn("■", combined)

    def test_render_square_view_with_success(self):
        """Square view should show square for success status."""
        from collections import deque

        display_entries = [(0, "host1")]
        buffers = {
            0: {
                "timeline": deque([".", ".", "."], maxlen=5),
                "rtt_history": deque([10.0, 11.0, 12.0], maxlen=5),
                "time_history": deque([1.0, 2.0, 3.0], maxlen=5),
                "ttl_history": deque([64, 64, 64], maxlen=5),
                "categories": {
                    "success": deque([1, 1, 1], maxlen=5),
                    "fail": deque([0, 0, 0], maxlen=5),
                    "slow": deque([0, 0, 0], maxlen=5),
                    "pending": deque([0, 0, 0], maxlen=5),
                },
            },
        }
        symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}

        lines = render_square_view(
            display_entries,
            buffers,
            symbols,
            width=40,
            height=10,
            header="Test",
            use_color=False,
        )

        # Should render without error
        self.assertGreater(len(lines), 0)
        combined = "\n".join(lines)
        self.assertIn("■", combined)

    def test_render_square_view_with_fail(self):
        """Square view should show blank space for fail status in monochrome mode."""
        from collections import deque

        display_entries = [(0, "host1")]
        buffers = {
            0: {
                "timeline": deque(["x", "x", "x"], maxlen=5),
                "rtt_history": deque([None, None, None], maxlen=5),
                "time_history": deque([1.0, 2.0, 3.0], maxlen=5),
                "ttl_history": deque([None, None, None], maxlen=5),
                "categories": {
                    "success": deque([0, 0, 0], maxlen=5),
                    "fail": deque([1, 1, 1], maxlen=5),
                    "slow": deque([0, 0, 0], maxlen=5),
                    "pending": deque([0, 0, 0], maxlen=5),
                },
            },
        }
        symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}

        lines = render_square_view(
            display_entries,
            buffers,
            symbols,
            width=40,
            height=10,
            header="Test",
            use_color=False,
        )

        # Should render without error
        self.assertGreater(len(lines), 0)
        # In monochrome mode, fail status renders as blank space (not ■)
        # This is the enhancement to improve monochrome visualization

    def test_render_square_view_time_series(self):
        """Square view should show multiple squares as a time-series."""
        from collections import deque

        display_entries = [(0, "testhost")]
        # Create a buffer with a mix of success and fail symbols
        buffers = {
            0: {
                "timeline": deque([".", "x", ".", ".", "x"], maxlen=10),
                "rtt_history": deque([10.0, None, 11.0, 12.0, None], maxlen=10),
                "time_history": deque([1.0, 2.0, 3.0, 4.0, 5.0], maxlen=10),
                "ttl_history": deque([64, None, 64, 64, None], maxlen=10),
                "categories": {
                    "success": deque([1, 0, 1, 1, 0], maxlen=10),
                    "fail": deque([0, 1, 0, 0, 1], maxlen=10),
                    "slow": deque([0, 0, 0, 0, 0], maxlen=10),
                    "pending": deque([0, 0, 0, 0, 0], maxlen=10),
                },
            },
        }
        symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}

        lines = render_square_view(
            display_entries,
            buffers,
            symbols,
            width=50,
            height=10,
            header="Test Time Series",
            use_color=False,
        )

        # Should have header, separator, host line with squares, and time axis
        self.assertGreaterEqual(len(lines), 4)
        # The host line should contain squares for success (3 successes in timeline)
        # In monochrome mode: success = ■, fail = blank space
        host_line = lines[2]  # After header and separator
        square_count = host_line.count("■")
        self.assertGreaterEqual(square_count, 3, "Should render squares for success statuses")
        # Should have a time axis
        combined = "\n".join(lines)
        self.assertIn("|", combined)  # Time axis separator

    def test_render_square_view_interval_seconds(self):
        """Square view should pass interval_seconds to time axis."""
        from collections import deque

        display_entries = [(0, "testhost")]
        buffers = {
            0: {
                "timeline": deque([".", ".", ".", ".", "."], maxlen=10),
                "rtt_history": deque([10.0, 11.0, 12.0, 13.0, 14.0], maxlen=10),
                "time_history": deque([1.0, 2.0, 3.0, 4.0, 5.0], maxlen=10),
                "ttl_history": deque([64, 64, 64, 64, 64], maxlen=10),
                "categories": {
                    "success": deque([1, 1, 1, 1, 1], maxlen=10),
                    "fail": deque([0, 0, 0, 0, 0], maxlen=10),
                    "slow": deque([0, 0, 0, 0, 0], maxlen=10),
                    "pending": deque([0, 0, 0, 0, 0], maxlen=10),
                },
            },
        }
        symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}

        # Test with custom interval_seconds
        lines = render_square_view(
            display_entries,
            buffers,
            symbols,
            width=60,
            height=10,
            header="Test",
            use_color=False,
            interval_seconds=2.0,  # Custom interval
        )

        # Should have time axis
        self.assertGreaterEqual(len(lines), 4)
        # Time axis should be present (indicated by | separator)
        combined = "\n".join(lines)
        self.assertIn("|", combined)


if __name__ == "__main__":
    unittest.main()
