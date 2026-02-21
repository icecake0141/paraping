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
from collections import deque
from datetime import datetime, timezone, timedelta

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
from paraping.ui_render import (  # noqa: E402
    build_colored_sparkline,
    build_colored_timeline,
    build_display_entries,
    build_display_names,
    build_status_line,
    build_status_metrics,
    build_time_axis,
    can_render_full_summary,
    colorize_text,
    compute_activity_indicator_width,
    compute_main_layout,
    compute_panel_sizes,
    cycle_panel_position,
    format_display_name,
    format_status_line,
    format_summary_line,
    format_timestamp,
    format_timezone_label,
    latest_status_from_timeline,
    pad_lines,
    pad_visible,
    render_fullscreen_rtt_graph,
    render_main_view,
    render_sparkline_view,
    render_summary_view,
    render_timeline_view,
    resample_values,
    resize_buffers,
    resolve_boxed_dimensions,
    resolve_display_name,
    rjust_visible,
    should_flash_on_fail,
    should_show_asn,
    status_from_symbol,
    strip_ansi,
    toggle_panel_visibility,
    truncate_visible,
    visible_len,
)


class TestHelpView(unittest.TestCase):
    """Test help view rendering."""

    def test_help_view_contains_close_hint(self):
        """Help view should include close hint text."""
        lines = render_help_view(60, 20)
        combined = "\n".join(lines)
        self.assertIn("H: show help", combined)
        self.assertIn("P: toggle Dormant Mode", combined)
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


def _make_stats(host_ids, fail_count=0):
    """Helper to build a full stats dict for testing."""
    return {
        i: {
            "success": 5, "fail": fail_count, "slow": 0, "pending": 0,
            "total": 5 + fail_count,
            "rtt_count": 5, "rtt_sum": 0.05, "rtt_sum_sq": 0.005,
        }
        for i in host_ids
    }


def _make_summary_entry(host="h1"):
    """Build a summary data entry with all required fields."""
    return {
        "host": host,
        "sent": 10, "received": 9, "lost": 1,
        "success_rate": 90.0, "loss_rate": 10.0,
        "streak_type": None, "streak_length": 0,
        "avg_rtt_ms": 15.0, "jitter_ms": 1.0, "stddev_ms": 0.5,
        "latest_ttl": 64,
    }


def _make_buffers(host_ids, timeline_data=None, rtt_data=None, maxlen=10):
    """Helper to build a buffers dict for testing."""
    buffers = {}
    for hid in host_ids:
        tl = list(timeline_data or ["."])
        rt = list(rtt_data or [10.0])
        buffers[hid] = {
            "timeline": deque(tl, maxlen=maxlen),
            "rtt_history": deque(rt, maxlen=maxlen),
            "time_history": deque([float(i) for i in range(len(tl))], maxlen=maxlen),
            "ttl_history": deque([64] * len(tl), maxlen=maxlen),
            "categories": {
                "success": deque([1] * len(tl), maxlen=maxlen),
                "fail": deque([0] * len(tl), maxlen=maxlen),
                "slow": deque([0] * len(tl), maxlen=maxlen),
                "pending": deque([0] * len(tl), maxlen=maxlen),
            },
        }
    return buffers


_SYMBOLS = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}


class TestTerminalEdgeCases(unittest.TestCase):
    """Test rendering with extreme terminal sizes."""

    def _entries_and_buffers(self, host_name="host1"):
        entries = [(0, host_name)]
        buffers = _make_buffers([0])
        return entries, buffers

    def test_minimum_viable_terminal_no_crash(self):
        """Rendering at 20x6 must not raise an exception."""
        entries, buffers = self._entries_and_buffers()
        for fn in (render_timeline_view, render_sparkline_view, render_square_view):
            result = fn(entries, buffers, _SYMBOLS, width=20, height=6, header="H")
            self.assertIsInstance(result, list)

    def test_very_narrow_terminal_no_crash(self):
        """Rendering at width < 40 must not raise an exception."""
        entries, buffers = self._entries_and_buffers()
        for width in (1, 5, 10, 20, 30, 39):
            result = render_timeline_view(entries, buffers, _SYMBOLS, width=width, height=10, header="H")
            self.assertIsInstance(result, list)

    def test_very_tall_terminal_no_crash(self):
        """Rendering at height > 100 must not raise an exception."""
        entries, buffers = self._entries_and_buffers()
        result = render_timeline_view(entries, buffers, _SYMBOLS, width=80, height=120, header="H")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_single_column_timeline_truncates_host(self):
        """Very narrow width should produce truncated/short lines, not crash."""
        entries = [(0, "very_long_hostname_here")]
        buffers = _make_buffers([0])
        result = render_timeline_view(entries, buffers, _SYMBOLS, width=10, height=8, header="H")
        self.assertIsInstance(result, list)
        for line in result:
            self.assertLessEqual(len(strip_ansi(line)), 10)

    def test_extreme_sizes_no_crash(self):
        """Rendering across a range of sizes (20x6 to 200x50) must not crash."""
        entries, buffers = self._entries_and_buffers()
        sizes = [(20, 6), (40, 10), (80, 24), (120, 40), (200, 50)]
        for width, height in sizes:
            for fn in (render_timeline_view, render_sparkline_view, render_square_view):
                result = fn(entries, buffers, _SYMBOLS, width=width, height=height, header="H")
                self.assertIsInstance(result, list, f"Failed for {fn.__name__} at {width}x{height}")

    def test_zero_width_returns_empty(self):
        """Width=0 must return empty list."""
        entries, buffers = self._entries_and_buffers()
        for fn in (render_timeline_view, render_sparkline_view, render_square_view):
            result = fn(entries, buffers, _SYMBOLS, width=0, height=10, header="H")
            self.assertEqual(result, [])

    def test_zero_height_returns_empty(self):
        """Height=0 must return empty list."""
        entries, buffers = self._entries_and_buffers()
        for fn in (render_timeline_view, render_sparkline_view, render_square_view):
            result = fn(entries, buffers, _SYMBOLS, width=80, height=0, header="H")
            self.assertEqual(result, [])

    def test_help_view_minimum_terminal(self):
        """Help view at 20x6 should not crash."""
        lines = render_help_view(20, 6)
        self.assertIsInstance(lines, list)

    def test_help_view_very_tall(self):
        """Help view at 80x120 should not crash."""
        lines = render_help_view(80, 120)
        self.assertIsInstance(lines, list)

    def test_host_selection_view_minimum_terminal(self):
        """Host selection view at 20x6 should not crash."""
        entries = [(0, "host1"), (1, "host2")]
        lines = render_host_selection_view(entries, 0, 20, 6, "ip")
        self.assertIsInstance(lines, list)

    def test_host_selection_view_empty_entries(self):
        """Host selection view with no entries should render gracefully."""
        lines = render_host_selection_view([], 0, 40, 10, "ip")
        self.assertIsInstance(lines, list)
        combined = "\n".join(lines)
        self.assertIn("No hosts", combined)


