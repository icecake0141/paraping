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
# Review for correctness and security.

"""
Unit tests for paraping.pinger module.

This module tests ping functionality with mocked network operations.
"""

import os
import queue
import socket
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, call, patch

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.pinger import (
    ping_host,
    rdns_worker,
    resolve_rdns,
    worker_ping,
)


class TestPingHost(unittest.TestCase):
    """Test cases for ping_host function"""

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_success(self, mock_exists, mock_ping):
        """Test successful ping"""
        mock_exists.return_value = True
        mock_ping.return_value = (10.5, 64)  # RTT in ms, TTL

        results = list(ping_host("192.0.2.1", timeout=1, count=1, slow_threshold=0.5, verbose=False))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "success")
        self.assertAlmostEqual(results[0]["rtt"], 0.0105, places=4)
        self.assertEqual(results[0]["ttl"], 64)

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_slow(self, mock_exists, mock_ping):
        """Test slow ping (RTT above threshold)"""
        mock_exists.return_value = True
        mock_ping.return_value = (600.0, 64)  # 600ms = 0.6s > 0.5s threshold

        results = list(ping_host("192.0.2.1", timeout=1, count=1, slow_threshold=0.5, verbose=False))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "slow")
        self.assertAlmostEqual(results[0]["rtt"], 0.6, places=2)

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_failure(self, mock_exists, mock_ping):
        """Test ping failure (no response)"""
        mock_exists.return_value = True
        mock_ping.return_value = (None, None)

        results = list(ping_host("192.0.2.1", timeout=1, count=1, slow_threshold=0.5, verbose=False))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "fail")
        self.assertIsNone(results[0]["rtt"])
        self.assertIsNone(results[0]["ttl"])

    @patch("os.path.exists")
    def test_ping_host_helper_not_found(self, mock_exists):
        """Test when ping_helper binary is not found"""
        mock_exists.return_value = False

        results = list(ping_host("192.0.2.1", timeout=1, count=1, slow_threshold=0.5, verbose=False))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "fail")

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_multiple_pings(self, mock_exists, mock_ping):
        """Test multiple ping attempts"""
        mock_exists.return_value = True
        mock_ping.side_effect = [
            (10.0, 64),
            (15.0, 64),
            (20.0, 64),
        ]

        results = list(
            ping_host(
                "192.0.2.1", timeout=1, count=3, slow_threshold=0.5, verbose=False, interval=0.01  # Small interval for testing
            )
        )

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["sequence"], 1)
        self.assertEqual(results[1]["sequence"], 2)
        self.assertEqual(results[2]["sequence"], 3)

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_with_stop_event(self, mock_exists, mock_ping):
        """Test that stop_event terminates pinging"""
        mock_exists.return_value = True
        mock_ping.return_value = (10.0, 64)

        stop_event = threading.Event()

        def ping_generator():
            for result in ping_host(
                "192.0.2.1",
                timeout=1,
                count=0,  # Infinite
                slow_threshold=0.5,
                verbose=False,
                stop_event=stop_event,
                interval=0.01,
            ):
                yield result
                if result["sequence"] >= 2:
                    stop_event.set()

        results = list(ping_generator())

        # Should stop after 2 pings
        self.assertLessEqual(len(results), 2)

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_with_pause_event(self, mock_exists, mock_ping):
        """Test that pause_event pauses pinging"""
        mock_exists.return_value = True
        mock_ping.return_value = (10.0, 64)

        pause_event = threading.Event()
        stop_event = threading.Event()

        results = []

        def run_ping():
            for result in ping_host(
                "192.0.2.1",
                timeout=1,
                count=5,
                slow_threshold=0.5,
                verbose=False,
                pause_event=pause_event,
                stop_event=stop_event,
                interval=0.01,
            ):
                results.append(result)
                if len(results) == 2:
                    pause_event.set()
                    # Pause briefly then stop
                    threading.Timer(0.05, lambda: stop_event.set()).start()

        run_ping()

        # Should get some results before stop
        self.assertGreater(len(results), 0)

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_exception_handling(self, mock_exists, mock_ping):
        """Test handling of exceptions during ping"""
        mock_exists.return_value = True
        mock_ping.side_effect = Exception("Network error")

        results = list(ping_host("192.0.2.1", timeout=1, count=1, slow_threshold=0.5, verbose=False))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "fail")


