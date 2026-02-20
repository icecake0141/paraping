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
Unit tests for display formatting and summary data computation
"""

import os
import socket
import sys
import unittest
from collections import deque
from datetime import datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

# Add parent directory to path to import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import (  # noqa: E402
    build_activity_indicator,
    build_colored_sparkline,
    build_colored_timeline,
    build_display_names,
    build_host_infos,
    build_sparkline,
    build_status_line,
    build_status_metrics,
    compute_summary_data,
    format_display_name,
    format_timestamp,
    format_timezone_label,
    render_summary_view,
)


class TestDisplayNames(unittest.TestCase):
    """Test display name building functions"""

    def test_format_display_name_ip_mode(self):
        """Test display name formatting in IP mode"""
        host_info = {
            "id": 0,
            "host": "example.com",
            "alias": "example.com",
            "ip": "93.184.216.34",
            "rdns": None,
            "asn": None,
        }
        name = format_display_name(host_info, "ip", False, 8)
        self.assertEqual(name, "93.184.216.34")

    def test_format_display_name_rdns_mode(self):
        """Test display name formatting in rDNS mode"""
        host_info = {
            "id": 0,
            "host": "example.com",
            "alias": "example.com",
            "ip": "93.184.216.34",
            "rdns": "example.com",
            "rdns_pending": False,
            "asn": None,
        }
        name = format_display_name(host_info, "rdns", False, 8)
        self.assertEqual(name, "example.com")

    def test_format_display_name_alias_mode(self):
        """Test display name formatting in alias mode"""
        host_info = {
            "id": 0,
            "host": "example.com",
            "alias": "my-server",
            "ip": "93.184.216.34",
            "rdns": None,
            "asn": None,
        }
        name = format_display_name(host_info, "alias", False, 8)
        self.assertEqual(name, "my-server")

    def test_format_display_name_with_asn(self):
        """Test display name formatting with ASN"""
        host_info = {
            "id": 0,
            "host": "example.com",
            "alias": "example.com",
            "ip": "93.184.216.34",
            "rdns": None,
            "asn": "AS15133",
            "asn_pending": False,
        }
        name = format_display_name(host_info, "ip", True, 8)
        self.assertIn("93.184.216.34", name)
        self.assertIn("AS15133", name)

    def test_build_display_names(self):
        """Test building display names for multiple hosts"""
        host_infos = [
            {
                "id": 0,
                "host": "h1.com",
                "alias": "h1",
                "ip": "1.1.1.1",
                "rdns": None,
                "asn": None,
            },
            {
                "id": 1,
                "host": "h2.com",
                "alias": "h2",
                "ip": "2.2.2.2",
                "rdns": None,
                "asn": None,
            },
        ]
        names = build_display_names(host_infos, "alias", False, 8)
        self.assertEqual(names[0], "h1")
        self.assertEqual(names[1], "h2")


class TestSummaryData(unittest.TestCase):
    """Test summary data computation"""

    def test_compute_summary_data_basic(self):
        """Test basic summary data computation"""
        host_infos = [
            {"id": 0, "alias": "host1.com"},
        ]
        display_names = {0: "host1.com"}
        buffers = {
            0: {
                "timeline": deque([".", ".", "x", "."]),
                "rtt_history": deque([0.01, 0.02, None, 0.015]),
                "ttl_history": deque([64, 64, None, 64]),
                "categories": {
                    "success": deque([1, 2, 4]),
                    "slow": deque([]),
                    "fail": deque([3]),
                },
            }
        }
        stats = {
            0: {
                "success": 3,
                "slow": 0,
                "fail": 1,
                "total": 4,
                "rtt_sum": 0.045,
                "rtt_sum_sq": 0.000725,
                "rtt_count": 3,
            }
        }
        symbols = {"success": ".", "fail": "x", "slow": "!"}

        summary = compute_summary_data(host_infos, display_names, buffers, stats, symbols)

        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["host"], "host1.com")
        self.assertEqual(summary[0]["success_rate"], 75.0)
        self.assertEqual(summary[0]["loss_rate"], 25.0)
        self.assertIsNotNone(summary[0]["avg_rtt_ms"])
        self.assertAlmostEqual(summary[0]["jitter_ms"], 7.5, places=1)
        self.assertAlmostEqual(summary[0]["stddev_ms"], 4.1, places=1)
        self.assertEqual(summary[0]["latest_ttl"], 64)

    def test_compute_summary_data_all_success(self):
        """Test summary with all successful pings"""
        host_infos = [{"id": 0, "alias": "host1.com"}]
        display_names = {0: "host1.com"}
        buffers = {
            0: {
                "timeline": deque([".", ".", ".", "."]),
                "rtt_history": deque([0.01, 0.02, 0.015, 0.018]),
                "ttl_history": deque([64, 64, 64, 64]),
                "categories": {
                    "success": deque([1, 2, 3, 4]),
                    "slow": deque([]),
                    "fail": deque([]),
                },
            }
        }
        stats = {
            0: {
                "success": 4,
                "slow": 0,
                "fail": 0,
                "total": 4,
                "rtt_sum": 0.063,
                "rtt_sum_sq": 0.001049,
                "rtt_count": 4,
            }
        }
        symbols = {"success": ".", "fail": "x", "slow": "!"}

        summary = compute_summary_data(host_infos, display_names, buffers, stats, symbols)

        self.assertEqual(summary[0]["success_rate"], 100.0)
        self.assertEqual(summary[0]["loss_rate"], 0.0)
        self.assertEqual(summary[0]["streak_type"], "success")

    def test_compute_summary_data_respects_ordered_host_ids(self):
        """Test summary data order follows ordered host ids."""
        host_infos = [
            {"id": 0, "alias": "host1.com"},
            {"id": 1, "alias": "host2.com"},
        ]
        display_names = {0: "alpha", 1: "beta"}
        buffers = {
            0: {
                "timeline": deque(["."]),
                "rtt_history": deque([0.01]),
                "ttl_history": deque([64]),
                "categories": {
                    "success": deque([1]),
                    "slow": deque([]),
                    "fail": deque([]),
                },
            },
            1: {
                "timeline": deque(["x"]),
                "rtt_history": deque([None]),
                "ttl_history": deque([None]),
                "categories": {
                    "success": deque([]),
                    "slow": deque([]),
                    "fail": deque([1]),
                },
            },
        }
        stats = {
            0: {
                "success": 1,
                "slow": 0,
                "fail": 0,
                "total": 1,
                "rtt_sum": 0.01,
                "rtt_sum_sq": 0.0001,
                "rtt_count": 1,
            },
            1: {
                "success": 0,
                "slow": 0,
                "fail": 1,
                "total": 1,
                "rtt_sum": 0.0,
                "rtt_sum_sq": 0.0,
                "rtt_count": 0,
            },
        }
        symbols = {"success": ".", "fail": "x", "slow": "!"}

        summary = compute_summary_data(
            host_infos,
            display_names,
            buffers,
            stats,
            symbols,
            ordered_host_ids=[1, 0],
        )

        self.assertEqual([entry["host"] for entry in summary], ["beta", "alpha"])

    def test_render_summary_view_fits_width(self):
        """Test that summary view lines don't exceed specified width"""
        summary_data = [
            {
                "host": "very-long-hostname-with-asn-info.example.com AS12345",
                "sent": 22,
                "received": 21,
                "lost": 1,
                "success_rate": 95.5,
                "loss_rate": 4.5,
                "streak_type": "success",
                "streak_length": 10,
                "avg_rtt_ms": 42.3,
                "jitter_ms": 3.2,
                "stddev_ms": 4.1,
            }
        ]

        width = 40
        height = 10
        lines = render_summary_view(summary_data, width, height, "rates")

        # All lines should be exactly 'width' characters
        for line in lines:
            self.assertEqual(len(line), width, f"Line '{line}' has length {len(line)}, expected {width}")

    def test_render_summary_view_truncates_long_hostnames(self):
        """Test that long hostnames are truncated to fit"""
        summary_data = [
            {
                "host": "extremely-long-hostname-that-definitely-exceeds-width.example.com AS99999",
                "sent": 10,
                "received": 10,
                "lost": 0,
                "success_rate": 100.0,
                "loss_rate": 0.0,
                "streak_type": "success",
                "streak_length": 5,
                "avg_rtt_ms": 25.0,
                "jitter_ms": 2.5,
                "stddev_ms": 3.2,
            }
        ]

        # Use a reasonable width that can fit the status info
        width = 50
        height = 10
        lines = render_summary_view(summary_data, width, height, "rates")

        # Check all lines fit within width
        for line in lines:
            self.assertEqual(len(line), width)

        # The host info line should contain essential info when width is sufficient
        # Line 0: "Summary (Rates)", Line 1: separator, Line 2: legend, Line 3: first host
        host_line = lines[3]  # First line is "Summary", second is separator, third is legend
        self.assertIn("10/10/0", host_line)
        self.assertIn("%", host_line)

    def test_render_summary_view_multiple_hosts(self):
        """Test summary view with multiple hosts respects width"""
        summary_data = [
            {
                "host": "host1.example.com AS1111",
                "sent": 3,
                "received": 3,
                "lost": 0,
                "success_rate": 100.0,
                "loss_rate": 0.0,
                "streak_type": "success",
                "streak_length": 3,
                "avg_rtt_ms": 10.5,
                "jitter_ms": 1.1,
                "stddev_ms": 2.2,
            },
            {
                "host": "very-long-host2.example.com AS22222",
                "sent": 10,
                "received": 9,
                "lost": 1,
                "success_rate": 90.0,
                "loss_rate": 10.0,
                "streak_type": "fail",
                "streak_length": 2,
                "avg_rtt_ms": 45.2,
                "jitter_ms": 3.3,
                "stddev_ms": 4.4,
            },
        ]

        width = 35
        height = 20
        lines = render_summary_view(summary_data, width, height, "rates")

        # All lines should fit within width
        for line in lines:
            self.assertEqual(len(line), width)

    def test_render_summary_view_prefers_all_fields_when_space_allows(self):
        """Test summary view shows all fields when space allows"""
        summary_data = [
            {
                "host": "example.com",
                "sent": 10,
                "received": 10,
                "lost": 0,
                "success_rate": 100.0,
                "loss_rate": 0.0,
                "streak_type": "success",
                "streak_length": 5,
                "avg_rtt_ms": 25.0,
                "jitter_ms": 2.5,
                "stddev_ms": 3.2,
                "latest_ttl": 64,
            }
        ]

        width = 120
        height = 6
        lines = render_summary_view(summary_data, width, height, "rates", prefer_all=True)

        self.assertIn("Summary (All)", lines[0])
        combined = "\n".join(lines)
        self.assertIn("10/10/0 loss 0.0%", combined)
        self.assertIn("avg rtt 25.0 ms", combined)
        self.assertIn("jitter 2.5 ms", combined)
        self.assertIn("stddev 3.2 ms", combined)
        self.assertIn("ttl 64", combined)
        self.assertIn("streak S5", combined)

    def test_render_summary_view_falls_back_when_space_is_tight(self):
        """Test summary view falls back to selected mode when space is tight"""
        summary_data = [
            {
                "host": "example.com",
                "sent": 10,
                "received": 10,
                "lost": 0,
                "success_rate": 100.0,
                "loss_rate": 0.0,
                "streak_type": "success",
                "streak_length": 5,
                "avg_rtt_ms": 25.0,
                "jitter_ms": 2.5,
                "stddev_ms": 3.2,
                "latest_ttl": 64,
            }
        ]

        width = 60
        height = 6
        lines = render_summary_view(summary_data, width, height, "rtt", prefer_all=True)

        self.assertIn("Summary (Avg RTT)", lines[0])
        combined = "\n".join(lines)
        self.assertIn("avg rtt 25.0 ms", combined)
        self.assertIn("jitter 2.5 ms", combined)
        self.assertIn("stddev 3.2 ms", combined)
        self.assertNotIn("ttl 64", combined)
        self.assertNotIn("streak", combined)

    def test_render_summary_view_includes_legend_for_rates_mode(self):
        """Test that summary view includes Snt/Rcv/Los legend in rates mode"""
        summary_data = [
            {
                "host": "example.com",
                "sent": 10,
                "received": 9,
                "lost": 1,
                "success_rate": 90.0,
                "loss_rate": 10.0,
                "streak_type": "fail",
                "streak_length": 1,
                "avg_rtt_ms": 25.0,
                "jitter_ms": 2.5,
                "stddev_ms": 3.2,
            }
        ]

        width = 60
        height = 10
        lines = render_summary_view(summary_data, width, height, "rates")

        # Check that legend is present
        legend_found = False
        for line in lines:
            if "Snt/Rcv/Los" in line and "Sent/Received/Lost" in line:
                legend_found = True
                break
        self.assertTrue(legend_found, "Legend for Snt/Rcv/Los should be present in rates mode")

    def test_render_summary_view_no_legend_for_other_modes(self):
        """Test that summary view does not include Snt/Rcv/Los legend in non-rates modes"""
        summary_data = [
            {
                "host": "example.com",
                "sent": 10,
                "received": 9,
                "lost": 1,
                "success_rate": 90.0,
                "loss_rate": 10.0,
                "streak_type": "fail",
                "streak_length": 1,
                "avg_rtt_ms": 25.0,
                "jitter_ms": 2.5,
                "stddev_ms": 3.2,
                "latest_ttl": 64,
            }
        ]

        width = 60
        height = 10

        # Test RTT mode
        lines_rtt = render_summary_view(summary_data, width, height, "rtt")
        legend_in_rtt = any("Snt/Rcv/Los" in line for line in lines_rtt)
        self.assertFalse(legend_in_rtt, "Legend should not be present in rtt mode")

        # Test TTL mode
        lines_ttl = render_summary_view(summary_data, width, height, "ttl")
        legend_in_ttl = any("Snt/Rcv/Los" in line for line in lines_ttl)
        self.assertFalse(legend_in_ttl, "Legend should not be present in ttl mode")

        # Test streak mode
        lines_streak = render_summary_view(summary_data, width, height, "streak")
        legend_in_streak = any("Snt/Rcv/Los" in line for line in lines_streak)
        self.assertFalse(legend_in_streak, "Legend should not be present in streak mode")


