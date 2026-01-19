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
Unit tests for ping host functionality and main function
"""

import argparse
import os
import queue
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path to import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import (  # noqa: E402
    MAX_HOST_THREADS,
    main,
    ping_host,
)


class TestPingHost(unittest.TestCase):
    """Test ping host functionality"""

    @patch("paraping.pinger.os.path.exists", return_value=True)
    @patch("paraping.pinger.ping_with_helper")
    def test_ping_host_success(self, mock_ping_with_helper, mock_path_exists):
        """Test successful ping"""
        mock_ping_with_helper.return_value = (25.0, 64)

        results = list(ping_host("example.com", 1, 4, 0.5, False))

        self.assertEqual(len(results), 4)
        for result in results:
            self.assertEqual(result["host"], "example.com")
            self.assertIn(result["status"], ["success", "slow"])
            self.assertEqual(result["ttl"], 64)

    @patch("paraping.pinger.os.path.exists", return_value=True)
    @patch("paraping.pinger.ping_with_helper")
    def test_ping_host_failure(self, mock_ping_with_helper, mock_path_exists):
        """Test failed ping"""
        mock_ping_with_helper.return_value = (None, None)

        results = list(ping_host("example.com", 1, 4, 0.5, False))

        self.assertEqual(len(results), 4)
        for result in results:
            self.assertEqual(result["host"], "example.com")
            self.assertEqual(result["status"], "fail")
            self.assertIsNone(result["ttl"])

    @patch("paraping.pinger.os.path.exists", return_value=True)
    @patch("paraping.pinger.ping_with_helper")
    def test_ping_host_partial_success(self, mock_ping_with_helper, mock_path_exists):
        """Test partial ping success"""
        # Mock alternating success/failure
        mock_ping_with_helper.side_effect = [
            (25.0, 64),
            (None, None),
            (25.0, 64),
            (None, None),
        ]

        results = list(ping_host("example.com", 1, 4, 0.5, False))

        self.assertEqual(len(results), 4)
        success_count = sum(1 for r in results if r["status"] in ["success", "slow"])
        fail_count = sum(1 for r in results if r["status"] == "fail")
        self.assertEqual(success_count, 2)
        self.assertEqual(fail_count, 2)
        # Check TTL is present in successful pings
        for r in results:
            if r["status"] in ["success", "slow"]:
                self.assertEqual(r["ttl"], 64)
            else:
                self.assertIsNone(r["ttl"])

    @patch("paraping.pinger.os.path.exists", return_value=True)
    @patch("paraping.pinger.ping_with_helper")
    def test_ping_host_with_network_error(self, mock_ping_with_helper, mock_path_exists):
        """Test ping with network error"""
        mock_ping_with_helper.side_effect = OSError("Network unreachable")

        results = list(ping_host("example.com", 1, 2, 0.5, False))

        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result["host"], "example.com")
            self.assertEqual(result["status"], "fail")
            self.assertIsNone(result["ttl"])


class TestMain(unittest.TestCase):
    """Test main function"""

    @patch("paraping.cli.queue.Queue")
    @patch("paraping.cli.sys.stdin")
    @patch("paraping.ui_render.get_terminal_size")
    @patch("paraping.cli.ThreadPoolExecutor")
    @patch("paraping.cli.threading.Thread")
    def test_main_with_hosts(self, mock_thread, mock_executor, mock_term_size, mock_stdin, mock_queue):
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
            color=False,
            hosts=["host1.com", "host2.com"],
            input=None,
            panel_position="right",
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
            ping_helper="./ping_helper",
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
            color=False,
            hosts=["host1.com"],
            input=None,
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
            ping_helper="./ping_helper",
        )

        main(args)
        mock_print.assert_called()

    @patch("builtins.print")
    def test_main_with_invalid_timeout(self, mock_print):
        """Test main function with invalid timeout"""
        args = argparse.Namespace(
            timeout=0,
            count=4,
            interval=1.0,
            verbose=False,
            color=False,
            hosts=["host1.com"],
            input=None,
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
            ping_helper="./ping_helper",
        )

        main(args)
        mock_print.assert_called()
        call_args = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("Timeout" in str(call) for call in call_args))

    @patch("builtins.print")
    def test_main_with_no_hosts(self, mock_print):
        """Test main function with no hosts"""
        args = argparse.Namespace(
            timeout=1,
            count=4,
            interval=1.0,
            verbose=False,
            color=False,
            hosts=[],
            input=None,
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
            ping_helper="./ping_helper",
        )

        main(args)
        mock_print.assert_called()

    @patch("builtins.print")
    def test_main_with_too_many_hosts(self, mock_print):
        """Test main function with too many hosts"""
        hosts = [f"host{idx}.com" for idx in range(MAX_HOST_THREADS + 1)]
        args = argparse.Namespace(
            timeout=1,
            count=4,
            interval=1.0,
            slow_threshold=0.5,
            verbose=False,
            color=False,
            hosts=hosts,
            input=None,
            panel_position="right",
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
            ping_helper="./ping_helper",
        )

        main(args)
        call_args = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("exceeds maximum supported threads" in call for call in call_args))

    @patch("paraping.cli.queue.Queue")
    @patch("paraping.cli.sys.stdin")
    @patch("paraping.ui_render.get_terminal_size")
    @patch("paraping.cli.read_input_file")
    @patch("paraping.cli.ThreadPoolExecutor")
    @patch("paraping.cli.threading.Thread")
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
            color=False,
            hosts=[],
            input="hosts.txt",
            panel_position="right",
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
            ping_helper="./ping_helper",
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
            color=False,
            hosts=["host1.com"],
            input=None,
            pause_mode="display",
            timezone=None,
            snapshot_timezone="utc",
            ping_helper="./ping_helper",
        )

        main(args)
        mock_print.assert_called()
        # Check that it printed the error message
        call_args = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("Interval" in str(call) for call in call_args))


if __name__ == "__main__":
    unittest.main()
