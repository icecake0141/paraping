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
Integration tests for per-host sequence tracking and outstanding ping limits.

This module tests that the pinger module correctly uses SequenceTracker to:
- Assign unique ICMP sequence numbers per host
- Enforce maximum 3 outstanding pings per host
- Handle sequence wraparound at uint16 boundary
"""

import os
import queue
import sys
import threading
import time
import unittest
from unittest.mock import patch

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.pinger import scheduler_driven_ping_host  # noqa: E402  # pylint: disable=wrong-import-position
from paraping.scheduler import Scheduler  # noqa: E402  # pylint: disable=wrong-import-position
from paraping.sequence_tracker import SequenceTracker  # noqa: E402  # pylint: disable=wrong-import-position


class TestSequenceTrackingIntegration(unittest.TestCase):
    """Integration tests for sequence tracking in pinger module"""

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_sequences_start_at_zero(self, mock_exists, mock_ping):
        """Test that ICMP sequences start at 0 for each host"""
        mock_exists.return_value = True
        mock_ping.return_value = (10.0, 64)

        scheduler = Scheduler(interval=1.0, stagger=0.0)
        sequence_tracker = SequenceTracker(max_outstanding=3)
        host_info = {"id": 0, "host": "192.0.2.1"}
        scheduler.add_host("192.0.2.1")

        result_queue = queue.Queue()
        stop_event = threading.Event()
        pause_event = threading.Event()
        ping_lock = threading.Lock()

        # Run for 3 pings
        ping_thread = threading.Thread(
            target=scheduler_driven_ping_host,
            args=(
                host_info,
                scheduler,
                1,  # timeout
                3,  # count
                0.5,  # slow_threshold
                pause_event,
                stop_event,
                result_queue,
                "./ping_helper",
                ping_lock,
                sequence_tracker,
            ),
            daemon=True,
        )
        ping_thread.start()
        ping_thread.join(timeout=5.0)

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        # Filter for sent events
        sent_events = [r for r in results if r.get("status") == "sent"]

        # Should have 3 sent events with sequences 0, 1, 2
        self.assertEqual(len(sent_events), 3)
        sequences = [e["sequence"] for e in sent_events]
        self.assertEqual(sequences, [0, 1, 2])

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_max_three_outstanding_enforced(self, mock_exists, mock_ping):
        """Test that max 3 outstanding pings per host is enforced"""
        mock_exists.return_value = True

        # Simulate slow pings that don't complete immediately
        ping_completion_event = threading.Event()

        def slow_ping(*args, **kwargs):
            # Block until event is set
            ping_completion_event.wait(timeout=5.0)
            return (10.0, 64)

        mock_ping.side_effect = slow_ping

        scheduler = Scheduler(interval=0.1, stagger=0.0)  # Fast interval
        sequence_tracker = SequenceTracker(max_outstanding=3)
        host_info = {"id": 0, "host": "192.0.2.1"}
        scheduler.add_host("192.0.2.1")

        result_queue = queue.Queue()
        stop_event = threading.Event()
        pause_event = threading.Event()
        ping_lock = threading.Lock()

        # Run pinger in background
        ping_thread = threading.Thread(
            target=scheduler_driven_ping_host,
            args=(
                host_info,
                scheduler,
                1,  # timeout
                10,  # count - try to send 10 pings
                0.5,  # slow_threshold
                pause_event,
                stop_event,
                result_queue,
                "./ping_helper",
                ping_lock,
                sequence_tracker,
            ),
            daemon=True,
        )
        ping_thread.start()

        # Wait for some pings to be sent
        time.sleep(0.5)

        # Check outstanding count - should be capped at 3
        outstanding = sequence_tracker.get_outstanding_count("192.0.2.1")
        self.assertLessEqual(outstanding, 3)

        # Collect sent events
        sent_events = []
        while not result_queue.empty():
            result = result_queue.get()
            if result.get("status") == "sent":
                sent_events.append(result)

        # Should have sent exactly 3 pings (max outstanding limit)
        self.assertEqual(len(sent_events), 3)

        # Release the ping completions
        ping_completion_event.set()

        # Stop the thread
        stop_event.set()
        ping_thread.join(timeout=2.0)

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_reply_frees_outstanding_slot(self, mock_exists, mock_ping):
        """Test that receiving a reply frees up an outstanding slot"""
        mock_exists.return_value = True

        ping_call_count = [0]
        ping_locks = {}

        def controlled_ping(*args, **kwargs):
            # Extract icmp_seq from kwargs
            icmp_seq = kwargs.get("icmp_seq", 0)
            ping_call_count[0] += 1

            # Create a lock for this sequence if it doesn't exist
            if icmp_seq not in ping_locks:
                ping_locks[icmp_seq] = threading.Event()

            # Wait for the lock to be released
            ping_locks[icmp_seq].wait(timeout=5.0)
            return (10.0, 64)

        mock_ping.side_effect = controlled_ping

        scheduler = Scheduler(interval=0.05, stagger=0.0)  # Very fast interval
        sequence_tracker = SequenceTracker(max_outstanding=3)
        host_info = {"id": 0, "host": "192.0.2.1"}
        scheduler.add_host("192.0.2.1")

        result_queue = queue.Queue()
        stop_event = threading.Event()
        pause_event = threading.Event()
        ping_lock = threading.Lock()

        # Run pinger
        ping_thread = threading.Thread(
            target=scheduler_driven_ping_host,
            args=(
                host_info,
                scheduler,
                1,  # timeout
                6,  # count - try to send 6 pings total
                0.5,  # slow_threshold
                pause_event,
                stop_event,
                result_queue,
                "./ping_helper",
                ping_lock,
                sequence_tracker,
            ),
            daemon=True,
        )
        ping_thread.start()

        # Wait for first 3 pings to be sent
        time.sleep(0.3)

        # Should be at max outstanding
        self.assertEqual(sequence_tracker.get_outstanding_count("192.0.2.1"), 3)

        # Release sequence 0 to complete
        if 0 in ping_locks:
            ping_locks[0].set()
        time.sleep(0.2)

        # Should now have sent a 4th ping (sequence 3)
        # and have 3 outstanding (1, 2, 3)
        self.assertEqual(sequence_tracker.get_outstanding_count("192.0.2.1"), 3)

        # Release sequences 1 and 2
        if 1 in ping_locks:
            ping_locks[1].set()
        if 2 in ping_locks:
            ping_locks[2].set()
        time.sleep(0.2)

        # Should now have sent pings 4 and 5, with 3 outstanding (3, 4, 5)
        self.assertEqual(sequence_tracker.get_outstanding_count("192.0.2.1"), 3)

        # Release all remaining
        for lock in ping_locks.values():
            lock.set()

        stop_event.set()
        ping_thread.join(timeout=2.0)

        # Verify all 6 pings were sent
        sent_events = []
        while not result_queue.empty():
            result = result_queue.get()
            if result.get("status") == "sent":
                sent_events.append(result)

        self.assertEqual(len(sent_events), 6)
        sequences = [e["sequence"] for e in sent_events]
        self.assertEqual(sequences, [0, 1, 2, 3, 4, 5])

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_multiple_hosts_independent_sequences(self, mock_exists, mock_ping):
        """Test that multiple hosts have independent sequence counters"""
        mock_exists.return_value = True
        mock_ping.return_value = (10.0, 64)

        scheduler = Scheduler(interval=1.0, stagger=0.0)
        sequence_tracker = SequenceTracker(max_outstanding=3)

        hosts = ["192.0.2.1", "192.0.2.2", "192.0.2.3"]
        for i, host in enumerate(hosts):
            scheduler.add_host(host, host_id=i)

        result_queue = queue.Queue()
        stop_event = threading.Event()
        pause_event = threading.Event()
        ping_lock = threading.Lock()

        # Run pingers for all hosts
        threads = []
        for i, host in enumerate(hosts):
            host_info = {"id": i, "host": host}
            thread = threading.Thread(
                target=scheduler_driven_ping_host,
                args=(
                    host_info,
                    scheduler,
                    1,  # timeout
                    3,  # count
                    0.5,  # slow_threshold
                    pause_event,
                    stop_event,
                    result_queue,
                    "./ping_helper",
                    ping_lock,
                    sequence_tracker,
                ),
                daemon=True,
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10.0)

        # Collect results by host
        results_by_host = {host: [] for host in hosts}
        while not result_queue.empty():
            result = result_queue.get()
            if result.get("status") == "sent":
                results_by_host[result["host"]].append(result)

        # Each host should have independent sequences starting at 0
        for host in hosts:
            sent_events = results_by_host[host]
            self.assertEqual(len(sent_events), 3, f"Host {host} should have 3 sent events")
            sequences = [e["sequence"] for e in sent_events]
            self.assertEqual(sequences, [0, 1, 2], f"Host {host} should have sequences [0, 1, 2]")

    @patch("paraping.pinger.ping_with_helper")
    @patch("os.path.exists")
    def test_sequence_wraparound_at_65536(self, mock_exists, mock_ping):
        """Test that sequence numbers wrap at uint16 boundary"""
        mock_exists.return_value = True
        mock_ping.return_value = (10.0, 64)

        sequence_tracker = SequenceTracker(max_outstanding=3)
        host = "192.0.2.1"

        # Manually set the sequence counter to near wraparound
        sequence_tracker._sequences[host] = 65534
        sequence_tracker._outstanding[host] = set()

        # Get sequences around wraparound
        seq1 = sequence_tracker.get_next_sequence(host)
        sequence_tracker.mark_replied(host, seq1)

        seq2 = sequence_tracker.get_next_sequence(host)
        sequence_tracker.mark_replied(host, seq2)

        seq3 = sequence_tracker.get_next_sequence(host)
        sequence_tracker.mark_replied(host, seq3)

        # Verify wraparound
        self.assertEqual(seq1, 65534)
        self.assertEqual(seq2, 65535)
        self.assertEqual(seq3, 0)  # Should wrap to 0


if __name__ == "__main__":
    unittest.main()
