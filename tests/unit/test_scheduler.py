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
Unit tests for paraping.scheduler module.

This module tests the Scheduler class for time-driven ping scheduling,
including host management, timing computation, and mock event generation.
"""

import os
import sys
import time
import unittest

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.scheduler import Scheduler  # noqa: E402  # pylint: disable=wrong-import-position


class TestSchedulerInstantiation(unittest.TestCase):
    """Test cases for Scheduler class instantiation"""

    def test_default_instantiation(self):
        """Test scheduler creation with default parameters"""
        scheduler = Scheduler()
        self.assertEqual(scheduler.interval, 1.0)
        self.assertEqual(scheduler.stagger, 0.0)
        self.assertEqual(scheduler.get_host_count(), 0)
        self.assertIsNone(scheduler.start_time)

    def test_custom_interval_instantiation(self):
        """Test scheduler creation with custom interval"""
        scheduler = Scheduler(interval=2.5)
        self.assertEqual(scheduler.interval, 2.5)
        self.assertEqual(scheduler.stagger, 0.0)

    def test_custom_stagger_instantiation(self):
        """Test scheduler creation with custom stagger"""
        scheduler = Scheduler(interval=1.0, stagger=0.1)
        self.assertEqual(scheduler.interval, 1.0)
        self.assertEqual(scheduler.stagger, 0.1)

    def test_custom_interval_and_stagger(self):
        """Test scheduler creation with both custom interval and stagger"""
        scheduler = Scheduler(interval=3.0, stagger=0.2)
        self.assertEqual(scheduler.interval, 3.0)
        self.assertEqual(scheduler.stagger, 0.2)


class TestSchedulerHostManagement(unittest.TestCase):
    """Test cases for adding and managing hosts"""

    def test_add_single_host(self):
        """Test adding a single host"""
        scheduler = Scheduler()
        scheduler.add_host("192.0.2.1")
        self.assertEqual(scheduler.get_host_count(), 1)
        self.assertIn("192.0.2.1", scheduler.get_hosts())

    def test_add_multiple_hosts(self):
        """Test adding multiple hosts"""
        scheduler = Scheduler()
        scheduler.add_host("192.0.2.1")
        scheduler.add_host("192.0.2.2")
        scheduler.add_host("example.com")
        self.assertEqual(scheduler.get_host_count(), 3)
        hosts = scheduler.get_hosts()
        self.assertIn("192.0.2.1", hosts)
        self.assertIn("192.0.2.2", hosts)
        self.assertIn("example.com", hosts)

    def test_add_duplicate_host(self):
        """Test that adding duplicate hosts doesn't create duplicates"""
        scheduler = Scheduler()
        scheduler.add_host("192.0.2.1")
        scheduler.add_host("192.0.2.1")
        self.assertEqual(scheduler.get_host_count(), 1)

    def test_add_host_with_id(self):
        """Test adding host with custom ID"""
        scheduler = Scheduler()
        scheduler.add_host("192.0.2.1", host_id=42)
        self.assertEqual(scheduler.host_data["192.0.2.1"]["id"], 42)

    def test_host_data_initialization(self):
        """Test that host data is properly initialized"""
        scheduler = Scheduler()
        scheduler.add_host("192.0.2.1")
        host_data = scheduler.host_data["192.0.2.1"]
        self.assertIsNotNone(host_data["id"])
        self.assertIsNone(host_data["last_ping_time"])
        self.assertIsNone(host_data["next_ping_time"])
        self.assertEqual(host_data["ping_count"], 0)


class TestSchedulerConfiguration(unittest.TestCase):
    """Test cases for scheduler configuration methods"""

    def test_set_interval(self):
        """Test setting interval after instantiation"""
        scheduler = Scheduler(interval=1.0)
        scheduler.set_interval(2.5)
        self.assertEqual(scheduler.interval, 2.5)

    def test_set_stagger(self):
        """Test setting stagger after instantiation"""
        scheduler = Scheduler(stagger=0.0)
        scheduler.set_stagger(0.15)
        self.assertEqual(scheduler.stagger, 0.15)