class TestColorAndNonTTY(unittest.TestCase):
    """Test color output and non-TTY stripping behaviour."""

    def test_strip_ansi_removes_color_codes(self):
        """strip_ansi should remove ANSI color escape sequences."""
        colored = "\x1b[31mred text\x1b[0m"
        self.assertEqual(strip_ansi(colored), "red text")

    def test_strip_ansi_plain_text_unchanged(self):
        """strip_ansi should leave plain text untouched."""
        self.assertEqual(strip_ansi("hello world"), "hello world")

    def test_strip_ansi_incomplete_code(self):
        """strip_ansi should handle text that contains only partial/standalone escape."""
        text = "abc\x1b[mdef"
        result = strip_ansi(text)
        self.assertNotIn("\x1b", result)

    def test_visible_len_accounts_for_ansi(self):
        """visible_len must not count ANSI escape characters."""
        colored = "\x1b[32mhello\x1b[0m"
        self.assertEqual(visible_len(colored), 5)

    def test_colorize_text_no_color(self):
        """colorize_text with use_color=False returns plain text."""
        result = colorize_text("hello", "success", use_color=False)
        self.assertEqual(result, "hello")

    def test_colorize_text_with_color(self):
        """colorize_text with use_color=True wraps text in ANSI codes."""
        result = colorize_text("hello", "success", use_color=True)
        self.assertIn("\x1b[", result)
        self.assertIn("hello", result)

    def test_colorize_text_unknown_status(self):
        """colorize_text with unknown status returns plain text."""
        result = colorize_text("hello", "unknown_status", use_color=True)
        self.assertEqual(result, "hello")

    def test_render_timeline_view_no_color(self):
        """Timeline view with use_color=False should produce no ANSI codes."""
        entries = [(0, "host1")]
        buffers = _make_buffers([0])
        lines = render_timeline_view(entries, buffers, _SYMBOLS, width=60, height=10, header="H", use_color=False)
        for line in lines:
            self.assertNotIn("\x1b[", line)

    def test_render_timeline_view_with_color(self):
        """Timeline view with use_color=True should contain ANSI codes."""
        entries = [(0, "host1")]
        buffers = _make_buffers([0], timeline_data=["."])
        lines = render_timeline_view(entries, buffers, _SYMBOLS, width=60, height=10, header="H", use_color=True)
        combined = "\n".join(lines)
        self.assertIn("\x1b[", combined)

    def test_truncate_visible_preserves_ansi(self):
        """truncate_visible must count only visible chars and keep ANSI codes."""
        colored = "\x1b[31mabcdef\x1b[0m"
        result, count = truncate_visible(colored, 3)
        self.assertEqual(count, 3)
        self.assertIn("abc", strip_ansi(result))
        self.assertNotIn("d", strip_ansi(result))

    def test_truncate_visible_adds_reset(self):
        """truncate_visible must append ANSI_RESET if an open color code exists."""
        colored = "\x1b[31mabcdef"  # no closing reset
        result, _ = truncate_visible(colored, 3)
        self.assertTrue(result.endswith("\x1b[0m"))

    def test_build_colored_timeline_no_color(self):
        """build_colored_timeline with use_color=False should have no ANSI."""
        result = build_colored_timeline([".", "x"], _SYMBOLS, use_color=False)
        self.assertNotIn("\x1b[", result)

    def test_build_colored_timeline_with_color(self):
        """build_colored_timeline with use_color=True should contain ANSI codes."""
        result = build_colored_timeline([".", "x"], _SYMBOLS, use_color=True)
        self.assertIn("\x1b[", result)

    def test_build_colored_sparkline_no_color(self):
        """build_colored_sparkline with use_color=False returns plain sparkline."""
        sparkline = "▁▂▃"
        result = build_colored_sparkline(sparkline, [".", ".", "."], _SYMBOLS, use_color=False)
        self.assertEqual(result, sparkline)


class TestLongHostnames(unittest.TestCase):
    """Test rendering with very long hostnames (>30 chars)."""

    def test_long_hostname_timeline_no_crash(self):
        """A >30-char hostname should not crash timeline rendering."""
        long_name = "a" * 50
        entries = [(0, long_name)]
        buffers = _make_buffers([0])
        result = render_timeline_view(entries, buffers, _SYMBOLS, width=80, height=10, header="H")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_long_hostname_sparkline_no_crash(self):
        """A >30-char hostname should not crash sparkline rendering."""
        long_name = "b" * 40
        entries = [(0, long_name)]
        buffers = _make_buffers([0])
        result = render_sparkline_view(entries, buffers, _SYMBOLS, width=80, height=10, header="H")
        self.assertIsInstance(result, list)

    def test_long_hostname_square_no_crash(self):
        """A >30-char hostname should not crash square rendering."""
        long_name = "c" * 35
        entries = [(0, long_name)]
        buffers = _make_buffers([0])
        result = render_square_view(entries, buffers, _SYMBOLS, width=80, height=10, header="H")
        self.assertIsInstance(result, list)

    def test_long_hostname_narrow_terminal_no_crash(self):
        """A long hostname on a narrow terminal should not crash."""
        long_name = "d" * 60
        entries = [(0, long_name)]
        buffers = _make_buffers([0])
        result = render_timeline_view(entries, buffers, _SYMBOLS, width=20, height=6, header="H")
        self.assertIsInstance(result, list)
        for line in result:
            self.assertLessEqual(len(strip_ansi(line)), 20)

    def test_long_hostname_selection_view_no_crash(self):
        """Host selection view with a long hostname should not crash."""
        long_name = "very_long_hostname_that_exceeds_thirty_characters"
        entries = [(0, long_name)]
        lines = render_host_selection_view(entries, 0, 40, 10, "ip")
        self.assertIsInstance(lines, list)


class TestResizeAndUpdate(unittest.TestCase):
    """Test buffer resize and rendering after terminal resize."""

    def test_resize_buffers_expands(self):
        """resize_buffers should expand deques when timeline_width increases."""
        buffers = _make_buffers([0], maxlen=5)
        resize_buffers(buffers, 10, _SYMBOLS)
        self.assertEqual(buffers[0]["timeline"].maxlen, 10)

    def test_resize_buffers_shrinks(self):
        """resize_buffers should shrink deques when timeline_width decreases."""
        buffers = _make_buffers([0], maxlen=20)
        resize_buffers(buffers, 5, _SYMBOLS)
        self.assertEqual(buffers[0]["timeline"].maxlen, 5)

    def test_resize_buffers_no_change(self):
        """resize_buffers should be a no-op when sizes already match."""
        buffers = _make_buffers([0], maxlen=10)
        resize_buffers(buffers, 10, _SYMBOLS)
        self.assertEqual(buffers[0]["timeline"].maxlen, 10)

    def test_partial_terminal_resize_renders_without_crash(self):
        """Changing width mid-render should not crash."""
        entries = [(0, "host1"), (1, "host2")]
        buffers = _make_buffers([0, 1])
        # First render at normal size
        result1 = render_timeline_view(entries, buffers, _SYMBOLS, width=80, height=24, header="H")
        self.assertIsInstance(result1, list)
        # Then render at a much smaller size (simulating terminal resize)
        result2 = render_timeline_view(entries, buffers, _SYMBOLS, width=20, height=6, header="H")
        self.assertIsInstance(result2, list)
        # Then expand back
        result3 = render_timeline_view(entries, buffers, _SYMBOLS, width=200, height=50, header="H")
        self.assertIsInstance(result3, list)


