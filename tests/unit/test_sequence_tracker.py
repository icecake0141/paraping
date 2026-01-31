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
Unit tests for paraping.sequence_tracker module.

This module tests per-host sequence tracking and outstanding ping management.
"""

import os
import sys
import threading
import time
import unittest

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.sequence_tracker import SequenceTracker  # noqa: E402  # pylint: disable=wrong-import-position


class TestSequenceTracker(unittest.TestCase):
    """Test cases for SequenceTracker class"""

    def test_initialization(self):
        """Test SequenceTracker initialization"""
        tracker = SequenceTracker()
        self.assertEqual(tracker.max_outstanding, 3)

        tracker_custom = SequenceTracker(max_outstanding=5)
        self.assertEqual(tracker_custom.max_outstanding, 5)

    def test_first_sequence_is_zero(self):
        """Test that first sequence for a host is 0"""
        tracker = SequenceTracker()
        seq = tracker.get_next_sequence("192.0.2.1")
        self.assertEqual(seq, 0)

    def test_sequence_increments(self):
        """Test that sequence numbers increment for each ping"""
        tracker = SequenceTracker()
        host = "192.0.2.1"

        # Get first 3 sequences
        seq1 = tracker.get_next_sequence(host)
        seq2 = tracker.get_next_sequence(host)
        seq3 = tracker.get_next_sequence(host)

        self.assertEqual(seq1, 0)
        self.assertEqual(seq2, 1)
        self.assertEqual(seq3, 2)

    def test_max_outstanding_limit(self):
        """Test that max outstanding limit is enforced"""
        tracker = SequenceTracker(max_outstanding=3)
        host = "192.0.2.1"

        # Send 3 pings (at limit)
        seq1 = tracker.get_next_sequence(host)
        seq2 = tracker.get_next_sequence(host)
        seq3 = tracker.get_next_sequence(host)

        self.assertIsNotNone(seq1)
        self.assertIsNotNone(seq2)
        self.assertIsNotNone(seq3)

        # 4th ping should be rejected (over limit)
        seq4 = tracker.get_next_sequence(host)
        self.assertIsNone(seq4)

    def test_mark_replied_frees_slot(self):
        """Test that marking a ping as replied frees an outstanding slot"""
        tracker = SequenceTracker(max_outstanding=3)
        host = "192.0.2.1"

        # Fill outstanding slots
        seq1 = tracker.get_next_sequence(host)
        _ = tracker.get_next_sequence(host)  # seq2
        _ = tracker.get_next_sequence(host)  # seq3

        # Should be at limit
        self.assertIsNone(tracker.get_next_sequence(host))

        # Mark one as replied
        result = tracker.mark_replied(host, seq1)
        self.assertTrue(result)

        # Should be able to send another ping now
        seq4 = tracker.get_next_sequence(host)
        self.assertIsNotNone(seq4)
        self.assertEqual(seq4, 3)

    def test_mark_replied_returns_false_for_unknown_sequence(self):
        """Test that mark_replied returns False for unknown sequence"""
        tracker = SequenceTracker()
        host = "192.0.2.1"

        # Mark a sequence that was never sent
        result = tracker.mark_replied(host, 999)
        self.assertFalse(result)

    def test_mark_replied_returns_false_for_unknown_host(self):
        """Test that mark_replied returns False for unknown host"""
        tracker = SequenceTracker()

        # Mark a sequence for a host that was never tracked
        result = tracker.mark_replied("unknown.host", 0)
        self.assertFalse(result)

    def test_sequence_wraparound_at_65536(self):
        """Test that sequence numbers wrap at uint16 boundary (65536)"""
        tracker = SequenceTracker()
        host = "192.0.2.1"

        # Set sequence counter to near wraparound
        tracker._sequences[host] = 65534
        tracker._outstanding[host] = set()

        # Get sequences around wraparound point
        seq1 = tracker.get_next_sequence(host)
        tracker.mark_replied(host, seq1)

        seq2 = tracker.get_next_sequence(host)
        tracker.mark_replied(host, seq2)

        seq3 = tracker.get_next_sequence(host)

        self.assertEqual(seq1, 65534)
        self.assertEqual(seq2, 65535)
        self.assertEqual(seq3, 0)  # Should wrap to 0

    def test_get_outstanding_count(self):
        """Test getting the count of outstanding pings"""
        tracker = SequenceTracker()
        host = "192.0.2.1"

        # Initially zero
        self.assertEqual(tracker.get_outstanding_count(host), 0)

        # Send 2 pings
        tracker.get_next_sequence(host)
        tracker.get_next_sequence(host)

        self.assertEqual(tracker.get_outstanding_count(host), 2)

        # Mark one as replied
        tracker.mark_replied(host, 0)

        self.assertEqual(tracker.get_outstanding_count(host), 1)

    def test_get_outstanding_sequences(self):
        """Test getting the set of outstanding sequences"""
        tracker = SequenceTracker()
        host = "192.0.2.1"

        # Initially empty
        self.assertEqual(tracker.get_outstanding_sequences(host), set())

        # Send 3 pings
        seq1 = tracker.get_next_sequence(host)
        seq2 = tracker.get_next_sequence(host)
        seq3 = tracker.get_next_sequence(host)

        outstanding = tracker.get_outstanding_sequences(host)
        self.assertEqual(outstanding, {seq1, seq2, seq3})

        # Mark one as replied
        tracker.mark_replied(host, seq2)

        outstanding = tracker.get_outstanding_sequences(host)
        self.assertEqual(outstanding, {seq1, seq3})

    def test_can_send_ping(self):
        """Test checking if a ping can be sent"""
        tracker = SequenceTracker(max_outstanding=3)
        host = "192.0.2.1"

        # Initially can send
        self.assertTrue(tracker.can_send_ping(host))

        # Send 3 pings (at limit)
        tracker.get_next_sequence(host)
        tracker.get_next_sequence(host)
        tracker.get_next_sequence(host)

        # At limit, cannot send
        self.assertFalse(tracker.can_send_ping(host))

        # Mark one as replied
        tracker.mark_replied(host, 0)

        # Can send again
        self.assertTrue(tracker.can_send_ping(host))

    def test_reset_host(self):
        """Test resetting a specific host"""
        tracker = SequenceTracker()
        host = "192.0.2.1"

        # Send some pings
        tracker.get_next_sequence(host)
        tracker.get_next_sequence(host)

        # Reset the host
        tracker.reset_host(host)

        # Should start from sequence 0 again
        seq = tracker.get_next_sequence(host)
        self.assertEqual(seq, 0)
        self.assertEqual(tracker.get_outstanding_count(host), 1)

    def test_reset_all(self):
        """Test resetting all hosts"""
        tracker = SequenceTracker()

        # Send pings to multiple hosts
        tracker.get_next_sequence("192.0.2.1")
        tracker.get_next_sequence("192.0.2.2")
        tracker.get_next_sequence("192.0.2.3")

        # Reset all
        tracker.reset_all()

        # All hosts should start from 0
        self.assertEqual(tracker.get_next_sequence("192.0.2.1"), 0)
        self.assertEqual(tracker.get_next_sequence("192.0.2.2"), 0)
        self.assertEqual(tracker.get_next_sequence("192.0.2.3"), 0)

    def test_multiple_hosts_independent(self):
        """Test that multiple hosts have independent sequence tracking"""
        tracker = SequenceTracker()

        # Get sequences for different hosts
        seq1_host1 = tracker.get_next_sequence("192.0.2.1")
        seq1_host2 = tracker.get_next_sequence("192.0.2.2")
        seq2_host1 = tracker.get_next_sequence("192.0.2.1")
        seq2_host2 = tracker.get_next_sequence("192.0.2.2")

        # Each host should have independent sequences
        self.assertEqual(seq1_host1, 0)
        self.assertEqual(seq1_host2, 0)
        self.assertEqual(seq2_host1, 1)
        self.assertEqual(seq2_host2, 1)

        # Outstanding counts should be independent
        self.assertEqual(tracker.get_outstanding_count("192.0.2.1"), 2)
        self.assertEqual(tracker.get_outstanding_count("192.0.2.2"), 2)

    def test_thread_safety(self):
        """Test that SequenceTracker is thread-safe"""
        tracker = SequenceTracker(max_outstanding=100)
        host = "192.0.2.1"
        sequences = []

        def get_sequences(num):
            for _ in range(num):
                seq = tracker.get_next_sequence(host)
                if seq is not None:
                    sequences.append(seq)
                    # Immediately mark as replied to free slot
                    tracker.mark_replied(host, seq)

        # Create multiple threads trying to get sequences
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_sequences, args=(10,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have 100 unique sequences (0-99)
        self.assertEqual(len(sequences), 100)
        self.assertEqual(set(sequences), set(range(100)))

    def test_outstanding_limit_enforced_under_load(self):
        """Test that outstanding limit is strictly enforced under concurrent load"""
        tracker = SequenceTracker(max_outstanding=3)
        host = "192.0.2.1"
        max_outstanding_observed = [0]
        lock = threading.Lock()

        def ping_simulation():
            for _ in range(20):
                seq = tracker.get_next_sequence(host)
                if seq is not None:
                    # Record max outstanding count
                    with lock:
                        current = tracker.get_outstanding_count(host)
                        if current > max_outstanding_observed[0]:
                            max_outstanding_observed[0] = current

                    # Simulate some work
                    time.sleep(0.001)

                    # Mark as replied
                    tracker.mark_replied(host, seq)
                else:
                    # If we can't send, wait a bit
                    time.sleep(0.001)

        # Run multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=ping_simulation)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Max outstanding should never exceed the limit
        self.assertLessEqual(max_outstanding_observed[0], 3)


if __name__ == "__main__":
    unittest.main()
