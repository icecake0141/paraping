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

import unittest
import os
import sys

# Add parent directory to path to import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import (
    render_help_view,
    box_lines,
    render_status_box,
    build_ascii_graph,
    render_host_selection_view,
)  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
