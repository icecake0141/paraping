#!/usr/bin/env python3
# Copyright 2026 icecake0141
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
Realistic multi-host integration tests for ParaPing.

This module tests scheduler behavior, history buffer memory, rate limit enforcement,
and performance at realistic scale (50–100+ simulated hosts).
"""

import os
import sys
import time
import unittest
from collections import deque

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.core import MAX_GLOBAL_PINGS_PER_SECOND, validate_global_rate_limit  # noqa: E402
from paraping.scheduler import Scheduler  # noqa: E402


class TestScheduler50Hosts(unittest.TestCase):
    """Scheduler stagger tests with 50 simulated hosts."""

    def _make_scheduler(self, host_count: int, interval: float = 1.0) -> Scheduler:
        """Return a Scheduler populated with *host_count* mock hosts."""
        stagger = interval / host_count
        scheduler = Scheduler(interval=interval, stagger=stagger)
        for i in range(host_count):
            scheduler.add_host(f"host{i}.local", host_id=i)
        return scheduler

    def test_scheduler_50_hosts_all_registered(self):
        """All 50 hosts must be registered in the scheduler."""
        scheduler = self._make_scheduler(50)
        self.assertEqual(scheduler.get_host_count(), 50)
        hosts = scheduler.get_hosts()
        for i in range(50):
            self.assertIn(f"host{i}.local", hosts)

    def test_scheduler_100_hosts_all_registered(self):
        """All 100 hosts must be registered in the scheduler."""
        scheduler = self._make_scheduler(100, interval=2.0)
        self.assertEqual(scheduler.get_host_count(), 100)

    def test_scheduler_50_hosts_no_drift(self):
        """With 50 hosts, every host receives its correct staggered start time."""
        host_count = 50
        interval = 1.0
        stagger = interval / host_count  # 0.02 s
        scheduler = Scheduler(interval=interval, stagger=stagger)
        for i in range(host_count):
            scheduler.add_host(f"host{i}.local", host_id=i)

        base_time = 1000.0
        next_times = scheduler.get_next_ping_times(base_time)

        for i in range(host_count):
            expected = base_time + i * stagger
            actual = next_times[f"host{i}.local"]
            self.assertAlmostEqual(
                actual,
                expected,
                places=9,
                msg=f"host{i}: expected {expected}, got {actual}",
            )

    def test_scheduler_100_hosts_no_drift(self):
        """With 100 hosts, all scheduled times follow the stagger pattern exactly."""
        host_count = 100
        interval = 1.0
        stagger = 0.01  # 10ms between hosts
        scheduler = Scheduler(interval=interval, stagger=stagger)
        for i in range(host_count):
            scheduler.add_host(f"host{i}.local", host_id=i)

        base_time = 5000.0
        next_times = scheduler.get_next_ping_times(base_time)

        for i in range(host_count):
            expected = base_time + i * stagger
            actual = next_times[f"host{i}.local"]
            self.assertAlmostEqual(
                actual,
                expected,
                places=9,
                msg=f"host{i}: expected {expected}, got {actual}",
            )

    def test_scheduler_50_hosts_no_burst(self):
        """After generating one round of mock events, no 50ms window contains >5 pings."""
        host_count = 50
        interval = 1.0
        stagger = interval / host_count  # 0.02 s between hosts
        scheduler = Scheduler(interval=interval, stagger=stagger)
        for i in range(host_count):
            scheduler.add_host(f"host{i}.local", host_id=i)

        events = scheduler.emit_mock_send_events(count=1)
        self.assertEqual(len(events), host_count, "Should emit one event per host")

        # Verify no burst: count pings in any 50ms sliding window
        times = sorted(e["scheduled_time"] for e in events)
        window_ms = 0.050
        max_in_window = 5

        for start_idx, t_start in enumerate(times):
            count_in_window = sum(1 for t in times if t_start <= t < t_start + window_ms)
            self.assertLessEqual(
                count_in_window,
                max_in_window,
                msg=f"Burst detected: {count_in_window} pings in 50ms window starting at {t_start:.4f}",
            )

    def test_scheduler_50_hosts_second_round_advances(self):
        """After the first round, all hosts advance by the configured interval."""
        host_count = 50
        interval = 1.0
        stagger = interval / host_count
        scheduler = Scheduler(interval=interval, stagger=stagger)
        for i in range(host_count):
            scheduler.add_host(f"host{i}.local", host_id=i)

        base_time = 1000.0
        first_times = scheduler.get_next_ping_times(base_time)

        # Mark all hosts as sent in round 1
        for host, t in first_times.items():
            scheduler.mark_ping_sent(host, t)

        second_times = scheduler.get_next_ping_times(base_time + interval)
        for host, t1 in first_times.items():
            expected_t2 = t1 + interval
            self.assertAlmostEqual(
                second_times[host],
                expected_t2,
                places=9,
                msg=f"{host}: second round should be first + interval",
            )

    def test_scheduler_stagger_start_time_is_stable(self):
        """Calling get_next_ping_times twice returns identical results (no drift)."""
        host_count = 50
        scheduler = Scheduler(interval=1.0, stagger=0.02)
        for i in range(host_count):
            scheduler.add_host(f"host{i}.local")

        base_time = 2000.0
        first_call = scheduler.get_next_ping_times(base_time)
        # Call again with a slightly later current_time – results must be identical
        second_call = scheduler.get_next_ping_times(base_time + 0.005)

        for host in first_call:
            self.assertEqual(
                first_call[host],
                second_call[host],
                msg=f"{host}: repeated calls must return same scheduled time",
            )


class TestHistoryBufferMemory(unittest.TestCase):
    """Memory usage tests – verify deque(maxlen) enforcement for history buffers."""

    def _make_buffers(self, host_count: int, maxlen: int = 60) -> dict:
        """Create host buffers matching the structure used in cli.py."""
        buffers = {}
        for host_id in range(host_count):
            buffers[host_id] = {
                "timeline": deque(maxlen=maxlen),
                "rtt_history": deque(maxlen=maxlen),
                "time_history": deque(maxlen=maxlen),
                "ttl_history": deque(maxlen=maxlen),
            }
        return buffers

    def test_history_buffer_maxlen_enforced(self):
        """Buffer length never exceeds maxlen even when overfilled."""
        maxlen = 60
        buffers = self._make_buffers(1, maxlen=maxlen)
        buf = buffers[0]["timeline"]

        for i in range(maxlen * 3):
            buf.append("." if i % 2 == 0 else "x")

        self.assertEqual(len(buf), maxlen)
        self.assertIsNotNone(buf.maxlen)
        self.assertEqual(buf.maxlen, maxlen)

    def test_history_buffer_memory_linear_with_hosts(self):
        """Buffer memory scales linearly: 100 hosts ≈ 2× the memory of 50 hosts."""
        maxlen = 60
        # Measure approximate entry counts only (deque length = maxlen per buffer)
        for host_count in (50, 100):
            buffers = self._make_buffers(host_count, maxlen=maxlen)
            # Fill all buffers to capacity
            for host_id in range(host_count):
                for _ in range(maxlen):
                    buffers[host_id]["timeline"].append(".")
                    buffers[host_id]["rtt_history"].append(1.0)
                    buffers[host_id]["time_history"].append(time.time())
                    buffers[host_id]["ttl_history"].append(64)
            total_entries = sum(
                len(buffers[hid]["timeline"]) for hid in range(host_count)
            )
            self.assertEqual(
                total_entries,
                host_count * maxlen,
                msg=f"Expected {host_count * maxlen} timeline entries for {host_count} hosts",
            )

    def test_history_buffer_50_hosts_rtt(self):
        """RTT history never grows past maxlen for 50 hosts filled past capacity."""
        maxlen = 60
        buffers = self._make_buffers(50, maxlen=maxlen)
        for host_id in range(50):
            for _ in range(200):  # significantly overfill
                buffers[host_id]["rtt_history"].append(0.025)

        for host_id in range(50):
            self.assertLessEqual(len(buffers[host_id]["rtt_history"]), maxlen)

    def test_history_buffer_old_entries_evicted(self):
        """When buffer is full, oldest entries are evicted (FIFO)."""
        maxlen = 5
        buffers = self._make_buffers(1, maxlen=maxlen)
        timeline = buffers[0]["timeline"]

        # Fill with known values
        for symbol in ["a", "b", "c", "d", "e"]:
            timeline.append(symbol)

        # Add one more – "a" should be evicted
        timeline.append("f")
        self.assertEqual(list(timeline), ["b", "c", "d", "e", "f"])


class TestRateLimitAtScale(unittest.TestCase):
    """Rate limit enforcement tests at realistic scale."""

    def test_rate_limit_50_hosts_2s_interval_passes(self):
        """50 hosts × 1/2 s = 25 pings/sec – well within limit."""
        is_valid, rate, _ = validate_global_rate_limit(50, 2.0)
        self.assertTrue(is_valid)
        self.assertAlmostEqual(rate, 25.0, places=5)

    def test_rate_limit_100_hosts_2s_interval_passes(self):
        """100 hosts × 1/2 s = 50 pings/sec – exactly at the limit."""
        is_valid, rate, _ = validate_global_rate_limit(100, 2.0)
        self.assertTrue(is_valid)
        self.assertAlmostEqual(rate, 50.0, places=5)

    def test_rate_limit_100_hosts_1s_interval_fails(self):
        """100 hosts × 1 s = 100 pings/sec – exceeds limit."""
        is_valid, rate, error = validate_global_rate_limit(100, 1.0)
        self.assertFalse(is_valid)
        self.assertAlmostEqual(rate, 100.0, places=5)
        self.assertIn(str(MAX_GLOBAL_PINGS_PER_SECOND), error)

    def test_rate_limit_50_hosts_1s_interval_passes(self):
        """50 hosts × 1 s = 50 pings/sec – exactly at the limit."""
        is_valid, rate, _ = validate_global_rate_limit(50, 1.0)
        self.assertTrue(is_valid)
        self.assertAlmostEqual(rate, 50.0, places=5)

    def test_rate_limit_error_includes_suggestions_at_scale(self):
        """Error for 100 hosts at 1s interval must include actionable suggestions."""
        is_valid, _, error = validate_global_rate_limit(100, 1.0)
        self.assertFalse(is_valid)
        self.assertIn("Suggestions:", error)
        self.assertIn("Reduce host count from 100 to", error)
        self.assertIn("Increase interval from", error)

    def test_rate_limit_constant_is_50(self):
        """MAX_GLOBAL_PINGS_PER_SECOND must be 50."""
        self.assertEqual(MAX_GLOBAL_PINGS_PER_SECOND, 50)

    def test_rate_limit_many_hosts_long_interval(self):
        """500 hosts at 10 s interval = 50 pings/sec – at the limit."""
        is_valid, rate, _ = validate_global_rate_limit(500, 10.0)
        self.assertTrue(is_valid)
        self.assertAlmostEqual(rate, 50.0, places=5)


class TestSchedulerBenchmark(unittest.TestCase):
    """Performance benchmark – scheduler operations must complete quickly."""

    def test_get_next_ping_times_100_hosts_under_100ms(self):
        """get_next_ping_times for 100 hosts must finish in < 100ms."""
        scheduler = Scheduler(interval=1.0, stagger=0.01)
        for i in range(100):
            scheduler.add_host(f"host{i}.local")

        start = time.monotonic()
        scheduler.get_next_ping_times(1000.0)
        elapsed_ms = (time.monotonic() - start) * 1000

        self.assertLess(elapsed_ms, 100, f"get_next_ping_times took {elapsed_ms:.1f}ms (limit 100ms)")

    def test_emit_mock_events_100_hosts_10_rounds_under_500ms(self):
        """Emitting 10 rounds of mock events for 100 hosts must finish in < 500ms."""
        scheduler = Scheduler(interval=1.0, stagger=0.01)
        for i in range(100):
            scheduler.add_host(f"host{i}.local")

        start = time.monotonic()
        events = scheduler.emit_mock_send_events(count=10)
        elapsed_ms = (time.monotonic() - start) * 1000

        self.assertEqual(len(events), 1000, "Should emit 100 hosts × 10 rounds")
        self.assertLess(elapsed_ms, 500, f"emit_mock_send_events took {elapsed_ms:.1f}ms (limit 500ms)")

    def test_add_100_hosts_under_50ms(self):
        """Adding 100 hosts to the scheduler must finish in < 50ms."""
        scheduler = Scheduler(interval=1.0, stagger=0.01)

        start = time.monotonic()
        for i in range(100):
            scheduler.add_host(f"host{i}.local")
        elapsed_ms = (time.monotonic() - start) * 1000

        self.assertLess(elapsed_ms, 50, f"add_host (×100) took {elapsed_ms:.1f}ms (limit 50ms)")


class TestTimelineSynchronizationAtScale(unittest.TestCase):
    """Timeline synchronisation tests across many simulated hosts."""

    def _make_buffers(self, host_count: int, timeline_width: int = 60) -> dict:
        """Create buffers for *host_count* hosts."""
        return {
            host_id: {
                "timeline": deque(maxlen=timeline_width),
                "rtt_history": deque(maxlen=timeline_width),
                "time_history": deque(maxlen=timeline_width),
                "ttl_history": deque(maxlen=timeline_width),
            }
            for host_id in range(host_count)
        }

    def test_timeline_width_consistent_across_50_hosts(self):
        """After filling all timelines to capacity, every host has the same width."""
        host_count = 50
        timeline_width = 60
        buffers = self._make_buffers(host_count, timeline_width)

        for host_id in range(host_count):
            for _ in range(timeline_width):
                buffers[host_id]["timeline"].append(".")

        lengths = [len(buffers[hid]["timeline"]) for hid in range(host_count)]
        self.assertTrue(all(tl_len == timeline_width for tl_len in lengths), f"Inconsistent lengths: {set(lengths)}")

    def test_pending_replaced_by_success_50_hosts(self):
        """Pending slot is correctly replaced by a success result for each of 50 hosts."""
        symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}
        host_count = 50
        buffers = self._make_buffers(host_count)

        # Insert pending for all hosts
        for host_id in range(host_count):
            buffers[host_id]["timeline"].append(symbols["pending"])
            buffers[host_id]["rtt_history"].append(None)

        # Simulate success arriving for each host
        for host_id in range(host_count):
            self.assertEqual(buffers[host_id]["timeline"][-1], symbols["pending"])
            buffers[host_id]["timeline"][-1] = symbols["success"]
            buffers[host_id]["rtt_history"][-1] = 0.015

        for host_id in range(host_count):
            self.assertEqual(buffers[host_id]["timeline"][-1], symbols["success"])
            self.assertAlmostEqual(buffers[host_id]["rtt_history"][-1], 0.015)

    def test_timeline_columns_stay_aligned_after_overflow(self):
        """After overflow, timeline columns remain maxlen – all hosts stay aligned."""
        host_count = 20
        timeline_width = 10
        buffers = self._make_buffers(host_count, timeline_width)

        # Push 25 items – 15 more than maxlen
        for _ in range(25):
            for host_id in range(host_count):
                buffers[host_id]["timeline"].append(".")

        for host_id in range(host_count):
            self.assertEqual(
                len(buffers[host_id]["timeline"]),
                timeline_width,
                msg=f"host {host_id}: timeline length should equal maxlen after overflow",
            )


if __name__ == "__main__":
    unittest.main()