class TestWorkerPing(unittest.TestCase):
    """Test cases for worker_ping function"""

    @patch("paraping.pinger.ping_host")
    def test_worker_ping_puts_results_in_queue(self, mock_ping_host):
        """Test that worker_ping puts results in queue"""
        mock_ping_host.return_value = [
            {"host": "192.0.2.1", "sequence": 1, "status": "success", "rtt": 0.01, "ttl": 64},
            {"host": "192.0.2.1", "sequence": 2, "status": "success", "rtt": 0.02, "ttl": 64},
        ]

        host_info = {"id": 0, "host": "192.0.2.1", "alias": "server1", "ip": "192.0.2.1"}
        result_queue = queue.Queue()

        worker_ping(
            host_info,
            timeout=1,
            count=2,
            slow_threshold=0.5,
            verbose=False,
            pause_event=None,
            stop_event=None,
            result_queue=result_queue,
            interval=1.0,
            helper_path="./ping_helper",
        )

        # Should have 2 results + 1 done message
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["host_id"], 0)
        self.assertEqual(results[1]["host_id"], 0)
        self.assertEqual(results[2]["status"], "done")

    @patch("paraping.pinger.ping_host")
    def test_worker_ping_adds_host_id(self, mock_ping_host):
        """Test that worker_ping adds host_id to results"""
        mock_ping_host.return_value = [
            {"host": "192.0.2.1", "sequence": 1, "status": "success", "rtt": 0.01, "ttl": 64},
        ]

        host_info = {"id": 42, "host": "192.0.2.1", "alias": "server1", "ip": "192.0.2.1"}
        result_queue = queue.Queue()

        worker_ping(
            host_info,
            timeout=1,
            count=1,
            slow_threshold=0.5,
            verbose=False,
            pause_event=None,
            stop_event=None,
            result_queue=result_queue,
            interval=1.0,
            helper_path="./ping_helper",
        )

        result = result_queue.get()
        self.assertEqual(result["host_id"], 42)


class TestResolveRDNS(unittest.TestCase):
    """Test cases for resolve_rdns function"""

    @patch("socket.gethostbyaddr")
    def test_resolve_rdns_success(self, mock_gethostbyaddr):
        """Test successful reverse DNS resolution"""
        mock_gethostbyaddr.return_value = ("example.com", [], ["192.0.2.1"])

        result = resolve_rdns("192.0.2.1")

        self.assertEqual(result, "example.com")
        mock_gethostbyaddr.assert_called_once_with("192.0.2.1")

    @patch("socket.gethostbyaddr")
    def test_resolve_rdns_herror(self, mock_gethostbyaddr):
        """Test handling of socket.herror"""
        mock_gethostbyaddr.side_effect = socket.herror("Host not found")

        result = resolve_rdns("192.0.2.1")

        self.assertIsNone(result)

    @patch("socket.gethostbyaddr")
    def test_resolve_rdns_gaierror(self, mock_gethostbyaddr):
        """Test handling of socket.gaierror"""
        mock_gethostbyaddr.side_effect = socket.gaierror("Address resolution failed")

        result = resolve_rdns("192.0.2.1")

        self.assertIsNone(result)

    @patch("socket.gethostbyaddr")
    def test_resolve_rdns_oserror(self, mock_gethostbyaddr):
        """Test handling of OSError"""
        mock_gethostbyaddr.side_effect = OSError("Network unreachable")

        result = resolve_rdns("192.0.2.1")

        self.assertIsNone(result)