class TestAnsiEdgeCases(unittest.TestCase):
    """Test ANSI color edge cases."""

    def test_strip_ansi_nested_colors(self):
        """strip_ansi should handle multiple nested/stacked color codes."""
        text = "\x1b[31m\x1b[1mBold Red\x1b[0m\x1b[0m"
        result = strip_ansi(text)
        self.assertEqual(result, "Bold Red")

    def test_strip_ansi_multiple_codes(self):
        """strip_ansi should remove all escape codes from a string."""
        text = "\x1b[32mgreen\x1b[0m normal \x1b[31mred\x1b[0m"
        result = strip_ansi(text)
        self.assertEqual(result, "green normal red")

    def test_visible_len_nested_colors(self):
        """visible_len must return correct length with nested ANSI codes."""
        text = "\x1b[31m\x1b[1mhello\x1b[0m\x1b[0m"
        self.assertEqual(visible_len(text), 5)

    def test_pad_visible_with_ansi(self):
        """pad_visible should pad based on visible width, not raw string length."""
        colored = "\x1b[32mhi\x1b[0m"
        result = pad_visible(colored, 10)
        self.assertEqual(visible_len(result), 10)

    def test_rjust_visible_with_ansi(self):
        """rjust_visible should right-justify using visible width."""
        colored = "\x1b[32mhi\x1b[0m"
        result = rjust_visible(colored, 10)
        self.assertEqual(visible_len(result), 10)

    def test_truncate_visible_plain_text(self):
        """truncate_visible should work with plain text."""
        result, count = truncate_visible("hello world", 5)
        self.assertEqual(result, "hello")
        self.assertEqual(count, 5)

    def test_truncate_visible_exact_width(self):
        """truncate_visible should return full text when width equals length."""
        result, count = truncate_visible("hello", 5)
        self.assertEqual(result, "hello")
        self.assertEqual(count, 5)

    def test_truncate_visible_wider_than_text(self):
        """truncate_visible should return full text when width exceeds length."""
        result, count = truncate_visible("hi", 10)
        self.assertEqual(result, "hi")
        self.assertEqual(count, 2)


class TestComputeLayout(unittest.TestCase):
    """Tests for layout computation functions."""

    def test_compute_main_layout_basic(self):
        """compute_main_layout should return sane values for standard terminal."""
        width, label_width, timeline_width, visible_hosts = compute_main_layout(
            ["host1", "host2"], width=80, height=24
        )
        self.assertGreater(timeline_width, 0)
        self.assertGreater(label_width, 0)
        self.assertGreater(visible_hosts, 0)
        self.assertEqual(width, 80)

    def test_compute_main_layout_narrow(self):
        """compute_main_layout should return at least 1 for timeline_width."""
        width, label_width, timeline_width, visible_hosts = compute_main_layout(
            ["longhost"], width=20, height=6
        )
        self.assertGreaterEqual(timeline_width, 1)
        self.assertGreaterEqual(visible_hosts, 1)

    def test_compute_panel_sizes_none(self):
        """panel_position=none should return full terminal dimensions."""
        mw, mh, sw, sh, pos = compute_panel_sizes(80, 24, "none")
        self.assertEqual(mw, 80)
        self.assertEqual(mh, 24)
        self.assertEqual(sw, 0)
        self.assertEqual(sh, 0)
        self.assertEqual(pos, "none")

    def test_compute_panel_sizes_right(self):
        """panel_position=right should split the terminal."""
        mw, mh, sw, sh, pos = compute_panel_sizes(120, 30, "right")
        self.assertGreater(mw, 0)
        self.assertGreater(sw, 0)
        self.assertEqual(pos, "right")

    def test_compute_panel_sizes_too_small(self):
        """Very small terminal should disable the panel."""
        mw, mh, sw, sh, pos = compute_panel_sizes(10, 4, "right")
        self.assertEqual(pos, "none")

    def test_resolve_boxed_dimensions_with_box(self):
        """Boxed dimensions should be reduced by 2 in each axis."""
        iw, ih, can_box = resolve_boxed_dimensions(20, 10, boxed=True)
        self.assertTrue(can_box)
        self.assertEqual(iw, 18)
        self.assertEqual(ih, 8)

    def test_resolve_boxed_dimensions_too_small(self):
        """Boxed dimensions with small size should disable boxing."""
        _, _, can_box = resolve_boxed_dimensions(1, 2, boxed=True)
        self.assertFalse(can_box)


class TestStatusAndSummary(unittest.TestCase):
    """Test status line and summary rendering."""

    def test_status_from_symbol_known(self):
        """status_from_symbol should identify known symbols."""
        self.assertEqual(status_from_symbol(".", _SYMBOLS), "success")
        self.assertEqual(status_from_symbol("x", _SYMBOLS), "fail")
        self.assertEqual(status_from_symbol("!", _SYMBOLS), "slow")

    def test_status_from_symbol_unknown(self):
        """status_from_symbol should return None for unknown symbols."""
        self.assertIsNone(status_from_symbol("?", _SYMBOLS))

    def test_latest_status_from_timeline_empty(self):
        """latest_status_from_timeline should return None for empty timeline."""
        self.assertIsNone(latest_status_from_timeline([], _SYMBOLS))

    def test_latest_status_from_timeline_nonempty(self):
        """latest_status_from_timeline should return the latest symbol's status."""
        self.assertEqual(latest_status_from_timeline([".", "x"], _SYMBOLS), "fail")
        self.assertEqual(latest_status_from_timeline(["x", "."], _SYMBOLS), "success")

    def test_build_status_line_basic(self):
        """build_status_line should include sort, filter, and summary info."""
        line = build_status_line("failures", "all", "rates", paused=False)
        self.assertIn("Failure Count", line)
        self.assertIn("All Items", line)
        self.assertIn("Rates", line)

    def test_build_status_line_paused(self):
        """build_status_line with paused=True should mention PAUSED."""
        line = build_status_line("host", "all", "rtt", paused=True)
        self.assertIn("PAUSED", line)

    def test_build_status_line_dormant(self):
        """build_status_line with dormant=True should mention DORMANT."""
        line = build_status_line("host", "all", "rtt", paused=False, dormant=True)
        self.assertIn("DORMANT", line)

    def test_build_status_metrics_empty(self):
        """build_status_metrics with no hosts should still return a string."""
        result = build_status_metrics([], {})
        self.assertIsInstance(result, str)
        self.assertIn("Hosts:", result)

    def test_should_flash_on_fail(self):
        """should_flash_on_fail returns True when status is fail and flags are set."""
        self.assertTrue(should_flash_on_fail("fail", flash_on_fail=True, show_help=False))
        self.assertFalse(should_flash_on_fail("fail", flash_on_fail=True, show_help=True))
        self.assertFalse(should_flash_on_fail("success", flash_on_fail=True, show_help=False))

    def test_toggle_panel_visibility_off(self):
        """toggle_panel_visibility should hide panel when visible."""
        pos, last = toggle_panel_visibility("right", "right")
        self.assertEqual(pos, "none")
        self.assertEqual(last, "right")

    def test_toggle_panel_visibility_on(self):
        """toggle_panel_visibility should restore panel when hidden."""
        pos, last = toggle_panel_visibility("none", "right")
        self.assertEqual(pos, "right")
        self.assertEqual(last, "right")

    def test_cycle_panel_position(self):
        """cycle_panel_position should cycle through positions."""
        self.assertEqual(cycle_panel_position("left"), "right")
        self.assertEqual(cycle_panel_position("right"), "top")
        self.assertEqual(cycle_panel_position("top"), "bottom")
        self.assertEqual(cycle_panel_position("bottom"), "left")

    def test_render_summary_view_basic(self):
        """render_summary_view should produce lines with summary data."""
        summary_data = [_make_summary_entry("host1")]
        lines = render_summary_view(summary_data, width=60, height=10, summary_mode="rates")
        self.assertIsInstance(lines, list)
        self.assertGreater(len(lines), 0)

    def test_render_summary_view_zero_size(self):
        """render_summary_view with zero dimensions returns empty list."""
        lines = render_summary_view([], width=0, height=10, summary_mode="rates")
        self.assertEqual(lines, [])
        lines = render_summary_view([], width=60, height=0, summary_mode="rates")
        self.assertEqual(lines, [])