class TestTimezoneFormatting(unittest.TestCase):
    """Test timezone handling functions"""

    def test_format_timestamp_utc(self):
        """Test timestamp formatting with UTC"""
        now_utc = datetime(2025, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        result = format_timestamp(now_utc, timezone.utc)
        self.assertIn("2025-01-15", result)
        self.assertIn("12:30:45", result)
        self.assertIn("UTC", result)

    def test_format_timestamp_with_timezone(self):
        """Test timestamp formatting with non-UTC timezone"""
        now_utc = datetime(2025, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        tokyo_tz = ZoneInfo("Asia/Tokyo")
        result = format_timestamp(now_utc, tokyo_tz)
        self.assertIn("2025-01-15", result)
        # Tokyo is UTC+9, so 12:30 UTC = 21:30 JST
        self.assertIn("21:30:45", result)

    def test_format_timezone_label_utc(self):
        """Test timezone label formatting for UTC"""
        now_utc = datetime(2025, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        label = format_timezone_label(now_utc, timezone.utc)
        self.assertEqual(label, "UTC")


class TestHostInfoBuilding(unittest.TestCase):
    """Test host info building functions"""

    @patch("paraping.core.socket.getaddrinfo")
    def test_build_host_infos_with_hostname(self, mock_getaddrinfo):
        """Test building host infos with resolvable hostname"""
        mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_RAW, 0, "", ("93.184.216.34", 0))]

        host_infos, host_map = build_host_infos(["example.com"])

        self.assertEqual(len(host_infos), 1)
        self.assertEqual(host_infos[0]["host"], "example.com")
        self.assertEqual(host_infos[0]["ip"], "93.184.216.34")
        self.assertEqual(host_infos[0]["alias"], "example.com")
        self.assertIn("example.com", host_map)

    @patch("paraping.core.socket.getaddrinfo")
    def test_build_host_infos_with_ip(self, mock_getaddrinfo):
        """Test building host infos with IP address"""
        mock_getaddrinfo.side_effect = OSError()

        host_infos, host_map = build_host_infos(["192.168.1.1"])

        self.assertEqual(len(host_infos), 1)
        self.assertEqual(host_infos[0]["ip"], "192.168.1.1")

    @patch("paraping.core.socket.getaddrinfo")
    def test_build_host_infos_multiple_hosts(self, mock_getaddrinfo):
        """Test building host infos with multiple hosts"""
        mock_getaddrinfo.side_effect = [
            [(socket.AF_INET, socket.SOCK_RAW, 0, "", ("1.1.1.1", 0))],
            [(socket.AF_INET, socket.SOCK_RAW, 0, "", ("2.2.2.2", 0))],
            [(socket.AF_INET, socket.SOCK_RAW, 0, "", ("3.3.3.3", 0))],
        ]

        host_infos, host_map = build_host_infos(["h1.com", "h2.com", "h3.com"])

        self.assertEqual(len(host_infos), 3)
        self.assertEqual(host_infos[0]["ip"], "1.1.1.1")
        self.assertEqual(host_infos[1]["ip"], "2.2.2.2")
        self.assertEqual(host_infos[2]["ip"], "3.3.3.3")


class TestSparklineBuilding(unittest.TestCase):
    """Test sparkline building function"""

    def test_build_sparkline_with_values(self):
        """Test sparkline building with RTT values"""
        rtt_values = [0.01, 0.02, 0.03, 0.04, 0.05]
        status_symbols = [".", ".", ".", ".", "."]
        fail_symbol = "x"

        result = build_sparkline(rtt_values, status_symbols, fail_symbol)

        self.assertEqual(len(result), 5)
        # Should use sparkline characters
        self.assertTrue(all(c in "▁▂▃▄▅▆▇█" for c in result))

    def test_build_sparkline_with_failures(self):
        """Test sparkline with failed pings (None values)"""
        rtt_values = [0.01, None, 0.03, None, 0.05]
        status_symbols = [".", "x", ".", "x", "."]
        fail_symbol = "x"

        result = build_sparkline(rtt_values, status_symbols, fail_symbol)

        self.assertEqual(len(result), 5)

    def test_build_sparkline_all_same_value(self):
        """Test sparkline when all RTT values are the same"""
        rtt_values = [0.02, 0.02, 0.02, 0.02]
        status_symbols = [".", ".", ".", "."]
        fail_symbol = "x"

        result = build_sparkline(rtt_values, status_symbols, fail_symbol)

        self.assertEqual(len(result), 4)


class TestActivityIndicator(unittest.TestCase):
    """Test activity indicator behavior"""

    def test_activity_indicator_moves(self):
        """Indicator should move between ticks"""
        first = build_activity_indicator(datetime.fromtimestamp(0, tz=timezone.utc))
        second = build_activity_indicator(datetime.fromtimestamp(0.25, tz=timezone.utc))
        self.assertEqual(len(first), 10)
        self.assertEqual(len(second), 10)
        self.assertNotEqual(first, second)


class TestColorOutput(unittest.TestCase):
    """Test colored output helpers"""

    def test_build_colored_timeline_adds_color_codes(self):
        """Colored timeline should include ANSI color codes"""
        symbols = {"success": ".", "fail": "x", "slow": "!"}
        timeline = [".", "!", "x"]
        colored = build_colored_timeline(timeline, symbols, use_color=True)
        self.assertIn("\x1b[37m", colored)
        self.assertIn("\x1b[33m", colored)
        self.assertIn("\x1b[31m", colored)
        self.assertIn("\x1b[0m", colored)

    def test_build_colored_timeline_includes_pending(self):
        """Colored timeline should include pending status with dark gray color"""
        symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}
        timeline = ["-", ".", "-"]
        colored = build_colored_timeline(timeline, symbols, use_color=True)
        # Dark gray (bright black) color code
        self.assertIn("\x1b[90m", colored)
        # White for success
        self.assertIn("\x1b[37m", colored)
        # Reset code
        self.assertIn("\x1b[0m", colored)

    def test_build_colored_sparkline_respects_status_symbols(self):
        """Colored sparkline should map statuses to colors"""
        symbols = {"success": ".", "fail": "x", "slow": "!"}
        sparkline = "▁▂▃"
        status_symbols = [".", "!", "x"]
        colored = build_colored_sparkline(sparkline, status_symbols, symbols, use_color=True)
        self.assertIn("\x1b[37m", colored)
        self.assertIn("\x1b[33m", colored)
        self.assertIn("\x1b[31m", colored)