class TestRDNSWorker(unittest.TestCase):
    """Test cases for rdns_worker function"""

    @patch("paraping.pinger.resolve_rdns")
    def test_rdns_worker_processes_requests(self, mock_resolve):
        """Test that rdns_worker processes requests from queue"""
        mock_resolve.return_value = "example.com"

        request_queue = queue.Queue()
        result_queue = queue.Queue()
        stop_event = threading.Event()

        # Add a request
        request_queue.put(("192.0.2.1", "192.0.2.1"))
        # Add termination signal
        request_queue.put(None)

        # Run worker
        rdns_worker(request_queue, result_queue, stop_event)

        # Check result
        self.assertFalse(result_queue.empty())
        host, rdns = result_queue.get()
        self.assertEqual(host, "192.0.2.1")
        self.assertEqual(rdns, "example.com")

    @patch("paraping.pinger.resolve_rdns")
    def test_rdns_worker_stops_on_none(self, mock_resolve):
        """Test that rdns_worker stops on None item"""
        mock_resolve.return_value = "example.com"

        request_queue = queue.Queue()
        result_queue = queue.Queue()
        stop_event = threading.Event()

        # Add requests
        request_queue.put(("192.0.2.1", "192.0.2.1"))
        request_queue.put(("192.0.2.2", "192.0.2.2"))
        request_queue.put(None)  # Termination signal

        rdns_worker(request_queue, result_queue, stop_event)

        # Should process 2 items
        self.assertEqual(result_queue.qsize(), 2)

    @patch("paraping.pinger.resolve_rdns")
    def test_rdns_worker_stops_on_event(self, mock_resolve):
        """Test that rdns_worker stops when stop_event is set"""
        mock_resolve.return_value = "example.com"

        request_queue = queue.Queue()
        result_queue = queue.Queue()
        stop_event = threading.Event()

        # Set stop event immediately
        stop_event.set()

        # Worker should exit quickly without processing
        start_time = time.time()
        rdns_worker(request_queue, result_queue, stop_event)
        elapsed = time.time() - start_time

        # Should exit within reasonable time
        self.assertLess(elapsed, 1.0)

    @patch("paraping.pinger.resolve_rdns")
    def test_rdns_worker_handles_empty_queue(self, mock_resolve):
        """Test that rdns_worker handles empty queue gracefully"""
        mock_resolve.return_value = "example.com"

        request_queue = queue.Queue()
        result_queue = queue.Queue()
        stop_event = threading.Event()

        # Run worker in thread and stop after short delay
        worker_thread = threading.Thread(target=rdns_worker, args=(request_queue, result_queue, stop_event), daemon=True)
        worker_thread.start()

        # Wait briefly then stop
        time.sleep(0.2)
        stop_event.set()
        worker_thread.join(timeout=1.0)

        # Worker should have stopped
        self.assertFalse(worker_thread.is_alive())


class TestPingHostIntegration(unittest.TestCase):
    """Integration tests for ping_host with various scenarios"""

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_mixed_results(self, mock_exists, mock_ping):
        """Test ping with mixed success/failure results"""
        mock_exists.return_value = True
        mock_ping.side_effect = [
            (10.0, 64),  # Success
            (None, None),  # Failure
            (600.0, 64),  # Slow
            (15.0, 64),  # Success
        ]

        results = list(ping_host("192.0.2.1", timeout=1, count=4, slow_threshold=0.5, verbose=False, interval=0.01))

        self.assertEqual(len(results), 4)
        self.assertEqual(results[0]["status"], "success")
        self.assertEqual(results[1]["status"], "fail")
        self.assertEqual(results[2]["status"], "slow")
        self.assertEqual(results[3]["status"], "success")

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_infinite_with_early_stop(self, mock_exists, mock_ping):
        """Test infinite ping with early termination"""
        mock_exists.return_value = True
        mock_ping.return_value = (10.0, 64)

        stop_event = threading.Event()
        results = []

        for i, result in enumerate(
            ping_host(
                "192.0.2.1",
                timeout=1,
                count=0,  # Infinite
                slow_threshold=0.5,
                verbose=False,
                stop_event=stop_event,
                interval=0.01,
            )
        ):
            results.append(result)
            if i >= 4:  # Stop after 5 results
                stop_event.set()
                break

        self.assertEqual(len(results), 5)


if __name__ == "__main__":
    unittest.main()