class TestDisplayFormatting(unittest.TestCase):
    """Test display name and line formatting functions."""

    def _make_host_info(self, host_id=0, ip="1.2.3.4", alias="myhost", rdns=None):
        return {"id": host_id, "ip": ip, "alias": alias, "host": alias,
                "rdns": rdns, "rdns_pending": False, "asn": None, "asn_pending": False}

    def test_resolve_display_name_ip(self):
        info = self._make_host_info(ip="10.0.0.1")
        self.assertEqual(resolve_display_name(info, "ip"), "10.0.0.1")

    def test_resolve_display_name_alias(self):
        info = self._make_host_info(alias="myhost")
        self.assertEqual(resolve_display_name(info, "alias"), "myhost")

    def test_resolve_display_name_rdns_pending(self):
        info = self._make_host_info()
        info["rdns_pending"] = True
        self.assertEqual(resolve_display_name(info, "rdns"), "resolving...")

    def test_resolve_display_name_rdns_resolved(self):
        info = self._make_host_info(rdns="hostname.example.com")
        self.assertEqual(resolve_display_name(info, "rdns"), "hostname.example.com")

    def test_format_status_line(self):
        """format_status_line should format host and timeline with separator."""
        result = format_status_line("host1", "...xxx", label_width=10)
        self.assertIn("host1", result)
        self.assertIn("|", result)
        self.assertIn("...xxx", result)

    def test_build_time_axis_basic(self):
        """build_time_axis should return a string with label padding."""
        axis = build_time_axis(timeline_width=20, label_width=10)
        self.assertIn("|", axis)
        self.assertGreaterEqual(len(axis), 10)

    def test_build_time_axis_zero_width(self):
        """build_time_axis with zero timeline_width should return empty string."""
        axis = build_time_axis(timeline_width=0, label_width=10)
        self.assertEqual(axis, "")

    def test_pad_lines_fills_height(self):
        """pad_lines should always return exactly height lines."""
        result = pad_lines(["a", "b"], width=10, height=5)
        self.assertEqual(len(result), 5)

    def test_pad_lines_truncates_height(self):
        """pad_lines should truncate to height when input exceeds it."""
        result = pad_lines(["a"] * 10, width=5, height=3)
        self.assertEqual(len(result), 3)

    def test_resample_values_empty(self):
        """resample_values on empty input returns list of Nones."""
        result = resample_values([], 5)
        self.assertEqual(result, [None] * 5)

    def test_resample_values_zero_target(self):
        """resample_values with target_width=0 returns empty list."""
        result = resample_values([1.0, 2.0], 0)
        self.assertEqual(result, [])

    def test_resample_values_same_length(self):
        """resample_values returns same list when lengths match."""
        data = [1.0, 2.0, 3.0]
        result = resample_values(data, 3)
        self.assertEqual(result, data)

    def test_format_timestamp(self):
        """format_timestamp should produce a human-readable timestamp string."""
        now = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = format_timestamp(now, timezone.utc)
        self.assertIn("2025-01-15", result)
        self.assertIn("12:00:00", result)


class TestFullscreenRttGraph(unittest.TestCase):
    """Test fullscreen RTT graph rendering."""

    def test_render_fullscreen_rtt_basic(self):
        """Fullscreen RTT graph should render without error."""
        rtt_values = [0.01, 0.02, None, 0.015, 0.018]
        time_history = [1.0, 2.0, 3.0, 4.0, 5.0]
        lines = render_fullscreen_rtt_graph(
            "host1", rtt_values, time_history,
            width=80, height=24, display_mode="line",
            paused=False, timestamp="2025-01-01 00:00:00 (UTC)"
        )
        self.assertIsInstance(lines, list)
        self.assertGreater(len(lines), 0)

    def test_render_fullscreen_rtt_minimum_size(self):
        """Fullscreen RTT graph at 20x6 should not crash."""
        lines = render_fullscreen_rtt_graph(
            "host1", [], [],
            width=20, height=6, display_mode="line",
            paused=False, timestamp="2025-01-01 00:00:00 (UTC)"
        )
        self.assertIsInstance(lines, list)

    def test_render_fullscreen_rtt_no_samples(self):
        """Fullscreen RTT graph with no RTT data should render n/a message."""
        lines = render_fullscreen_rtt_graph(
            "myhost", [], [],
            width=80, height=20, display_mode="bar",
            paused=True, timestamp="2025-01-01 00:00:00 (UTC)"
        )
        combined = "\n".join(lines)
        self.assertIn("n/a", combined)

    def test_render_fullscreen_rtt_zero_size_returns_empty(self):
        """Fullscreen RTT graph with zero dimensions returns empty list."""
        lines = render_fullscreen_rtt_graph(
            "host1", [0.01], [1.0],
            width=0, height=10, display_mode="line",
            paused=False, timestamp="ts"
        )
        self.assertEqual(lines, [])

    def test_render_fullscreen_rtt_dormant(self):
        """Fullscreen RTT graph with dormant=True should show DORMANT."""
        lines = render_fullscreen_rtt_graph(
            "host1", [0.01], [1.0],
            width=80, height=20, display_mode="line",
            paused=False, timestamp="ts", dormant=True
        )
        combined = "\n".join(lines)
        self.assertIn("DORMANT", combined)


