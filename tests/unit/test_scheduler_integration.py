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
Integration tests for scheduler-driven ping functionality.

This module tests the integration of the Scheduler with the ping loop,
verifying real-time timing, staggering, and event handling.
"""

import os
import queue
import sys
import threading
import time
import unittest
from typing import Any, TypedDict
from unittest.mock import MagicMock, patch

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.pinger import scheduler_driven_worker_ping  # noqa: E402
from paraping.scheduler import Scheduler  # noqa: E402


class HostInfo(TypedDict):
    """Typed host metadata for scheduler-driven tests."""

    host: str
    id: int


def _clear_queue(result_queue: "queue.Queue[dict[str, Any]]") -> None:
    while not result_queue.empty():
        result_queue.get_nowait()


def _collect_sent_hosts(
    result_queue: "queue.Queue[dict[str, Any]]",
    host_count: int,
    deadline: float,
) -> set[int]:
    sent_hosts: set[int] = set()
    while len(sent_hosts) < host_count and time.time() < deadline:
        try:
            result = result_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        if result.get("status") == "sent":
            sent_hosts.add(int(result["host_id"]))
    return sent_hosts


def _collect_sent_times_after(
    result_queue: "queue.Queue[dict[str, Any]]",
    host_count: int,
    resume_time: float,
    deadline: float,
) -> dict[int, float]:
    sent_after: dict[int, float] = {}
    while len(sent_after) < host_count and time.time() < deadline:
        try:
            result = result_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        if result.get("status") == "sent":
            sent_time = float(result.get("sent_time", time.time()))
            host_id = int(result["host_id"])
            if sent_time >= resume_time and host_id not in sent_after:
                sent_after[host_id] = sent_time
    return sent_after


class TestSchedulerIntegration(unittest.TestCase):
    """Integration tests for scheduler-driven ping timing"""

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_scheduler_driven_staggering(self, mock_exists: MagicMock, mock_ping: MagicMock) -> None:
        """Test that pings are staggered correctly across multiple hosts"""
        mock_exists.return_value = True
        mock_ping.return_value = (50.0, 64)  # 50ms RTT, TTL 64

        # Setup
        interval = 1.0
        hosts: list[HostInfo] = [
            {"host": "192.0.2.1", "id": 0},
            {"host": "192.0.2.2", "id": 1},
            {"host": "192.0.2.3", "id": 2},
        ]
        num_hosts = len(hosts)
        stagger = interval / num_hosts

        scheduler = Scheduler(interval=interval, stagger=stagger)
        ping_lock = threading.Lock()

        for host_info in hosts:
            scheduler.add_host(host_info["host"], host_id=host_info["id"])

        result_queue: "queue.Queue[dict[str, Any]]" = queue.Queue()
        stop_event = threading.Event()

        # Start ping workers
        threads: list[threading.Thread] = []
        for host_info in hosts:
            thread = threading.Thread(
                target=scheduler_driven_worker_ping,
                args=(
                    host_info,
                    scheduler,
                    1.0,  # timeout
                    1,  # count (just one ping)
                    0.5,  # slow_threshold
                    None,  # pause_event
                    stop_event,
                    result_queue,
                    "./ping_helper",
                    ping_lock,
                ),
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        # Collect sent events with timestamps
        sent_events: list[dict[str, Any]] = []
        base_time = None
        collection_deadline = time.time() + 5.0  # 5 second deadline

        while len(sent_events) < num_hosts and time.time() < collection_deadline:
            try:
                result = result_queue.get(timeout=0.5)
                if result.get("status") == "sent":
                    sent_time = result.get("sent_time", time.time())
                    if base_time is None:
                        base_time = sent_time
                    offset = sent_time - base_time
                    sent_events.append(
                        {
                            "host_id": result["host_id"],
                            "offset": offset,
                            "sent_time": sent_time,
                        }
                    )
            except queue.Empty:
                continue

        # Wait for threads to complete
        for thread in threads:
            thread.join(timeout=2.0)

        stop_event.set()

        # Verify we got all sent events
        self.assertEqual(len(sent_events), num_hosts, "Should receive sent event from all hosts")

        # Sort by host_id to verify staggering
        sent_events.sort(key=lambda x: x["host_id"])

        # Verify staggering with tolerance of ~0.1s
        tolerance = 0.15  # Allow 150ms tolerance for system scheduling
        for i, event in enumerate(sent_events):
            expected_offset = i * stagger
            actual_offset = event["offset"]
            self.assertAlmostEqual(
                actual_offset,
                expected_offset,
                delta=tolerance,
                msg=f"Host {i} offset {actual_offset:.3f}s should be near {expected_offset:.3f}s (stagger={stagger:.3f}s)",
            )

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_scheduler_driven_pause_and_stop(self, mock_exists: MagicMock, mock_ping: MagicMock) -> None:
        """Test that pause_event and stop_event work correctly"""
        mock_exists.return_value = True
        mock_ping.return_value = (50.0, 64)

        host_info: HostInfo = {"host": "192.0.2.1", "id": 0}
        scheduler = Scheduler(interval=0.2, stagger=0.0)
        scheduler.add_host(host_info["host"], host_id=host_info["id"])

        result_queue: "queue.Queue[dict[str, Any]]" = queue.Queue()
        pause_event = threading.Event()
        stop_event = threading.Event()
        ping_lock = threading.Lock()

        # Start worker
        thread = threading.Thread(
            target=scheduler_driven_worker_ping,
            args=(
                host_info,
                scheduler,
                1.0,
                0,  # infinite count
                0.5,
                pause_event,
                stop_event,
                result_queue,
                "./ping_helper",
                ping_lock,
            ),
            daemon=True,
        )
        thread.start()

        # Wait for first ping
        time.sleep(0.3)

        # Pause
        pause_event.set()
        time.sleep(0.1)

        # Count events before unpause
        events_before_unpause = 0
        while not result_queue.empty():
            result_queue.get_nowait()
            events_before_unpause += 1

        # Wait while paused - should not get new events
        time.sleep(0.3)
        new_events_while_paused = 0
        while not result_queue.empty():
            result_queue.get_nowait()
            new_events_while_paused += 1

        # Verify no new events during pause (or very few due to timing)
        self.assertLessEqual(new_events_while_paused, 1, "Should not generate many events while paused")

        # Unpause and verify pinging resumes
        pause_event.clear()
        time.sleep(0.3)

        events_after_unpause = 0
        while not result_queue.empty():
            result_queue.get_nowait()
            events_after_unpause += 1

        # Should have events after unpause
        self.assertGreater(events_after_unpause, 0, "Should resume pinging after unpause")

        # Test stop
        stop_event.set()
        thread.join(timeout=1.0)
        self.assertFalse(thread.is_alive(), "Thread should stop when stop_event is set")

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_scheduler_driven_resume_preserves_stagger(self, mock_exists: MagicMock, mock_ping: MagicMock) -> None:
        """Resume from pause should preserve stagger spacing between hosts."""
        mock_exists.return_value = True
        mock_ping.return_value = (50.0, 64)

        interval = 0.4
        hosts: list[HostInfo] = [
            {"host": "192.0.2.1", "id": 0},
            {"host": "192.0.2.2", "id": 1},
        ]
        stagger = interval / len(hosts)

        scheduler = Scheduler(interval=interval, stagger=stagger)
        ping_lock = threading.Lock()
        result_queue: "queue.Queue[dict[str, Any]]" = queue.Queue()
        pause_event = threading.Event()
        stop_event = threading.Event()

        for host_info in hosts:
            scheduler.add_host(host_info["host"], host_id=host_info["id"])

        threads: list[threading.Thread] = []
        for host_info in hosts:
            thread = threading.Thread(
                target=scheduler_driven_worker_ping,
                args=(
                    host_info,
                    scheduler,
                    1.0,
                    0,  # infinite count
                    0.5,
                    pause_event,
                    stop_event,
                    result_queue,
                    "./ping_helper",
                    ping_lock,
                ),
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        initial_sent = _collect_sent_hosts(result_queue, len(hosts), time.time() + 5.0)
        self.assertEqual(len(initial_sent), len(hosts), "Should receive initial sent events before pause")

        pause_event.set()
        pause_interval_multiplier = 2
        pause_duration = interval * pause_interval_multiplier  # ensure scheduled ping times expire while paused
        time.sleep(pause_duration)
        _clear_queue(result_queue)

        resume_time = time.time()
        pause_event.clear()

        sent_after = _collect_sent_times_after(result_queue, len(hosts), resume_time, time.time() + 5.0)

        stop_event.set()
        for thread in threads:
            thread.join(timeout=2.0)

        self.assertEqual(len(sent_after), len(hosts), "Should receive sent events after resume")

        sent_times = sorted(sent_after.values())
        stagger_gap = sent_times[1] - sent_times[0]
        min_acceptable_stagger_ratio = 0.5
        self.assertGreaterEqual(
            stagger_gap,
            stagger * min_acceptable_stagger_ratio,
            f"Stagger gap {stagger_gap:.3f}s should remain near {stagger:.3f}s after resume",
        )

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_scheduler_driven_monotonic_timing(self, mock_exists: MagicMock, mock_ping: MagicMock) -> None:
        """Test that timing uses monotonic clock for accuracy"""
        mock_exists.return_value = True
        mock_ping.return_value = (50.0, 64)

        host_info: HostInfo = {"host": "192.0.2.1", "id": 0}
        interval = 0.3
        scheduler = Scheduler(interval=interval, stagger=0.0)
        scheduler.add_host(host_info["host"], host_id=host_info["id"])

        result_queue: "queue.Queue[dict[str, Any]]" = queue.Queue()
        stop_event = threading.Event()
        ping_lock = threading.Lock()

        # Start worker
        thread = threading.Thread(
            target=scheduler_driven_worker_ping,
            args=(
                host_info,
                scheduler,
                1.0,
                3,  # 3 pings
                0.5,
                None,
                stop_event,
                result_queue,
                "./ping_helper",
                ping_lock,
            ),
            daemon=True,
        )

        thread.start()

        # Collect sent events
        sent_times_monotonic = []
        collection_deadline = time.time() + 5.0

        sent_count = 0
        while sent_count < 3 and time.time() < collection_deadline:
            try:
                result = result_queue.get(timeout=1.0)
                if result.get("status") == "sent":
                    sent_times_monotonic.append(time.monotonic())
                    sent_count += 1
            except queue.Empty:
                continue

        thread.join(timeout=2.0)
        stop_event.set()

        # Verify we got 3 pings
        self.assertEqual(len(sent_times_monotonic), 3, "Should have 3 sent events")

        # Verify intervals are approximately correct (using monotonic time)
        tolerance = 0.15
        for i in range(1, len(sent_times_monotonic)):
            actual_interval = sent_times_monotonic[i] - sent_times_monotonic[i - 1]
            self.assertAlmostEqual(
                actual_interval,
                interval,
                delta=tolerance,
                msg=f"Interval {i} should be approximately {interval}s (got {actual_interval:.3f}s)",
            )


if __name__ == "__main__":
    unittest.main()