class TestSchedulerNextPingTimes(unittest.TestCase):
    """Test cases for computing next ping times"""

    def test_next_ping_times_single_host(self):
        """Test computing next ping time for a single host"""
        scheduler = Scheduler(interval=1.0, stagger=0.0)
        scheduler.add_host("192.0.2.1")

        current_time = 1000.0
        next_times = scheduler.get_next_ping_times(current_time)

        self.assertIn("192.0.2.1", next_times)
        self.assertEqual(next_times["192.0.2.1"], current_time)

    def test_next_ping_times_multiple_hosts_no_stagger(self):
        """Test computing next ping times for multiple hosts without stagger"""
        scheduler = Scheduler(interval=1.0, stagger=0.0)
        scheduler.add_host("192.0.2.1")
        scheduler.add_host("192.0.2.2")
        scheduler.add_host("192.0.2.3")

        current_time = 1000.0
        next_times = scheduler.get_next_ping_times(current_time)

        # All hosts should be scheduled at the same time (no stagger)
        self.assertEqual(next_times["192.0.2.1"], current_time)
        self.assertEqual(next_times["192.0.2.2"], current_time)
        self.assertEqual(next_times["192.0.2.3"], current_time)

    def test_next_ping_times_multiple_hosts_with_stagger(self):
        """Test computing next ping times for multiple hosts with stagger"""
        scheduler = Scheduler(interval=1.0, stagger=0.1)
        scheduler.add_host("192.0.2.1")
        scheduler.add_host("192.0.2.2")
        scheduler.add_host("192.0.2.3")

        current_time = 1000.0
        next_times = scheduler.get_next_ping_times(current_time)

        # Hosts should be staggered by 0.1 seconds
        self.assertEqual(next_times["192.0.2.1"], current_time)
        self.assertAlmostEqual(next_times["192.0.2.2"], current_time + 0.1, places=6)
        self.assertAlmostEqual(next_times["192.0.2.3"], current_time + 0.2, places=6)

    def test_next_ping_times_after_marking_sent(self):
        """Test that next ping times advance after marking pings as sent"""
        scheduler = Scheduler(interval=2.0, stagger=0.0)
        scheduler.add_host("192.0.2.1")

        current_time = 1000.0
        next_times = scheduler.get_next_ping_times(current_time)
        self.assertEqual(next_times["192.0.2.1"], current_time)

        # Mark ping as sent
        scheduler.mark_ping_sent("192.0.2.1", current_time)

        # Next ping should be interval seconds later
        next_times = scheduler.get_next_ping_times(current_time + 1.0)
        self.assertEqual(next_times["192.0.2.1"], current_time + 2.0)

    def test_next_ping_times_preserves_stagger_after_long_pause(self):
        """Test that stagger offsets are preserved when resuming after a long pause (e.g., dormant mode)"""
        scheduler = Scheduler(interval=1.0, stagger=0.1)
        scheduler.add_host("192.0.2.1")
        scheduler.add_host("192.0.2.2")
        scheduler.add_host("192.0.2.3")

        # Simulate initial pings at t=1000
        start_time = 1000.0
        next_times = scheduler.get_next_ping_times(start_time)
        for host in ["192.0.2.1", "192.0.2.2", "192.0.2.3"]:
            scheduler.mark_ping_sent(host, next_times[host])

        # Simulate a long pause (dormant mode) of 60 seconds
        resume_time = start_time + 60.0

        # After resuming, stagger should be re-applied relative to resume_time
        next_times = scheduler.get_next_ping_times(resume_time)

        # All next_times must be >= resume_time (not stuck in the past)
        for host in ["192.0.2.1", "192.0.2.2", "192.0.2.3"]:
            self.assertGreaterEqual(next_times[host], resume_time)

        # Stagger offsets should be preserved (host 0: +0.0s, host 1: +0.1s, host 2: +0.2s)
        self.assertAlmostEqual(next_times["192.0.2.1"], resume_time + 0.0, places=6)
        self.assertAlmostEqual(next_times["192.0.2.2"], resume_time + 0.1, places=6)
        self.assertAlmostEqual(next_times["192.0.2.3"], resume_time + 0.2, places=6)