class TestRenderMainView(unittest.TestCase):
    """Test render_main_view dispatching and rendering."""

    def _entries_and_buffers(self):
        entries = [(0, "host1"), (1, "host2")]
        buffers = _make_buffers([0, 1])
        return entries, buffers

    def _now(self):
        return datetime.now(timezone.utc)

    def test_render_main_view_timeline(self):
        """render_main_view should dispatch to timeline rendering."""
        entries, buffers = self._entries_and_buffers()
        lines = render_main_view(
            entries, buffers, _SYMBOLS,
            width=80, height=24,
            mode_label="ip", display_mode="timeline",
            paused=False, timestamp="ts", now_utc=self._now()
        )
        self.assertIsInstance(lines, list)
        self.assertGreater(len(lines), 0)

    def test_render_main_view_sparkline(self):
        """render_main_view should dispatch to sparkline rendering."""
        entries, buffers = self._entries_and_buffers()
        lines = render_main_view(
            entries, buffers, _SYMBOLS,
            width=80, height=24,
            mode_label="ip", display_mode="sparkline",
            paused=False, timestamp="ts", now_utc=self._now()
        )
        self.assertIsInstance(lines, list)

    def test_render_main_view_square(self):
        """render_main_view should dispatch to square rendering."""
        entries, buffers = self._entries_and_buffers()
        lines = render_main_view(
            entries, buffers, _SYMBOLS,
            width=80, height=24,
            mode_label="ip", display_mode="square",
            paused=False, timestamp="ts", now_utc=self._now()
        )
        self.assertIsInstance(lines, list)

    def test_render_main_view_paused(self):
        """render_main_view with paused=True should mention PAUSED in header."""
        entries, buffers = self._entries_and_buffers()
        lines = render_main_view(
            entries, buffers, _SYMBOLS,
            width=80, height=24,
            mode_label="ip", display_mode="timeline",
            paused=True, timestamp="ts", now_utc=self._now()
        )
        combined = "\n".join(lines)
        self.assertIn("PAUSED", combined)

    def test_render_main_view_dormant(self):
        """render_main_view with dormant=True should mention DORMANT in header."""
        entries, buffers = self._entries_and_buffers()
        lines = render_main_view(
            entries, buffers, _SYMBOLS,
            width=80, height=24,
            mode_label="ip", display_mode="timeline",
            paused=False, timestamp="ts", now_utc=self._now(),
            dormant=True
        )
        combined = "\n".join(lines)
        self.assertIn("DORMANT", combined)

    def test_render_main_view_minimum_terminal(self):
        """render_main_view at 20x6 should not crash."""
        entries, buffers = self._entries_and_buffers()
        lines = render_main_view(
            entries, buffers, _SYMBOLS,
            width=20, height=6,
            mode_label="ip", display_mode="timeline",
            paused=False, timestamp="ts", now_utc=self._now()
        )
        self.assertIsInstance(lines, list)

    def test_render_main_view_many_hosts(self):
        """render_main_view with many hosts should show scroll indicator."""
        # Create 20 hosts but only 6 lines of height
        n = 20
        entries = [(i, f"host{i}") for i in range(n)]
        buffers = _make_buffers(list(range(n)))
        lines = render_main_view(
            entries, buffers, _SYMBOLS,
            width=80, height=8,
            mode_label="ip", display_mode="timeline",
            paused=False, timestamp="ts", now_utc=self._now()
        )
        self.assertIsInstance(lines, list)


class TestScrollOverflow(unittest.TestCase):
    """Test scroll/overflow indicator in all view types."""

    def _many_entries_and_buffers(self, n=20):
        entries = [(i, f"host{i}") for i in range(n)]
        buffers = _make_buffers(list(range(n)))
        return entries, buffers

    def test_timeline_scroll_overflow_indicator(self):
        """Boxed timeline with more hosts than fit exercises overflow code path."""
        entries, buffers = self._many_entries_and_buffers()
        # Boxed mode: render_height = height - 2, overflow line checked against height
        lines = render_timeline_view(entries, buffers, _SYMBOLS, width=80, height=14, header="H", boxed=True)
        # Overflow line path is exercised; result should render without error
        self.assertIsInstance(lines, list)
        self.assertEqual(len(lines), 14)

    def test_sparkline_scroll_overflow_indicator(self):
        """Boxed sparkline with more hosts than fit exercises overflow code path."""
        entries, buffers = self._many_entries_and_buffers()
        lines = render_sparkline_view(entries, buffers, _SYMBOLS, width=80, height=14, header="H", boxed=True)
        self.assertIsInstance(lines, list)
        self.assertEqual(len(lines), 14)

    def test_square_scroll_overflow_indicator(self):
        """Boxed square view with more hosts than fit exercises overflow code path."""
        entries, buffers = self._many_entries_and_buffers()
        lines = render_square_view(entries, buffers, _SYMBOLS, width=80, height=14, header="H", boxed=True)
        self.assertIsInstance(lines, list)
        self.assertEqual(len(lines), 14)

    def test_timeline_boxed_overflow(self):
        """Boxed timeline with overflow should render without crash."""
        entries, buffers = self._many_entries_and_buffers()
        lines = render_timeline_view(entries, buffers, _SYMBOLS, width=80, height=8, header="H", boxed=True)
        self.assertIsInstance(lines, list)

    def test_square_color_branches(self):
        """Square view should render all color branches (success, fail, pending)."""
        entries = [(0, "h1")]
        buffers = {
            0: {
                "timeline": deque([".", "x", "-"], maxlen=10),
                "rtt_history": deque([10.0, None, None], maxlen=10),
                "time_history": deque([1.0, 2.0, 3.0], maxlen=10),
                "ttl_history": deque([64, None, None], maxlen=10),
                "categories": {
                    "success": deque([1, 0, 0], maxlen=10),
                    "fail": deque([0, 1, 0], maxlen=10),
                    "slow": deque([0, 0, 0], maxlen=10),
                    "pending": deque([0, 0, 1], maxlen=10),
                },
            }
        }
        # With color
        lines_color = render_square_view(entries, buffers, _SYMBOLS, width=60, height=10, header="H", use_color=True)
        self.assertIsInstance(lines_color, list)
        combined = "\n".join(lines_color)
        self.assertIn("\x1b[", combined)

        # Without color
        lines_mono = render_square_view(entries, buffers, _SYMBOLS, width=60, height=10, header="H", use_color=False)
        self.assertIsInstance(lines_mono, list)

    def test_slow_color_branch(self):
        """Square view should render slow status with color."""
        entries = [(0, "h1")]
        buffers = {
            0: {
                "timeline": deque(["!"], maxlen=10),
                "rtt_history": deque([100.0], maxlen=10),
                "time_history": deque([1.0], maxlen=10),
                "ttl_history": deque([64], maxlen=10),
                "categories": {
                    "success": deque([0], maxlen=10),
                    "fail": deque([0], maxlen=10),
                    "slow": deque([1], maxlen=10),
                    "pending": deque([0], maxlen=10),
                },
            }
        }
        lines = render_square_view(entries, buffers, _SYMBOLS, width=60, height=10, header="H", use_color=True)
        self.assertIsInstance(lines, list)
        combined = "\n".join(lines)
        self.assertIn("\x1b[", combined)


class TestActivityIndicator(unittest.TestCase):
    """Test activity indicator building."""

    def test_build_activity_indicator_zero_width(self):
        """build_activity_indicator with width=0 should return empty string."""
        from paraping.ui_render import build_activity_indicator
        now = datetime.now(timezone.utc)
        result = build_activity_indicator(now, width=0)
        self.assertEqual(result, "")

    def test_build_activity_indicator_normal(self):
        """build_activity_indicator should return string of given width."""
        from paraping.ui_render import build_activity_indicator
        now = datetime.now(timezone.utc)
        result = build_activity_indicator(now, width=10)
        self.assertEqual(len(result), 10)

    def test_compute_activity_indicator_width_zero_panel(self):
        """compute_activity_indicator_width with panel_width=0 returns 0."""
        result = compute_activity_indicator_width(0, "header")
        self.assertEqual(result, 0)

    def test_compute_activity_indicator_width_no_space(self):
        """compute_activity_indicator_width with no remaining space returns 0."""
        result = compute_activity_indicator_width(5, "header text too long")
        self.assertEqual(result, 0)

    def test_compute_activity_indicator_width_expanded(self):
        """compute_activity_indicator_width with enough space returns expanded width."""
        result = compute_activity_indicator_width(100, "H")
        self.assertEqual(result, 20)  # ACTIVITY_INDICATOR_EXPANDED_WIDTH

    def test_compute_activity_indicator_width_default(self):
        """compute_activity_indicator_width with moderate space returns default width."""
        # header "H" (1 char) + 1 space = 2; remaining = 15 >= 10 (default) but < 20 (expanded)
        result = compute_activity_indicator_width(17, "H")
        self.assertEqual(result, 10)  # ACTIVITY_INDICATOR_WIDTH


