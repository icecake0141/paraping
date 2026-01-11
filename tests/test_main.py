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
Unit tests for multiping functionality
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import argparse
import os
import queue
import sys
from collections import deque
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Add parent directory to path to import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import (
    handle_options,
    read_input_file,
    ping_host,
    main,
    render_help_view,
    compute_main_layout,
    compute_panel_sizes,
    build_display_names,
    format_display_name,
    compute_summary_data,
    format_timestamp,
    format_timezone_label,
    build_host_infos,
    build_sparkline,
    build_status_line,
    get_terminal_size,
    flash_screen,
    ring_bell,
    read_key,
    create_state_snapshot,
)  # noqa: E402


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


class TestReadInputFile(unittest.TestCase):
    """Test input file reading functionality"""

    def test_read_valid_file(self):
        """Test reading a valid input file"""
        file_content = "host1.com\nhost2.com\nhost3.com\n"
        with patch("builtins.open", mock_open(read_data=file_content)):
            hosts = read_input_file("test.txt")
            self.assertEqual(len(hosts), 3)
            self.assertEqual(hosts, ["host1.com", "host2.com", "host3.com"])

    def test_read_file_with_comments(self):
        """Test reading file with comments"""
        file_content = "host1.com\n# This is a comment\nhost2.com\n"
        with patch("builtins.open", mock_open(read_data=file_content)):
            hosts = read_input_file("test.txt")
            self.assertEqual(len(hosts), 2)
            self.assertEqual(hosts, ["host1.com", "host2.com"])

    def test_read_file_with_empty_lines(self):
        """Test reading file with empty lines"""
        file_content = "host1.com\n\nhost2.com\n\n"
        with patch("builtins.open", mock_open(read_data=file_content)):
            hosts = read_input_file("test.txt")
            self.assertEqual(len(hosts), 2)
            self.assertEqual(hosts, ["host1.com", "host2.com"])

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


class TestPingHost(unittest.TestCase):
    """Test ping host functionality"""

    @patch("main.ICMP")
    @patch("main.IP")
    @patch("main.sr")
    def test_ping_host_success(self, mock_sr, mock_ip, mock_icmp):
        """Test successful ping"""
        # Mock IP and ICMP packet creation
        mock_packet = MagicMock()
        mock_ip.return_value.__truediv__ = MagicMock(return_value=mock_packet)

        # Mock successful ping response - ans should be a truthy list
        mock_sent = MagicMock()
        mock_sent.time = 0.0
        mock_received = MagicMock()
        mock_received.time = 0.001
        mock_sr.return_value = ([[mock_sent, mock_received]], [])

        results = list(ping_host("example.com", 1, 4, 0.5, False))

        self.assertEqual(len(results), 4)
        for result in results:
            self.assertEqual(result["host"], "example.com")
            self.assertIn(result["status"], ["success", "slow"])

    @patch("main.ICMP")
    @patch("main.IP")
    @patch("main.sr")
    def test_ping_host_failure(self, mock_sr, mock_ip, mock_icmp):
        """Test failed ping"""
        # Mock IP and ICMP packet creation
        mock_packet = MagicMock()
        mock_ip.return_value.__truediv__ = MagicMock(return_value=mock_packet)

        # Mock failed ping response (no answers)
        mock_sr.return_value = ([], [MagicMock()])

        results = list(ping_host("example.com", 1, 4, 0.5, False))

        self.assertEqual(len(results), 4)
        for result in results:
            self.assertEqual(result["host"], "example.com")
            self.assertEqual(result["status"], "fail")

    @patch("main.ICMP")
    @patch("main.IP")
    @patch("main.sr")
    def test_ping_host_partial_success(self, mock_sr, mock_ip, mock_icmp):
        """Test partial ping success"""
        # Mock IP and ICMP packet creation
        mock_packet = MagicMock()
        mock_ip.return_value.__truediv__ = MagicMock(return_value=mock_packet)

        # Mock alternating success/failure
        mock_sent = MagicMock()
        mock_sent.time = 0.0
        mock_received = MagicMock()
        mock_received.time = 0.001
        mock_sr.side_effect = [
            ([[mock_sent, mock_received]], []),
            ([], [MagicMock()]),
            ([[mock_sent, mock_received]], []),
            ([], [MagicMock()]),
        ]

        results = list(ping_host("example.com", 1, 4, 0.5, False))

        self.assertEqual(len(results), 4)
        success_count = sum(1 for r in results if r["status"] in ["success", "slow"])
        fail_count = sum(1 for r in results if r["status"] == "fail")
        self.assertEqual(success_count, 2)
        self.assertEqual(fail_count, 2)

    @patch("main.ICMP")
    @patch("main.IP")
    @patch("main.sr")
    def test_ping_host_with_network_error(self, mock_sr, mock_ip, mock_icmp):
        """Test ping with network error"""
        # Mock IP and ICMP packet creation
        mock_packet = MagicMock()
        mock_ip.return_value.__truediv__ = MagicMock(return_value=mock_packet)

        mock_sr.side_effect = OSError("Network unreachable")

        results = list(ping_host("example.com", 1, 2, 0.5, False))

        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result["host"], "example.com")
            self.assertEqual(result["status"], "fail")


