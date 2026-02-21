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
from unittest.mock import patch

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.pinger import (  # noqa: E402  # pylint: disable=wrong-import-position
    ping_host,
    rdns_worker,
    resolve_rdns,
    scheduler_driven_ping_host,
    worker_ping,
)
from paraping.scheduler import Scheduler  # noqa: E402  # pylint: disable=wrong-import-position


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
        mock_ping.side_effect = OSError("Network error")

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

    @patch("paraping.pinger.resolve_rdns")
    def test_rdns_worker_handles_unexpected_exception(self, mock_resolve):
        """Test that rdns_worker returns None and continues on unexpected exception"""
        mock_resolve.side_effect = [OSError("unexpected"), "example.com"]

        request_queue = queue.Queue()
        result_queue = queue.Queue()
        stop_event = threading.Event()

        request_queue.put(("192.0.2.1", "192.0.2.1"))
        request_queue.put(("192.0.2.2", "192.0.2.2"))
        request_queue.put(None)

        # Should not raise
        rdns_worker(request_queue, result_queue, stop_event)

        results = []
        while not result_queue.empty():
            results.append(result_queue.get_nowait())

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], ("192.0.2.1", None))
        self.assertEqual(results[1], ("192.0.2.2", "example.com"))


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


class TestEmitPendingMarker(unittest.TestCase):
    """Test cases for emit_pending marker functionality"""

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_emit_pending_single_ping(self, mock_exists, mock_ping):
        """Test that emit_pending yields a 'sent' event before ping"""
        mock_exists.return_value = True
        mock_ping.return_value = (10.0, 64)  # RTT in ms, TTL

        results = list(
            ping_host(
                "192.0.2.1",
                timeout=1,
                count=1,
                slow_threshold=0.5,
                verbose=False,
                emit_pending=True,
            )
        )

        # Should have 2 results: 'sent' event and actual ping result
        self.assertEqual(len(results), 2)

        # First result should be the 'sent' event
        sent_event = results[0]
        self.assertEqual(sent_event["status"], "sent")
        self.assertEqual(sent_event["host"], "192.0.2.1")
        self.assertEqual(sent_event["sequence"], 1)
        self.assertIsNone(sent_event["rtt"])
        self.assertIsNone(sent_event["ttl"])
        self.assertIn("sent_time", sent_event)
        self.assertIsInstance(sent_event["sent_time"], float)

        # Second result should be the actual ping result
        ping_result = results[1]
        self.assertEqual(ping_result["status"], "success")
        self.assertAlmostEqual(ping_result["rtt"], 0.01, places=2)

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_emit_pending_multiple_pings(self, mock_exists, mock_ping):
        """Test that emit_pending yields 'sent' events for multiple pings"""
        mock_exists.return_value = True
        mock_ping.side_effect = [
            (10.0, 64),
            (15.0, 64),
            (20.0, 64),
        ]

        results = list(
            ping_host(
                "192.0.2.1",
                timeout=1,
                count=3,
                slow_threshold=0.5,
                verbose=False,
                emit_pending=True,
                interval=0.01,  # Small interval for testing
            )
        )

        # Should have 6 results: 3 'sent' events and 3 ping results
        self.assertEqual(len(results), 6)

        # Check that results alternate: sent, success, sent, success, sent, success
        for i in range(3):
            sent_event = results[i * 2]
            ping_result = results[i * 2 + 1]

            # Verify sent event
            self.assertEqual(sent_event["status"], "sent")
            self.assertEqual(sent_event["sequence"], i + 1)
            self.assertIn("sent_time", sent_event)

            # Verify ping result
            self.assertEqual(ping_result["status"], "success")
            self.assertEqual(ping_result["sequence"], i + 1)

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_emit_pending_with_failure(self, mock_exists, mock_ping):
        """Test that emit_pending yields 'sent' event even when ping fails"""
        mock_exists.return_value = True
        mock_ping.return_value = (None, None)  # Ping failure

        results = list(
            ping_host(
                "192.0.2.1",
                timeout=1,
                count=1,
                slow_threshold=0.5,
                verbose=False,
                emit_pending=True,
            )
        )

        # Should have 2 results: 'sent' event and failed ping result
        self.assertEqual(len(results), 2)

        # First result should be the 'sent' event
        sent_event = results[0]
        self.assertEqual(sent_event["status"], "sent")

        # Second result should be the failed ping
        ping_result = results[1]
        self.assertEqual(ping_result["status"], "fail")

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_ping_host_without_emit_pending(self, mock_exists, mock_ping):
        """Test that without emit_pending, no 'sent' event is yielded"""
        mock_exists.return_value = True
        mock_ping.return_value = (10.0, 64)

        results = list(
            ping_host(
                "192.0.2.1",
                timeout=1,
                count=1,
                slow_threshold=0.5,
                verbose=False,
                emit_pending=False,  # Explicitly disable
            )
        )

        # Should have only 1 result: the ping result
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "success")