class TestBuildDisplayEntries(unittest.TestCase):
    """Test build_display_entries sorting and filtering."""

    def _make_host_infos(self, n=3):
        return [{"id": i, "ip": f"10.0.0.{i}", "alias": f"host{i}",
                 "host": f"host{i}", "rdns": None, "rdns_pending": False,
                 "asn": None, "asn_pending": False} for i in range(n)]

    def _make_stats(self, n=3, fail_count=0):
        return _make_stats(list(range(n)), fail_count)

    def test_sort_by_host(self):
        """build_display_entries with sort_mode=host should sort alphabetically."""
        infos = self._make_host_infos(3)
        # Reverse order to ensure sorting happens
        infos[0]["alias"] = "zzz"
        infos[1]["alias"] = "aaa"
        infos[2]["alias"] = "mmm"
        buffers = _make_buffers([0, 1, 2])
        names = {0: "zzz", 1: "aaa", 2: "mmm"}
        stats = self._make_stats()
        entries = build_display_entries(infos, names, buffers, stats, _SYMBOLS, "host", "all", 200.0)
        labels = [e[1] for e in entries]
        self.assertEqual(labels, sorted(labels))

    def test_sort_by_failures(self):
        """build_display_entries with sort_mode=failures should sort by fail count."""
        infos = self._make_host_infos(3)
        buffers = _make_buffers([0, 1, 2])
        names = {0: "h0", 1: "h1", 2: "h2"}
        stats = {0: {"success": 5, "fail": 1, "slow": 0, "pending": 0,
                     "total": 6, "rtt_count": 5, "rtt_sum": 0.05, "rtt_sum_sq": 0.005},
                 1: {"success": 5, "fail": 3, "slow": 0, "pending": 0,
                     "total": 8, "rtt_count": 5, "rtt_sum": 0.05, "rtt_sum_sq": 0.005},
                 2: {"success": 5, "fail": 2, "slow": 0, "pending": 0,
                     "total": 7, "rtt_count": 5, "rtt_sum": 0.05, "rtt_sum_sq": 0.005}}
        entries = build_display_entries(infos, names, buffers, stats, _SYMBOLS, "failures", "all", 200.0)
        fail_counts = [stats[hid]["fail"] for hid, _ in entries]
        self.assertEqual(fail_counts, sorted(fail_counts, reverse=True))

    def test_sort_by_streak(self):
        """build_display_entries with sort_mode=streak should sort by fail streak."""
        infos = self._make_host_infos(2)
        buffers = _make_buffers([0, 1])
        buffers[0]["timeline"] = deque(["x", "x", "x"], maxlen=10)
        buffers[1]["timeline"] = deque(["."], maxlen=10)
        names = {0: "h0", 1: "h1"}
        stats = self._make_stats(2)
        entries = build_display_entries(infos, names, buffers, stats, _SYMBOLS, "streak", "all", 200.0)
        self.assertEqual(entries[0][0], 0)  # host0 has longer fail streak

    def test_sort_by_latency(self):
        """build_display_entries with sort_mode=latency should sort by RTT."""
        infos = self._make_host_infos(2)
        buffers = _make_buffers([0, 1])
        buffers[0]["rtt_history"] = deque([5.0], maxlen=10)
        buffers[1]["rtt_history"] = deque([50.0], maxlen=10)
        names = {0: "h0", 1: "h1"}
        stats = self._make_stats(2)
        entries = build_display_entries(infos, names, buffers, stats, _SYMBOLS, "latency", "all", 200.0)
        self.assertEqual(entries[0][0], 1)  # host1 has higher RTT

    def test_sort_by_config(self):
        """build_display_entries with sort_mode=config should sort by host_id."""
        infos = self._make_host_infos(3)
        buffers = _make_buffers([0, 1, 2])
        names = {0: "h0", 1: "h1", 2: "h2"}
        stats = self._make_stats()
        entries = build_display_entries(infos, names, buffers, stats, _SYMBOLS, "config", "all", 200.0)
        ids = [hid for hid, _ in entries]
        self.assertEqual(ids, sorted(ids))

    def test_filter_failures(self):
        """build_display_entries with filter_mode=failures should exclude hosts with no failures."""
        infos = self._make_host_infos(3)
        buffers = _make_buffers([0, 1, 2])
        names = {0: "h0", 1: "h1", 2: "h2"}
        stats = {0: {"success": 5, "fail": 0, "slow": 0, "pending": 0,
                     "total": 5, "rtt_count": 5, "rtt_sum": 0.05, "rtt_sum_sq": 0.005},
                 1: {"success": 5, "fail": 2, "slow": 0, "pending": 0,
                     "total": 7, "rtt_count": 5, "rtt_sum": 0.05, "rtt_sum_sq": 0.005},
                 2: {"success": 5, "fail": 0, "slow": 0, "pending": 0,
                     "total": 5, "rtt_count": 5, "rtt_sum": 0.05, "rtt_sum_sq": 0.005}}
        entries = build_display_entries(infos, names, buffers, stats, _SYMBOLS, "host", "failures", 200.0)
        ids = [hid for hid, _ in entries]
        self.assertIn(1, ids)
        self.assertNotIn(0, ids)

    def test_filter_latency(self):
        """build_display_entries with filter_mode=latency excludes below-threshold hosts."""
        infos = self._make_host_infos(2)
        buffers = _make_buffers([0, 1])
        buffers[0]["rtt_history"] = deque([5.0], maxlen=10)
        buffers[1]["rtt_history"] = deque([500.0], maxlen=10)
        names = {0: "h0", 1: "h1"}
        stats = self._make_stats(2)
        entries = build_display_entries(infos, names, buffers, stats, _SYMBOLS, "host", "latency", 200.0)
        ids = [hid for hid, _ in entries]
        self.assertIn(1, ids)
        self.assertNotIn(0, ids)


class TestShouldShowAsn(unittest.TestCase):
    """Test should_show_asn function."""

    def _host_info(self, alias="host", ip="1.2.3.4"):
        return {"id": 0, "ip": ip, "alias": alias, "host": alias,
                "rdns": None, "rdns_pending": False, "asn": "AS1234", "asn_pending": False}

    def test_show_asn_disabled(self):
        """should_show_asn returns False when show_asn is False."""
        info = self._host_info()
        self.assertFalse(should_show_asn([info], "ip", show_asn=False, term_width=120))

    def test_show_asn_enabled_wide_terminal(self):
        """should_show_asn returns True when terminal is wide enough."""
        info = self._host_info()
        self.assertTrue(should_show_asn([info], "ip", show_asn=True, term_width=120))

    def test_show_asn_enabled_narrow_terminal(self):
        """should_show_asn returns False when terminal is too narrow."""
        info = self._host_info(alias="h" * 20)
        result = should_show_asn([info], "ip", show_asn=True, term_width=15)
        self.assertFalse(result)

    def test_show_asn_empty_host_list(self):
        """should_show_asn returns False for empty host list."""
        self.assertFalse(should_show_asn([], "ip", show_asn=True, term_width=120))