class TestSchedulerMarkPingSent(unittest.TestCase):
    """Test cases for marking pings as sent"""

    def test_mark_ping_sent_updates_time(self):
        """Test that marking ping sent updates last ping time"""
        scheduler = Scheduler()
        scheduler.add_host("192.0.2.1")

        sent_time = 1000.0
        scheduler.mark_ping_sent("192.0.2.1", sent_time)

        self.assertEqual(scheduler.host_data["192.0.2.1"]["last_ping_time"], sent_time)

    def test_mark_ping_sent_increments_count(self):
        """Test that marking ping sent increments ping count"""
        scheduler = Scheduler()
        scheduler.add_host("192.0.2.1")

        self.assertEqual(scheduler.host_data["192.0.2.1"]["ping_count"], 0)

        scheduler.mark_ping_sent("192.0.2.1", 1000.0)
        self.assertEqual(scheduler.host_data["192.0.2.1"]["ping_count"], 1)

        scheduler.mark_ping_sent("192.0.2.1", 1001.0)
        self.assertEqual(scheduler.host_data["192.0.2.1"]["ping_count"], 2)

    def test_mark_ping_sent_default_time(self):
        """Test that marking ping sent without time uses current time"""
        scheduler = Scheduler()
        scheduler.add_host("192.0.2.1")

        before = time.time()
        scheduler.mark_ping_sent("192.0.2.1")
        after = time.time()

        last_ping = scheduler.host_data["192.0.2.1"]["last_ping_time"]
        self.assertGreaterEqual(last_ping, before)
        self.assertLessEqual(last_ping, after)


class TestSchedulerMockEvents(unittest.TestCase):
    """Test cases for mock send event generation"""

    def test_emit_mock_send_events_single_host(self):
        """Test generating mock send events for a single host"""
        scheduler = Scheduler(interval=1.0, stagger=0.0)
        scheduler.add_host("192.0.2.1")

        events = scheduler.emit_mock_send_events(count=1)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["host"], "192.0.2.1")
        self.assertEqual(events[0]["event_type"], "send")
        self.assertEqual(events[0]["sequence"], 1)
        self.assertIn("scheduled_time", events[0])

    def test_emit_mock_send_events_multiple_hosts(self):
        """Test generating mock send events for multiple hosts"""
        scheduler = Scheduler(interval=1.0, stagger=0.1)
        scheduler.add_host("192.0.2.1")
        scheduler.add_host("192.0.2.2")
        scheduler.add_host("192.0.2.3")

        events = scheduler.emit_mock_send_events(count=1)

        # Should have 3 events (one per host)
        self.assertEqual(len(events), 3)

        # Check that all hosts are represented
        hosts_in_events = [e["host"] for e in events]
        self.assertIn("192.0.2.1", hosts_in_events)
        self.assertIn("192.0.2.2", hosts_in_events)
        self.assertIn("192.0.2.3", hosts_in_events)

    def test_emit_mock_send_events_multiple_rounds(self):
        """Test generating multiple rounds of mock send events"""
        scheduler = Scheduler(interval=1.0, stagger=0.0)
        scheduler.add_host("192.0.2.1")
        scheduler.add_host("192.0.2.2")

        events = scheduler.emit_mock_send_events(count=3)

        # Should have 6 events total (2 hosts × 3 rounds)
        self.assertEqual(len(events), 6)

        # Check sequence numbers increment
        host1_events = [e for e in events if e["host"] == "192.0.2.1"]
        self.assertEqual(len(host1_events), 3)
        self.assertEqual(host1_events[0]["sequence"], 1)
        self.assertEqual(host1_events[1]["sequence"], 2)
        self.assertEqual(host1_events[2]["sequence"], 3)

    def test_emit_mock_send_events_updates_ping_count(self):
        """Test that emitting mock events updates ping count"""
        scheduler = Scheduler(interval=1.0)
        scheduler.add_host("192.0.2.1")

        self.assertEqual(scheduler.host_data["192.0.2.1"]["ping_count"], 0)

        scheduler.emit_mock_send_events(count=2)

        self.assertEqual(scheduler.host_data["192.0.2.1"]["ping_count"], 2)