class TestMain(unittest.TestCase):
    """Test main function"""

    @patch("main.queue.Queue")
    @patch("main.sys.stdin")
    @patch("main.get_terminal_size")
    @patch("main.ThreadPoolExecutor")
    @patch("main.threading.Thread")
    def test_main_with_hosts(
        self, mock_thread, mock_executor, mock_term_size, mock_stdin, mock_queue
    ):
        """Test main function with hosts"""
        # Mock terminal properties
        mock_stdin.isatty.return_value = False
        mock_term_size.return_value = MagicMock(columns=80, lines=24)

        # Mock queue to simulate completion
        result_queue = MagicMock()
        # First return "done" for each host, then raise Empty
        result_queue.get_nowait.side_effect = [
            {"host_id": 0, "status": "done"},
            {"host_id": 1, "status": "done"},
            queue.Empty(),
        ]
        empty_queue = MagicMock()
        empty_queue.get_nowait.side_effect = queue.Empty()
        mock_queue.side_effect = [
            result_queue,
            MagicMock(),
            empty_queue,
            MagicMock(),
            empty_queue,
        ]

        args = argparse.Namespace(
            timeout=1,
            count=4,
            interval=1.0,
            slow_threshold=0.5,
            verbose=False,
            hosts=["host1.com", "host2.com"],
            input=None,
            panel_position="right",
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
        )

        # Mock executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_executor.return_value.__exit__.return_value = False

        # Mock futures
        mock_future = MagicMock()
        mock_future.done.return_value = True
        mock_future.result.return_value = None
        mock_executor_instance.submit.return_value = mock_future

        mock_thread.return_value = MagicMock()

        # Should not raise exception
        main(args)

    @patch("builtins.print")
    def test_main_with_invalid_count(self, mock_print):
        """Test main function with invalid count"""
        args = argparse.Namespace(
            timeout=1,
            count=-1,
            interval=1.0,
            verbose=False,
            hosts=["host1.com"],
            input=None,
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
        )

        main(args)
        mock_print.assert_called()

    @patch("builtins.print")
    def test_main_with_no_hosts(self, mock_print):
        """Test main function with no hosts"""
        args = argparse.Namespace(
            timeout=1,
            count=4,
            interval=1.0,
            verbose=False,
            hosts=[],
            input=None,
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
        )

        main(args)
        mock_print.assert_called()

    @patch("main.queue.Queue")
    @patch("main.sys.stdin")
    @patch("main.get_terminal_size")
    @patch("main.read_input_file")
    @patch("main.ThreadPoolExecutor")
    @patch("main.threading.Thread")
    def test_main_with_input_file(
        self,
        mock_thread,
        mock_executor,
        mock_read_file,
        mock_term_size,
        mock_stdin,
        mock_queue,
    ):
        """Test main function with input file"""
        # Mock terminal properties
        mock_stdin.isatty.return_value = False
        mock_term_size.return_value = MagicMock(columns=80, lines=24)

        mock_read_file.return_value = ["host1.com", "host2.com"]

        # Mock queue to simulate completion
        result_queue = MagicMock()
        # First return "done" for each host, then raise Empty
        result_queue.get_nowait.side_effect = [
            {"host_id": 0, "status": "done"},
            {"host_id": 1, "status": "done"},
            queue.Empty(),
        ]
        empty_queue = MagicMock()
        empty_queue.get_nowait.side_effect = queue.Empty()
        mock_queue.side_effect = [
            result_queue,
            MagicMock(),
            empty_queue,
            MagicMock(),
            empty_queue,
        ]

        args = argparse.Namespace(
            timeout=1,
            count=4,
            interval=1.0,
            slow_threshold=0.5,
            verbose=False,
            hosts=[],
            input="hosts.txt",
            panel_position="right",
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
        )

        # Mock executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_executor.return_value.__exit__.return_value = False

        # Mock futures
        mock_future = MagicMock()
        mock_future.done.return_value = True
        mock_future.result.return_value = None
        mock_executor_instance.submit.return_value = mock_future

        mock_thread.return_value = MagicMock()

        # Should not raise exception
        main(args)

        mock_read_file.assert_called_once_with("hosts.txt")

    @patch("builtins.print")
    def test_main_with_invalid_interval(self, mock_print):
        """Test main function with invalid interval"""
        args = argparse.Namespace(
            timeout=1,
            count=4,
            interval=100.0,  # Too large
            verbose=False,
            hosts=["host1.com"],
            input=None,
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
        )

        main(args)
        mock_print.assert_called()
        # Check that it printed the error message
        call_args = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("Interval" in str(call) for call in call_args))