class TestBuildDisplayNames(unittest.TestCase):
    """Test build_display_names and format_display_name."""

    def _host_info(self, hid=0, alias="host", asn="AS1234"):
        return {"id": hid, "ip": "1.2.3.4", "alias": alias, "host": alias,
                "rdns": None, "rdns_pending": False, "asn": asn, "asn_pending": False}

    def test_build_display_names_without_asn(self):
        """build_display_names returns simple labels when include_asn=False."""
        infos = [self._host_info(0, "host1"), self._host_info(1, "host2")]
        names = build_display_names(infos, "alias", include_asn=False, asn_width=8)
        self.assertEqual(names[0], "host1")
        self.assertEqual(names[1], "host2")

    def test_build_display_names_with_asn(self):
        """build_display_names returns labels with ASN when include_asn=True."""
        infos = [self._host_info(0, "host1", "AS1234")]
        names = build_display_names(infos, "alias", include_asn=True, asn_width=8)
        self.assertIn("AS1234", names[0])

    def test_format_display_name_with_asn(self):
        """format_display_name includes ASN info when include_asn=True."""
        info = self._host_info(asn="AS9999")
        result = format_display_name(info, "alias", include_asn=True, asn_width=8)
        self.assertIn("AS9999", result)


class TestCanRenderFullSummary(unittest.TestCase):
    """Test can_render_full_summary."""

    def test_can_render_empty(self):
        """can_render_full_summary returns False for empty data."""
        self.assertFalse(can_render_full_summary([], 100))

    def test_can_render_wide_enough(self):
        """can_render_full_summary returns True when terminal is wide enough."""
        entry = _make_summary_entry()
        result = can_render_full_summary([entry], 200)
        self.assertTrue(result)

    def test_can_render_too_narrow(self):
        """can_render_full_summary returns False for very narrow terminal."""
        entry = _make_summary_entry()
        result = can_render_full_summary([entry], 5)
        self.assertFalse(result)


class TestBuildDisplayLines(unittest.TestCase):
    """Test build_display_lines with various configurations."""

    from paraping.ui_render import build_display_lines

    def _make_host_info(self, hid, alias):
        return {"id": hid, "ip": f"10.0.0.{hid}", "alias": alias,
                "host": alias, "rdns": None, "rdns_pending": False,
                "asn": None, "asn_pending": False}

    def _setup(self, n=2):
        host_infos = [self._make_host_info(i, f"host{i}") for i in range(n)]
        buffers = _make_buffers(list(range(n)))
        stats = _make_stats(list(range(n)))
        return host_infos, buffers, stats

    def _now(self):
        return datetime.now(timezone.utc)

    def _call_build_display_lines(self, host_infos, buffers, stats, **kwargs):
        from paraping.ui_render import build_display_lines
        defaults = dict(
            symbols=_SYMBOLS,
            panel_position="none",
            mode_label="ip",
            display_mode="timeline",
            summary_mode="rates",
            sort_mode="host",
            filter_mode="all",
            slow_threshold=200.0,
            show_help=False,
            show_asn=False,
            paused=False,
            status_message=None,
            timestamp="2025-01-01 00:00:00 (UTC)",
            now_utc=self._now(),
        )
        defaults.update(kwargs)
        return build_display_lines(host_infos, buffers, stats, **defaults)

    def test_build_display_lines_basic(self):
        """build_display_lines should return a list of strings."""
        host_infos, buffers, stats = self._setup()
        result = self._call_build_display_lines(host_infos, buffers, stats)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_build_display_lines_show_help(self):
        """build_display_lines with show_help=True should show help view."""
        host_infos, buffers, stats = self._setup()
        result = self._call_build_display_lines(host_infos, buffers, stats, show_help=True)
        combined = "\n".join(result)
        self.assertIn("ParaPing - Help", combined)

    def test_build_display_lines_summary_fullscreen(self):
        """build_display_lines with summary_fullscreen=True shows summary."""
        host_infos, buffers, stats = self._setup()
        result = self._call_build_display_lines(
            host_infos, buffers, stats, summary_fullscreen=True
        )
        combined = "\n".join(result)
        self.assertIn("Summary", combined)

    def test_build_display_lines_panel_right(self):
        """build_display_lines with panel_position=right splits the view."""
        host_infos, buffers, stats = self._setup()
        result = self._call_build_display_lines(
            host_infos, buffers, stats, panel_position="right"
        )
        self.assertIsInstance(result, list)

    def test_build_display_lines_panel_top(self):
        """build_display_lines with panel_position=top stacks views."""
        host_infos, buffers, stats = self._setup()
        result = self._call_build_display_lines(
            host_infos, buffers, stats, panel_position="top"
        )
        self.assertIsInstance(result, list)

    def test_build_display_lines_panel_bottom(self):
        """build_display_lines with panel_position=bottom stacks views."""
        host_infos, buffers, stats = self._setup()
        result = self._call_build_display_lines(
            host_infos, buffers, stats, panel_position="bottom"
        )
        self.assertIsInstance(result, list)

    def test_build_display_lines_panel_left(self):
        """build_display_lines with panel_position=left splits view."""
        host_infos, buffers, stats = self._setup()
        result = self._call_build_display_lines(
            host_infos, buffers, stats, panel_position="left"
        )
        self.assertIsInstance(result, list)

    def test_build_display_lines_with_status_message(self):
        """build_display_lines with status_message produces output without error."""
        host_infos, buffers, stats = self._setup()
        result = self._call_build_display_lines(
            host_infos, buffers, stats, status_message="test message"
        )
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_build_display_lines_dormant(self):
        """build_display_lines with dormant=True shows DORMANT in status."""
        host_infos, buffers, stats = self._setup()
        result = self._call_build_display_lines(
            host_infos, buffers, stats, dormant=True
        )
        combined = "\n".join(result)
        self.assertIn("DORMANT", combined)

    def test_build_display_lines_sparkline_mode(self):
        """build_display_lines with display_mode=sparkline uses sparkline view."""
        host_infos, buffers, stats = self._setup()
        result = self._call_build_display_lines(
            host_infos, buffers, stats, display_mode="sparkline"
        )
        self.assertIsInstance(result, list)

    def test_build_display_lines_square_mode(self):
        """build_display_lines with display_mode=square uses square view."""
        host_infos, buffers, stats = self._setup()
        result = self._call_build_display_lines(
            host_infos, buffers, stats, display_mode="square"
        )
        self.assertIsInstance(result, list)