class TestSchedulerDrivenPendingEvents(unittest.TestCase):
    """Test cases for scheduler-driven ping pending events"""

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_scheduler_driven_ping_emits_sent_event(self, mock_exists, mock_ping):
        """Test that scheduler_driven_ping_host emits 'sent' event at send time"""
        mock_exists.return_value = True
        # Simulate a slow ping response to verify 'sent' event is emitted first
        mock_ping.return_value = (10.0, 64)

        scheduler = Scheduler(interval=1.0, stagger=0.0)
        host_info = {"id": 0, "host": "192.0.2.1"}
        scheduler.add_host("192.0.2.1")

        result_queue = queue.Queue()
        stop_event = threading.Event()
        pause_event = threading.Event()
        ping_lock = threading.Lock()

        # Run scheduler_driven_ping_host in a thread
        ping_thread = threading.Thread(
            target=scheduler_driven_ping_host,
            args=(
                host_info,
                scheduler,
                1,  # timeout
                1,  # count - only one ping
                0.5,  # slow_threshold
                pause_event,
                stop_event,
                result_queue,
                "./ping_helper",
                ping_lock,
            ),
            daemon=True,
        )
        ping_thread.start()

        # Wait for events to be queued
        time.sleep(0.2)
        stop_event.set()
        ping_thread.join(timeout=2.0)

        # Collect all results from queue
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # Should have at least 2 events: 'sent' and either 'success' or 'done'
        self.assertGreaterEqual(len(results), 2)

        # First result should be the 'sent' event
        sent_event = results[0]
        self.assertEqual(sent_event["status"], "sent")
        self.assertEqual(sent_event["host"], "192.0.2.1")
        self.assertEqual(sent_event["host_id"], 0)
        self.assertEqual(sent_event["sequence"], 0)  # ICMP seq starts at 0
        self.assertIsNone(sent_event["rtt"])
        self.assertIsNone(sent_event["ttl"])
        self.assertIn("sent_time", sent_event)
        self.assertIsInstance(sent_event["sent_time"], float)

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_scheduler_driven_ping_sent_before_result(self, mock_exists, mock_ping):
        """Test that 'sent' event is emitted before ping result"""
        mock_exists.return_value = True

        # Use a longer mock delay to ensure timing
        def delayed_ping(*args, **kwargs):
            time.sleep(0.05)  # Small delay to simulate network latency
            return (10.0, 64)

        mock_ping.side_effect = delayed_ping

        scheduler = Scheduler(interval=1.0, stagger=0.0)
        host_info = {"id": 0, "host": "192.0.2.1"}
        scheduler.add_host("192.0.2.1")

        result_queue = queue.Queue()
        stop_event = threading.Event()
        pause_event = threading.Event()
        ping_lock = threading.Lock()

        # Track the order of events
        event_order = []

        def track_events():
            start_time = time.time()
            while time.time() - start_time < 1.0 and not stop_event.is_set():
                try:
                    result = result_queue.get(timeout=0.1)
                    event_order.append((time.time(), result["status"]))
                except queue.Empty:
                    continue

        tracker_thread = threading.Thread(target=track_events, daemon=True)
        tracker_thread.start()

        # Run scheduler_driven_ping_host
        ping_thread = threading.Thread(
            target=scheduler_driven_ping_host,
            args=(
                host_info,
                scheduler,
                1,  # timeout
                1,  # count
                0.5,  # slow_threshold
                pause_event,
                stop_event,
                result_queue,
                "./ping_helper",
                ping_lock,
            ),
            daemon=True,
        )
        ping_thread.start()

        # Wait for completion
        time.sleep(0.3)
        stop_event.set()
        ping_thread.join(timeout=2.0)
        tracker_thread.join(timeout=1.0)

        # Verify that 'sent' event came before the ping result
        self.assertGreaterEqual(len(event_order), 2)
        statuses = [status for _, status in event_order]

        # Find the index of 'sent' and 'success'/'fail'
        sent_idx = None
        result_idx = None
        for i, status in enumerate(statuses):
            if status == "sent" and sent_idx is None:
                sent_idx = i
            if status in ["success", "slow", "fail"] and result_idx is None:
                result_idx = i

        # 'sent' should come before the result
        if sent_idx is not None and result_idx is not None:
            self.assertLess(sent_idx, result_idx)


if __name__ == "__main__":
    unittest.main()