class TestStatusLine(unittest.TestCase):
    """Test status line building function"""

    def test_build_status_line_basic(self):
        """Test basic status line building"""
        result = build_status_line("failures", "all", "rates", False, None)
        self.assertIn("Failure Count", result)
        self.assertIn("All Items", result)
        self.assertNotIn("PAUSED", result)

    def test_build_status_line_paused(self):
        """Test status line when paused"""
        result = build_status_line("host", "all", "rates", True, None)
        self.assertIn("PAUSED", result)

    def test_build_status_line_with_message(self):
        """Test status line with custom message"""
        result = build_status_line("failures", "all", "rates", False, "Test message")
        self.assertIn("Test message", result)

    def test_build_status_line_different_modes(self):
        """Test status line with different sort and filter modes"""
        result = build_status_line("latency", "failures", "rates", False, None)
        self.assertIn("Latest Latency", result)
        self.assertIn("Failures Only", result)

    def test_build_status_line_all_summary(self):
        """Test status line when summary displays all fields"""
        result = build_status_line("latency", "failures", "rates", False, None, summary_all=True)
        self.assertIn("Summary: All", result)


class TestStatusMetrics(unittest.TestCase):
    """Test status metrics computation."""

    def test_build_status_metrics_counts(self):
        """Status metrics should include host, success, error, and rate values."""
        host_infos = [{"id": 1}, {"id": 2}]
        stats = {
            1: {"success": 2, "slow": 1, "fail": 0},
            2: {"success": 1, "slow": 0, "fail": 2},
        }
        with patch.dict(os.environ, {"PARAPING_PING_RATE": ""}, clear=False):
            result = build_status_metrics(host_infos, stats, interval_seconds=2.0)
        self.assertIn("Hosts: 2", result)
        self.assertIn("Success: 4", result)
        self.assertIn("Errors: 2", result)
        self.assertIn("Rate: 1.0/s", result)

    def test_build_status_metrics_rate_override(self):
        """Status metrics should honor the rate override env var."""
        host_infos = [{"id": 1}, {"id": 2}, {"id": 3}]
        stats = {1: {"success": 0, "slow": 0, "fail": 0}}
        with patch.dict(os.environ, {"PARAPING_PING_RATE": "12.5"}, clear=False):
            result = build_status_metrics(host_infos, stats, interval_seconds=1.0)
        self.assertIn("Rate: 12.5/s", result)


if __name__ == "__main__":
    unittest.main()