class TestSchedulerReset(unittest.TestCase):
    """Test cases for scheduler reset functionality"""

    def test_reset_clears_hosts(self):
        """Test that reset clears all hosts"""
        scheduler = Scheduler()
        scheduler.add_host("192.0.2.1")
        scheduler.add_host("192.0.2.2")

        self.assertEqual(scheduler.get_host_count(), 2)

        scheduler.reset()

        self.assertEqual(scheduler.get_host_count(), 0)
        self.assertEqual(len(scheduler.get_hosts()), 0)

    def test_reset_clears_host_data(self):
        """Test that reset clears all host data"""
        scheduler = Scheduler()
        scheduler.add_host("192.0.2.1")
        scheduler.mark_ping_sent("192.0.2.1", 1000.0)

        scheduler.reset()

        self.assertEqual(len(scheduler.host_data), 0)

    def test_reset_clears_start_time(self):
        """Test that reset clears start time"""
        scheduler = Scheduler()
        scheduler.add_host("192.0.2.1")
        scheduler.get_next_ping_times(1000.0)

        self.assertIsNotNone(scheduler.start_time)

        scheduler.reset()

        self.assertIsNone(scheduler.start_time)


class TestSchedulerIntegration(unittest.TestCase):
    """Integration tests for scheduler functionality"""

    def test_full_scheduling_workflow(self):
        """Test a complete scheduling workflow"""
        scheduler = Scheduler(interval=1.0, stagger=0.1)

        # Add hosts
        scheduler.add_host("host1.example.com")
        scheduler.add_host("host2.example.com")
        scheduler.add_host("host3.example.com")

        # Get initial ping times
        current_time = 1000.0
        next_times = scheduler.get_next_ping_times(current_time)

        # Verify staggered scheduling
        self.assertAlmostEqual(next_times["host1.example.com"], 1000.0, places=6)
        self.assertAlmostEqual(next_times["host2.example.com"], 1000.1, places=6)
        self.assertAlmostEqual(next_times["host3.example.com"], 1000.2, places=6)

        # Mark first host as sent
        scheduler.mark_ping_sent("host1.example.com", next_times["host1.example.com"])

        # Get next ping times again
        next_times = scheduler.get_next_ping_times(current_time + 0.5)

        # First host should be scheduled for interval later
        self.assertEqual(next_times["host1.example.com"], 1001.0)
        # Other hosts should remain at their original times
        self.assertAlmostEqual(next_times["host2.example.com"], 1000.1, places=6)
        self.assertAlmostEqual(next_times["host3.example.com"], 1000.2, places=6)

    def test_scheduled_times_with_sleep(self):
        """Test scheduled times remain consistent across small time delays"""
        scheduler = Scheduler(interval=0.5, stagger=0.05)
        scheduler.add_host("test1.example.com")
        scheduler.add_host("test2.example.com")

        # Get initial times
        base_time = time.time()
        next_times_1 = scheduler.get_next_ping_times(base_time)

        # Small delay
        time.sleep(0.01)

        # Get times again with slightly later current time
        next_times_2 = scheduler.get_next_ping_times(base_time + 0.01)

        # Times should remain the same (based on start_time, not current_time)
        self.assertEqual(next_times_1["test1.example.com"], next_times_2["test1.example.com"])
        self.assertEqual(next_times_1["test2.example.com"], next_times_2["test2.example.com"])


if __name__ == "__main__":
    unittest.main()
