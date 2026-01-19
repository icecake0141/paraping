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
Unit tests for layout computation and terminal size handling
"""

import os
import sys
import unittest
from collections import deque
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Add parent directory to path to import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import build_display_lines, compute_main_layout, compute_panel_sizes, get_terminal_size  # noqa: E402


class TestLayoutComputation(unittest.TestCase):
    """Test layout computation functions"""

    def test_compute_main_layout_basic(self):
        """Test basic main layout computation"""
        host_labels = ["host1.com", "host2.com", "host3.com"]
        width, label_width, timeline_width, visible_hosts = compute_main_layout(host_labels, 80, 24, header_lines=2)
        self.assertEqual(width, 80)
        self.assertGreater(label_width, 0)
        self.assertGreater(timeline_width, 0)
        self.assertEqual(visible_hosts, 22)  # 24 - 2 header lines

    def test_compute_main_layout_with_long_hostnames(self):
        """Test layout with very long hostnames"""
        host_labels = ["very-long-hostname-that-exceeds-normal-length.example.com"]
        width, label_width, timeline_width, visible_hosts = compute_main_layout(host_labels, 80, 24)
        self.assertLessEqual(label_width, 80 // 3)  # Should be capped
        self.assertGreater(timeline_width, 0)

    def test_compute_panel_sizes_right(self):
        """Test panel size computation with right panel"""
        main_w, main_h, summ_w, summ_h, pos = compute_panel_sizes(80, 24, "right")
        self.assertGreater(main_w, 0)
        self.assertGreater(summ_w, 0)
        self.assertEqual(main_h, 24)
        self.assertEqual(summ_h, 24)
        self.assertEqual(pos, "right")

    def test_compute_panel_sizes_none(self):
        """Test panel size computation with no panel"""
        main_w, main_h, summ_w, summ_h, pos = compute_panel_sizes(80, 24, "none")
        self.assertEqual(main_w, 80)
        self.assertEqual(main_h, 24)
        self.assertEqual(summ_w, 0)
        self.assertEqual(summ_h, 0)
        self.assertEqual(pos, "none")

    def test_compute_panel_sizes_too_small(self):
        """Test panel computation falls back to none when terminal too small"""
        main_w, main_h, summ_w, summ_h, pos = compute_panel_sizes(10, 5, "right")
        self.assertEqual(pos, "none")

    @patch("paraping.ui_render.get_terminal_size")
    def test_bottom_panel_uses_extra_space(self, mock_term_size):
        """Bottom panel expands when main view needs fewer rows."""
        mock_term_size.return_value = os.terminal_size((80, 23))

        host_infos = [
            {
                "id": idx,
                "host": f"host{idx}.com",
                "alias": f"host{idx}.com",
                "ip": f"192.0.2.{idx + 1}",
                "rdns": None,
                "asn": None,
            }
            for idx in range(6)
        ]
        buffers = {
            idx: {
                "timeline": deque(["."] * 5),
                "rtt_history": deque([0.01] * 5),
                "time_history": deque([1000.0] * 5),
                "ttl_history": deque([64] * 5),
                "categories": {
                    "success": deque([1]),
                    "slow": deque([]),
                    "fail": deque([]),
                },
            }
            for idx in range(6)
        }
        stats = {
            idx: {
                "success": 1,
                "slow": 0,
                "fail": 0,
                "total": 1,
                "rtt_sum": 0.01,
                "rtt_count": 1,
            }
            for idx in range(6)
        }
        symbols = {"success": ".", "fail": "x", "slow": "!"}

        lines = build_display_lines(
            host_infos=host_infos,
            buffers=buffers,
            stats=stats,
            symbols=symbols,
            panel_position="bottom",
            mode_label="ip",
            display_mode="timeline",
            summary_mode="rates",
            sort_mode="host",
            filter_mode="all",
            slow_threshold=0.5,
            show_help=False,
            show_asn=False,
            paused=False,
            status_message=None,
            timestamp="2026-01-12 08:15:20 (UTC)",
            now_utc=datetime(2026, 1, 12, 8, 15, 20, tzinfo=timezone.utc),
        )

        summary_line_index = next(index for index, line in enumerate(lines) if "Summary (" in line)
        self.assertEqual(summary_line_index, 12)
        self.assertEqual(len(lines), 23)


class TestTerminalSize(unittest.TestCase):
    """Test terminal size retrieval function"""

    @patch("paraping.cli.os.get_terminal_size")
    @patch("paraping.cli.sys.stdout")
    def test_get_terminal_size_from_stdout(self, mock_stdout, mock_os_get_size):
        """Test getting terminal size from stdout"""
        mock_stdout.isatty.return_value = True
        mock_stdout.fileno.return_value = 1
        mock_os_get_size.return_value = MagicMock(columns=100, lines=50)

        result = get_terminal_size()

        self.assertEqual(result.columns, 100)
        self.assertEqual(result.lines, 50)
        mock_os_get_size.assert_called_once_with(1)

    @patch("paraping.cli.os.get_terminal_size")
    @patch("paraping.cli.sys.stdout")
    @patch("paraping.cli.sys.stderr")
    def test_get_terminal_size_fallback_to_stderr(self, mock_stderr, mock_stdout, mock_os_get_size):
        """Test fallback to stderr when stdout fails"""
        mock_stdout.isatty.return_value = False
        mock_stderr.isatty.return_value = True
        mock_stderr.fileno.return_value = 2
        mock_os_get_size.return_value = MagicMock(columns=120, lines=40)

        result = get_terminal_size()

        self.assertEqual(result.columns, 120)
        self.assertEqual(result.lines, 40)

    @patch("paraping.cli.os.get_terminal_size")
    @patch("paraping.cli.sys.stdout")
    @patch("paraping.cli.sys.stderr")
    @patch("paraping.cli.sys.stdin")
    def test_get_terminal_size_fallback_to_default(self, mock_stdin, mock_stderr, mock_stdout, mock_os_get_size):
        """Test fallback to default size when no tty available"""
        mock_stdout.isatty.return_value = False
        mock_stderr.isatty.return_value = False
        mock_stdin.isatty.return_value = False

        result = get_terminal_size(fallback=(80, 24))

        self.assertEqual(result.columns, 80)
        self.assertEqual(result.lines, 24)

    @patch("paraping.cli.os.get_terminal_size")
    @patch("paraping.cli.sys.stdout")
    def test_get_terminal_size_handles_os_error(self, mock_stdout, mock_os_get_size):
        """Test handling of OSError when querying terminal size"""
        mock_stdout.isatty.return_value = True
        mock_stdout.fileno.return_value = 1
        mock_os_get_size.side_effect = OSError("Not a terminal")

        result = get_terminal_size(fallback=(80, 24))

        self.assertEqual(result.columns, 80)
        self.assertEqual(result.lines, 24)

    def test_get_terminal_size_ignores_env_vars(self):
        """Test that get_terminal_size ignores COLUMNS/LINES env vars"""
        # Set environment variables
        original_columns = os.environ.get("COLUMNS")
        original_lines = os.environ.get("LINES")

        try:
            os.environ["COLUMNS"] = "50"
            os.environ["LINES"] = "20"

            # Our function should bypass env vars and query actual terminal
            # If running in a TTY, it should get the real size, not 50x20
            result = get_terminal_size(fallback=(80, 24))

            # The result should either be the actual terminal size
            # (not 50x20) or the fallback (80x24) if no TTY available
            # It should NOT be 50x20 from the env vars
            self.assertNotEqual((result.columns, result.lines), (50, 20))
        finally:
            # Restore original env vars
            if original_columns is not None:
                os.environ["COLUMNS"] = original_columns
            else:
                os.environ.pop("COLUMNS", None)
            if original_lines is not None:
                os.environ["LINES"] = original_lines
            else:
                os.environ.pop("LINES", None)


if __name__ == "__main__":
    unittest.main()