class TestHelpView(unittest.TestCase):
    """Test help view rendering."""

    def test_help_view_contains_close_hint(self):
        """Help view should include close hint text."""
        lines = render_help_view(60, 20)
        combined = "\n".join(lines)
        self.assertIn("H : show help", combined)
        self.assertIn("Press any key to close", combined)


class TestLayoutComputation(unittest.TestCase):
    """Test layout computation functions"""

    def test_compute_main_layout_basic(self):
        """Test basic main layout computation"""
        host_labels = ["host1.com", "host2.com", "host3.com"]
        width, label_width, timeline_width, visible_hosts = compute_main_layout(
            host_labels, 80, 24, header_lines=2
        )
        self.assertEqual(width, 80)
        self.assertGreater(label_width, 0)
        self.assertGreater(timeline_width, 0)
        self.assertEqual(visible_hosts, 22)  # 24 - 2 header lines

    def test_compute_main_layout_with_long_hostnames(self):
        """Test layout with very long hostnames"""
        host_labels = ["very-long-hostname-that-exceeds-normal-length.example.com"]
        width, label_width, timeline_width, visible_hosts = compute_main_layout(
            host_labels, 80, 24
        )
        self.assertLessEqual(label_width, 80 // 3)  # Should be capped
        self.assertGreater(timeline_width, 0)

    def test_compute_panel_sizes_right(self):
        """Test panel size computation with right panel"""
        main_w, main_h, summ_w, summ_h, pos = compute_panel_sizes(
            80, 24, "right"
        )
        self.assertGreater(main_w, 0)
        self.assertGreater(summ_w, 0)
        self.assertEqual(main_h, 24)
        self.assertEqual(summ_h, 24)
        self.assertEqual(pos, "right")

    def test_compute_panel_sizes_none(self):
        """Test panel size computation with no panel"""
        main_w, main_h, summ_w, summ_h, pos = compute_panel_sizes(
            80, 24, "none"
        )
        self.assertEqual(main_w, 80)
        self.assertEqual(main_h, 24)
        self.assertEqual(summ_w, 0)
        self.assertEqual(summ_h, 0)
        self.assertEqual(pos, "none")

    def test_compute_panel_sizes_too_small(self):
        """Test panel computation falls back to none when terminal too small"""
        main_w, main_h, summ_w, summ_h, pos = compute_panel_sizes(
            10, 5, "right"
        )
        self.assertEqual(pos, "none")


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
            {"id": 0, "host": "h1.com", "alias": "h1", "ip": "1.1.1.1", "rdns": None, "asn": None},
            {"id": 1, "host": "h2.com", "alias": "h2", "ip": "2.2.2.2", "rdns": None, "asn": None},
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

    def test_compute_summary_data_all_success(self):
        """Test summary with all successful pings"""
        host_infos = [{"id": 0, "alias": "host1.com"}]
        display_names = {0: "host1.com"}
        buffers = {
            0: {
                "timeline": deque([".", ".", ".", "."]),
                "rtt_history": deque([0.01, 0.02, 0.015, 0.018]),
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
                "rtt_count": 4,
            }
        }
        symbols = {"success": ".", "fail": "x", "slow": "!"}

        summary = compute_summary_data(host_infos, display_names, buffers, stats, symbols)

        self.assertEqual(summary[0]["success_rate"], 100.0)
        self.assertEqual(summary[0]["loss_rate"], 0.0)
        self.assertEqual(summary[0]["streak_type"], "success")


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

    @patch("main.socket.gethostbyname")
    def test_build_host_infos_with_hostname(self, mock_gethostbyname):
        """Test building host infos with resolvable hostname"""
        mock_gethostbyname.return_value = "93.184.216.34"

        host_infos, host_map = build_host_infos(["example.com"])

        self.assertEqual(len(host_infos), 1)
        self.assertEqual(host_infos[0]["host"], "example.com")
        self.assertEqual(host_infos[0]["ip"], "93.184.216.34")
        self.assertEqual(host_infos[0]["alias"], "example.com")
        self.assertIn("example.com", host_map)

    @patch("main.socket.gethostbyname")
    def test_build_host_infos_with_ip(self, mock_gethostbyname):
        """Test building host infos with IP address"""
        mock_gethostbyname.side_effect = OSError()

        host_infos, host_map = build_host_infos(["192.168.1.1"])

        self.assertEqual(len(host_infos), 1)
        self.assertEqual(host_infos[0]["ip"], "192.168.1.1")

    @patch("main.socket.gethostbyname")
    def test_build_host_infos_multiple_hosts(self, mock_gethostbyname):
        """Test building host infos with multiple hosts"""
        mock_gethostbyname.side_effect = ["1.1.1.1", "2.2.2.2", "3.3.3.3"]

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


class TestStatusLine(unittest.TestCase):
    """Test status line building function"""

    def test_build_status_line_basic(self):
        """Test basic status line building"""
        result = build_status_line("failures", "all", False, None)
        self.assertIn("Failure Count", result)
        self.assertIn("All Items", result)
        self.assertNotIn("PAUSED", result)

    def test_build_status_line_paused(self):
        """Test status line when paused"""
        result = build_status_line("host", "all", True, None)
        self.assertIn("PAUSED", result)

    def test_build_status_line_with_message(self):
        """Test status line with custom message"""
        result = build_status_line("failures", "all", False, "Test message")
        self.assertIn("Test message", result)

    def test_build_status_line_different_modes(self):
        """Test status line with different sort and filter modes"""
        result = build_status_line("latency", "failures", False, None)
        self.assertIn("Latest Latency", result)
        self.assertIn("Failures Only", result)


class TestQuitHotkey(unittest.TestCase):
    """Test quit hotkey functionality"""

    @patch("main.queue.Queue")
    @patch("main.sys.stdin")
    @patch("main.get_terminal_size")
    @patch("main.ThreadPoolExecutor")
    @patch("main.threading.Thread")
    @patch("main.read_key")
    def test_quit_key_exits_immediately(
        self, mock_read_key, mock_thread, mock_executor, mock_term_size, mock_stdin, mock_queue
    ):
        """Test that pressing 'q' key exits the program immediately"""
        # Mock terminal properties
        mock_stdin.isatty.return_value = True
        mock_term_size.return_value = os.terminal_size((80, 24))

        # Mock stdin for terminal setup
        mock_stdin.fileno.return_value = 0

        # Mock queue to simulate completion
        result_queue = MagicMock()
        # Always raise Empty to simulate no results
        result_queue.get_nowait.side_effect = queue.Empty
        empty_queue = MagicMock()
        empty_queue.get_nowait.side_effect = queue.Empty
        # Queue instances: result_queue, rdns_request_queue, rdns_result_queue, asn_request_queue, asn_result_queue
        mock_queue.side_effect = [
            result_queue,  # result_queue
            MagicMock(),   # rdns_request_queue
            empty_queue,   # rdns_result_queue
            MagicMock(),   # asn_request_queue
            empty_queue,   # asn_result_queue
        ]

        # Mock read_key to return 'q' after a few iterations
        mock_read_key.side_effect = [None, None, "q"]

        args = argparse.Namespace(
            timeout=1,
            count=0,  # Infinite count to ensure it would run forever without 'q'
            interval=1.0,
            slow_threshold=0.5,
            verbose=False,
            hosts=["host1.com"],
            input=None,
            panel_position="right",
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
            flash_on_fail=False,
            bell_on_fail=False,
        )

        # Mock executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_executor.return_value.__exit__.return_value = False
        mock_executor_instance.submit.return_value = MagicMock()

        mock_thread.return_value = MagicMock()

        # Mock termios functions
        with patch("main.termios.tcgetattr", return_value=MagicMock()):
            with patch("main.termios.tcsetattr"):
                with patch("main.tty.setcbreak"):
                    # Should exit without raising exception when 'q' is pressed
                    main(args)

    @patch("main.queue.Queue")
    @patch("main.sys.stdin")
    @patch("main.get_terminal_size")
    @patch("main.ThreadPoolExecutor")
    @patch("main.threading.Thread")
    @patch("main.read_key")
    def test_quit_key_exits_from_help_screen(
        self, mock_read_key, mock_thread, mock_executor, mock_term_size, mock_stdin, mock_queue
    ):
        """Test that pressing 'q' key exits even when help screen is showing"""
        # Mock terminal properties
        mock_stdin.isatty.return_value = True
        mock_term_size.return_value = os.terminal_size((80, 24))

        # Mock stdin for terminal setup
        mock_stdin.fileno.return_value = 0

        # Mock queue to simulate completion
        result_queue = MagicMock()
        # Always raise Empty to simulate no results
        result_queue.get_nowait.side_effect = queue.Empty
        empty_queue = MagicMock()
        empty_queue.get_nowait.side_effect = queue.Empty
        # Queue instances: result_queue, rdns_request_queue, rdns_result_queue, asn_request_queue, asn_result_queue
        mock_queue.side_effect = [
            result_queue,  # result_queue
            MagicMock(),   # rdns_request_queue
            empty_queue,   # rdns_result_queue
            MagicMock(),   # asn_request_queue
            empty_queue,   # asn_result_queue
        ]

        # Mock read_key to open help screen with 'H', then press 'q' to quit
        mock_read_key.side_effect = [None, "H", "q"]

        args = argparse.Namespace(
            timeout=1,
            count=0,  # Infinite count
            interval=1.0,
            slow_threshold=0.5,
            verbose=False,
            hosts=["host1.com"],
            input=None,
            panel_position="right",
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
            flash_on_fail=False,
            bell_on_fail=False,
        )

        # Mock executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_executor.return_value.__exit__.return_value = False
        mock_executor_instance.submit.return_value = MagicMock()

        mock_thread.return_value = MagicMock()

        # Mock termios functions
        with patch("main.termios.tcgetattr", return_value=MagicMock()):
            with patch("main.termios.tcsetattr"):
                with patch("main.tty.setcbreak"):
                    # Should exit when 'q' is pressed, even with help screen open
                    main(args)


class TestTerminalSize(unittest.TestCase):
    """Test terminal size retrieval function"""

    @patch("main.os.get_terminal_size")
    @patch("main.sys.stdout")
    def test_get_terminal_size_from_stdout(
        self, mock_stdout, mock_os_get_size
    ):
        """Test getting terminal size from stdout"""
        mock_stdout.isatty.return_value = True
        mock_stdout.fileno.return_value = 1
        mock_os_get_size.return_value = MagicMock(columns=100, lines=50)

        result = get_terminal_size()

        self.assertEqual(result.columns, 100)
        self.assertEqual(result.lines, 50)
        mock_os_get_size.assert_called_once_with(1)

    @patch("main.os.get_terminal_size")
    @patch("main.sys.stdout")
    @patch("main.sys.stderr")
    def test_get_terminal_size_fallback_to_stderr(
        self, mock_stderr, mock_stdout, mock_os_get_size
    ):
        """Test fallback to stderr when stdout fails"""
        mock_stdout.isatty.return_value = False
        mock_stderr.isatty.return_value = True
        mock_stderr.fileno.return_value = 2
        mock_os_get_size.return_value = MagicMock(columns=120, lines=40)

        result = get_terminal_size()

        self.assertEqual(result.columns, 120)
        self.assertEqual(result.lines, 40)

    @patch("main.os.get_terminal_size")
    @patch("main.sys.stdout")
    @patch("main.sys.stderr")
    @patch("main.sys.stdin")
    def test_get_terminal_size_fallback_to_default(
        self, mock_stdin, mock_stderr, mock_stdout, mock_os_get_size
    ):
        """Test fallback to default size when no tty available"""
        mock_stdout.isatty.return_value = False
        mock_stderr.isatty.return_value = False
        mock_stdin.isatty.return_value = False

        result = get_terminal_size(fallback=(80, 24))

        self.assertEqual(result.columns, 80)
        self.assertEqual(result.lines, 24)

    @patch("main.os.get_terminal_size")
    @patch("main.sys.stdout")
    def test_get_terminal_size_handles_os_error(
        self, mock_stdout, mock_os_get_size
    ):
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


class TestFlashAndBell(unittest.TestCase):
    """Test flash and bell notification features"""

    def test_handle_options_flash_on_fail(self):
        """Test --flash-on-fail option parsing"""
        with patch("sys.argv", ["main.py", "--flash-on-fail", "example.com"]):
            args = handle_options()
            self.assertTrue(args.flash_on_fail)

    def test_handle_options_bell_on_fail(self):
        """Test --bell-on-fail option parsing"""
        with patch("sys.argv", ["main.py", "--bell-on-fail", "example.com"]):
            args = handle_options()
            self.assertTrue(args.bell_on_fail)

    def test_handle_options_both_flags(self):
        """Test both flash and bell options together"""
        with patch("sys.argv", ["main.py", "--flash-on-fail", "--bell-on-fail", "example.com"]):
            args = handle_options()
            self.assertTrue(args.flash_on_fail)
            self.assertTrue(args.bell_on_fail)

    def test_handle_options_default_false(self):
        """Test that flash and bell options default to False"""
        with patch("sys.argv", ["main.py", "example.com"]):
            args = handle_options()
            self.assertFalse(args.flash_on_fail)
            self.assertFalse(args.bell_on_fail)

    @patch("main.sys.stdout")
    @patch("main.time.sleep")
    def test_flash_screen(self, mock_sleep, mock_stdout):
        """Test flash_screen function"""
        flash_screen()
        # Should have called write to send escape sequences
        self.assertGreaterEqual(mock_stdout.write.call_count, 2)
        # Should have slept for ~0.1 seconds
        mock_sleep.assert_called_once_with(0.1)
        # Should have called flush
        self.assertGreaterEqual(mock_stdout.flush.call_count, 2)

    @patch("main.sys.stdout")
    def test_ring_bell(self, mock_stdout):
        """Test ring_bell function"""
        ring_bell()
        # Should write the bell character
        mock_stdout.write.assert_called_once_with("\a")
        # Should flush the output
        mock_stdout.flush.assert_called_once()


class TestArrowKeyNavigation(unittest.TestCase):
    """Test arrow key navigation for history viewing"""

    @patch("main.select.select")
    @patch("main.sys.stdin")
    def test_read_key_arrow_left(self, mock_stdin, mock_select):
        """Test reading left arrow key"""
        mock_stdin.isatty.return_value = True
        # First select returns ready, second for escape sequence
        mock_select.side_effect = [
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
        ]
        # Simulate ESC [ D sequence
        mock_stdin.read.side_effect = ['\x1b', '[D']

        result = read_key()
        self.assertEqual(result, 'arrow_left')

    @patch("main.select.select")
    @patch("main.sys.stdin")
    def test_read_key_arrow_right(self, mock_stdin, mock_select):
        """Test reading right arrow key"""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
        ]
        mock_stdin.read.side_effect = ['\x1b', '[C']

        result = read_key()
        self.assertEqual(result, 'arrow_right')

    @patch("main.select.select")
    @patch("main.sys.stdin")
    def test_read_key_arrow_up(self, mock_stdin, mock_select):
        """Test reading up arrow key"""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
        ]
        mock_stdin.read.side_effect = ['\x1b', '[A']

        result = read_key()
        self.assertEqual(result, 'arrow_up')

    @patch("main.select.select")
    @patch("main.sys.stdin")
    def test_read_key_arrow_down(self, mock_stdin, mock_select):
        """Test reading down arrow key"""
        mock_stdin.isatty.return_value = True
        mock_select.side_effect = [
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
        ]
        mock_stdin.read.side_effect = ['\x1b', '[B']

        result = read_key()
        self.assertEqual(result, 'arrow_down')

    @patch("main.select.select")
    @patch("main.sys.stdin")
    def test_read_key_normal_character(self, mock_stdin, mock_select):
        """Test reading a normal character (not arrow key)"""
        mock_stdin.isatty.return_value = True
        mock_select.return_value = ([mock_stdin], [], [])
        mock_stdin.read.return_value = 'q'

        result = read_key()
        self.assertEqual(result, 'q')

    def test_create_state_snapshot(self):
        """Test creating a state snapshot"""
        # Create test buffers
        buffers = {
            0: {
                "timeline": deque([".", ".", "x"], maxlen=10),
                "rtt_history": deque([0.01, 0.02, None], maxlen=10),
                "categories": {
                    "success": deque([1, 2], maxlen=10),
                    "slow": deque([], maxlen=10),
                    "fail": deque([3], maxlen=10),
                }
            }
        }

        # Create test stats
        stats = {
            0: {
                "success": 2,
                "slow": 0,
                "fail": 1,
                "total": 3,
                "rtt_sum": 0.03,
                "rtt_count": 2,
            }
        }

        timestamp = 12345.67

        # Create snapshot
        snapshot = create_state_snapshot(buffers, stats, timestamp)

        # Verify snapshot structure
        self.assertEqual(snapshot["timestamp"], timestamp)
        self.assertIn("buffers", snapshot)
        self.assertIn("stats", snapshot)

        # Verify buffers were deep copied
        self.assertEqual(list(snapshot["buffers"][0]["timeline"]), [".", ".", "x"])
        self.assertEqual(list(snapshot["buffers"][0]["rtt_history"]), [0.01, 0.02, None])

        # Verify stats were deep copied
        self.assertEqual(snapshot["stats"][0]["success"], 2)
        self.assertEqual(snapshot["stats"][0]["fail"], 1)

        # Verify it's a deep copy (modifying original doesn't affect snapshot)
        buffers[0]["timeline"].append("!")
        stats[0]["success"] = 100

        self.assertEqual(list(snapshot["buffers"][0]["timeline"]), [".", ".", "x"])
        self.assertEqual(snapshot["stats"][0]["success"], 2)

    def test_help_view_includes_arrow_keys(self):
        """Test that help view includes arrow key documentation"""
        lines = render_help_view(80, 24)
        combined = "\n".join(lines)
        self.assertIn("<- / ->", combined)
        self.assertIn("navigate", combined.lower())


if __name__ == "__main__":
    unittest.main()