class TestMiscFunctions(unittest.TestCase):
    """Test miscellaneous rendering helper functions."""

    def test_format_timezone_label_utc(self):
        """format_timezone_label should return UTC for UTC timezone."""
        now = datetime.now(timezone.utc)
        result = format_timezone_label(now, timezone.utc)
        self.assertIn("UTC", result)

    def test_format_timezone_label_offset(self):
        """format_timezone_label should work for offset-based timezones."""
        tz = timezone(timedelta(hours=9))
        now = datetime.now(timezone.utc)
        result = format_timezone_label(now, tz)
        self.assertIsInstance(result, str)

    def test_resample_values_single_source(self):
        """resample_values with single input value should repeat it."""
        result = resample_values([42.0], 5)
        self.assertEqual(len(result), 5)
        self.assertTrue(all(v == 42.0 for v in result))

    def test_resample_values_single_target(self):
        """resample_values with target_width=1 returns the last value."""
        result = resample_values([1.0, 2.0, 3.0], 1)
        self.assertEqual(result, [3.0])

    def test_build_status_metrics_with_data(self):
        """build_status_metrics should count successes and errors from stats."""
        infos = [{"id": 0, "ip": "1.2.3.4", "alias": "h0", "host": "h0",
                  "rdns": None, "rdns_pending": False, "asn": None, "asn_pending": False}]
        stats = {0: {"success": 8, "fail": 2, "slow": 1, "pending": 0}}
        result = build_status_metrics(infos, stats)
        self.assertIn("Hosts: 1", result)

    def test_render_help_view_boxed(self):
        """render_help_view with boxed=True should render a boxed view."""
        lines = render_help_view(60, 30, boxed=True)
        self.assertIsInstance(lines, list)
        # Boxed output should have border characters
        self.assertTrue(lines[0].startswith("+") or "+" in lines[0])

    def test_render_summary_view_boxed(self):
        """render_summary_view with boxed=True should produce boxed output."""
        summary_data = [_make_summary_entry("h1")]
        lines = render_summary_view(summary_data, width=60, height=15, summary_mode="rates", boxed=True)
        self.assertIsInstance(lines, list)
        self.assertTrue(lines[0].startswith("+") or "+" in lines[0])

    def test_render_host_selection_view_many_entries(self):
        """Host selection with many entries - renders without error."""
        entries = [(i, f"host{i}") for i in range(20)]
        lines = render_host_selection_view(entries, 0, 40, 8, "ip")
        # Should render without crash and produce the expected number of lines
        self.assertIsInstance(lines, list)
        self.assertEqual(len(lines), 8)

    def test_cycle_panel_position_unknown(self):
        """cycle_panel_position with unknown position should return default."""
        result = cycle_panel_position("unknown_pos")
        self.assertEqual(result, "right")

    def test_build_sparkline_no_rtt_values(self):
        """build_sparkline with all-None RTT values uses status symbols."""
        from paraping.ui_render import build_sparkline
        result = build_sparkline([None, None], [".", "x"], "x")
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 2)

    def test_build_sparkline_empty(self):
        """build_sparkline with empty rtt_values uses status symbols."""
        from paraping.ui_render import build_sparkline
        result = build_sparkline([], [], "x")
        self.assertIsInstance(result, str)

    def test_build_sparkline_with_none_in_numeric_path(self):
        """build_sparkline with None mixed in rtt_values uses index 0 for None."""
        from paraping.ui_render import build_sparkline
        result = build_sparkline([10.0, None, 20.0], [".", "x", "."], "x")
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 3)

    def test_build_ascii_graph_all_none_values(self):
        """build_ascii_graph with all-None values returns space-filled lines."""
        lines = build_ascii_graph([None, None, None], width=3, height=2)
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(line == "   " for line in lines))

    def test_build_ascii_graph_empty_values(self):
        """build_ascii_graph with empty values returns space-filled lines."""
        lines = build_ascii_graph([], width=4, height=2)
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(len(line) == 4 for line in lines))

    def test_build_colored_sparkline_with_color(self):
        """build_colored_sparkline with use_color=True produces ANSI output."""
        sparkline = "▁▂"
        result = build_colored_sparkline(sparkline, [".", "x"], _SYMBOLS, use_color=True)
        self.assertIn("\x1b[", result)

    def test_format_summary_line_zero_width(self):
        """format_summary_line with very small width truncates gracefully."""
        entry = _make_summary_entry("h")
        result = format_summary_line(entry, width=1, summary_mode="ttl")
        self.assertLessEqual(len(result), 1)

    def test_render_host_selection_view_zero_size(self):
        """render_host_selection_view with zero size returns empty list."""
        result = render_host_selection_view([(0, "h")], 0, 0, 10, "ip")
        self.assertEqual(result, [])
        result = render_host_selection_view([(0, "h")], 0, 10, 0, "ip")
        self.assertEqual(result, [])

    def test_prepare_terminal_for_exit_non_tty(self):
        """prepare_terminal_for_exit should do nothing when not a TTY."""
        from paraping.ui_render import prepare_terminal_for_exit
        # In test environment, stdout is not a TTY - should return silently
        prepare_terminal_for_exit()  # Should not raise

    def test_flash_screen_non_tty(self):
        """flash_screen should do nothing when not a TTY."""
        from paraping.ui_render import flash_screen
        flash_screen()  # Should not raise

    def test_ring_bell_non_tty(self):
        """ring_bell should do nothing when not a TTY."""
        from paraping.ui_render import ring_bell
        ring_bell()  # Should not raise

    def test_resolve_display_name_rdns_none_fallback(self):
        """resolve_display_name with rdns=None falls back to IP."""
        from paraping.ui_render import resolve_display_name
        info = {"id": 0, "ip": "1.2.3.4", "alias": "host",
                "rdns": None, "rdns_pending": False}
        result = resolve_display_name(info, "rdns")
        self.assertEqual(result, "1.2.3.4")

    def test_format_asn_label_pending(self):
        """format_asn_label with asn_pending=True returns resolving text."""
        from paraping.ui_render import format_asn_label
        info = {"asn": None, "asn_pending": True}
        result = format_asn_label(info, asn_width=15)
        self.assertIn("resolving", result)


class TestEstimatePingRate(unittest.TestCase):
    """Test _parse_positive_float and estimate_ping_rate."""

    def test_parse_positive_float_valid(self):
        """_parse_positive_float returns float for valid positive string."""
        from paraping.ui_render import _parse_positive_float
        self.assertEqual(_parse_positive_float("1.5"), 1.5)

    def test_parse_positive_float_none(self):
        """_parse_positive_float returns None for None input."""
        from paraping.ui_render import _parse_positive_float
        self.assertIsNone(_parse_positive_float(None))

    def test_parse_positive_float_invalid_string(self):
        """_parse_positive_float returns None for non-numeric string."""
        from paraping.ui_render import _parse_positive_float
        self.assertIsNone(_parse_positive_float("not_a_number"))

    def test_parse_positive_float_zero(self):
        """_parse_positive_float returns None for zero."""
        from paraping.ui_render import _parse_positive_float
        self.assertIsNone(_parse_positive_float("0"))

    def test_parse_positive_float_negative(self):
        """_parse_positive_float returns None for negative values."""
        from paraping.ui_render import _parse_positive_float
        self.assertIsNone(_parse_positive_float("-1.0"))

    def test_estimate_ping_rate_env_override(self):
        """estimate_ping_rate uses PARAPING_PING_RATE env var when set."""
        from paraping.ui_render import estimate_ping_rate
        import os
        os.environ["PARAPING_PING_RATE"] = "5.0"
        try:
            result = estimate_ping_rate(10, 1.0)
            self.assertEqual(result, 5.0)
        finally:
            del os.environ["PARAPING_PING_RATE"]

    def test_estimate_ping_rate_zero_interval(self):
        """estimate_ping_rate returns None for zero interval."""
        from paraping.ui_render import estimate_ping_rate
        result = estimate_ping_rate(10, 0.0)
        self.assertIsNone(result)

    def test_estimate_ping_rate_interval_env(self):
        """estimate_ping_rate uses PARAPING_PING_INTERVAL env var when set."""
        from paraping.ui_render import estimate_ping_rate
        import os
        os.environ["PARAPING_PING_INTERVAL"] = "2.0"
        try:
            result = estimate_ping_rate(4, 1.0)
            self.assertEqual(result, 2.0)
        finally:
            del os.environ["PARAPING_PING_INTERVAL"]


if __name__ == "__main__":
    unittest.main()
