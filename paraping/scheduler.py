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
Scheduler module for ParaPing.

This module provides a Scheduler class for managing time-driven ping scheduling
to eliminate timeline drift. The scheduler tracks hosts and computes when pings
should be sent based on configured interval and stagger settings.
"""

import time
from typing import Any, Dict, List, Optional


class Scheduler:
    """
    Time-driven ping scheduler for ParaPing.

    The Scheduler manages ping timing for multiple hosts using a configured
    interval and optional stagger to avoid bursts. It computes next ping times
    and can emit mock send events for testing purposes.
    """

    def __init__(self, interval: float = 1.0, stagger: float = 0.0) -> None:
        """
        Initialize the Scheduler.

        Args:
            interval: Time in seconds between consecutive pings to the same host (default: 1.0)
            stagger: Time offset in seconds between pings to different hosts (default: 0.0)
        """
        self.interval = interval
        self.stagger = stagger
        self.hosts: List[str] = []
        self.host_data: Dict[str, Dict[str, Any]] = {}
        self.start_time: Optional[float] = None

    def add_host(self, host: str, host_id: Optional[int] = None) -> None:
        """
        Add a host to the schedule.

        Args:
            host: The hostname or IP address to schedule
            host_id: Optional numeric identifier for the host
        """
        if host not in self.hosts:
            self.hosts.append(host)
            self.host_data[host] = {
                "id": host_id if host_id is not None else len(self.hosts) - 1,
                "last_ping_time": None,
                "next_ping_time": None,
                "ping_count": 0,
            }

    def set_interval(self, interval: float) -> None:
        """
        Set the ping interval.

        Args:
            interval: Time in seconds between consecutive pings to the same host
        """
        self.interval = interval

    def set_stagger(self, stagger: float) -> None:
        """
        Set the stagger time between hosts.

        Args:
            stagger: Time offset in seconds between pings to different hosts
        """
        self.stagger = stagger

    def reset_timing(self, current_time: Optional[float] = None) -> None:
        """
        Reset the scheduler timing anchors.

        This clears per-host timing data and reanchors the stagger schedule so that
        the next ping cycle starts fresh (e.g., after dormant pauses).

        Args:
            current_time: The current time in seconds (uses time.time() if not provided)
        """
        if current_time is None:
            current_time = time.time()

        self.start_time = current_time
        for host_info in self.host_data.values():
            host_info["last_ping_time"] = None
            host_info["next_ping_time"] = None

    def get_next_ping_times(self, current_time: Optional[float] = None) -> Dict[str, float]:
        """
        Compute when the next pings should be scheduled for all hosts.

        Args:
            current_time: The current time in seconds (uses time.time() if not provided)

        Returns:
            Dictionary mapping host names to their next scheduled ping time
        """
        if current_time is None:
            current_time = time.time()

        # Algorithm overview:
        # - Pin the schedule to a single start_time so stagger offsets are stable across calls.
        # - First ping per host uses start_time + (index * stagger).
        # - Subsequent pings advance strictly by interval from last_ping_time.
        # Key invariants:
        # - host_info["next_ping_time"] is always populated for returned hosts.
        # - start_time is set once and remains constant to avoid drift.
        # Edge cases:
        # - Empty host list returns an empty mapping.
        # - stagger == 0 collapses all first pings to the same start_time.
        if self.start_time is None:
            self.start_time = current_time

        next_times = {}
        for idx, host in enumerate(self.hosts):
            host_info = self.host_data[host]
            last_ping = host_info["last_ping_time"]

            if last_ping is None:
                # First ping: apply stagger based on host index
                next_time = self.start_time + (idx * self.stagger)
            else:
                # Subsequent pings: add interval to last ping time
                next_time = last_ping + self.interval
                # If the computed time is in the past (e.g., after a long pause such as
                # dormant mode), re-anchor to current_time with the host's stagger offset
                # so that the inter-host spacing is preserved when pinging resumes.
                if next_time < current_time:
                    next_time = current_time + (idx * self.stagger)

            next_times[host] = next_time
            host_info["next_ping_time"] = next_time

        return next_times

    def mark_ping_sent(self, host: str, sent_time: Optional[float] = None) -> None:
        """
        Mark that a ping was sent to a host at the given time.

        Args:
            host: The hostname or IP address
            sent_time: The time the ping was sent (uses time.time() if not provided)
        """
        if sent_time is None:
            sent_time = time.time()

        if host in self.host_data:
            self.host_data[host]["last_ping_time"] = sent_time
            self.host_data[host]["ping_count"] += 1

    def emit_mock_send_events(self, count: int = 1) -> List[Dict[str, Any]]:
        """
        Generate mock send events for testing.

        Args:
            count: Number of mock events to generate per host

        Returns:
            List of mock send event dictionaries with host, time, and sequence info
        """
        events = []
        current_time = time.time()

        for _ in range(count):
            next_times = self.get_next_ping_times(current_time)

            # Sort hosts by their next scheduled time
            sorted_hosts = sorted(next_times.items(), key=lambda x: x[1])

            for host, scheduled_time in sorted_hosts:
                event = {
                    "host": host,
                    "scheduled_time": scheduled_time,
                    "sequence": self.host_data[host]["ping_count"] + 1,
                    "event_type": "send",
                }
                events.append(event)

                # Mark as sent and update for next iteration
                self.mark_ping_sent(host, scheduled_time)

            # Move to next round
            if sorted_hosts:
                # Advance to the latest scheduled time plus stagger so mock rounds
                # preserve the intended spacing between host send events.
                current_time = sorted_hosts[-1][1] + self.stagger

        return events

    def get_host_count(self) -> int:
        """
        Get the number of hosts in the schedule.

        Returns:
            Number of hosts currently scheduled
        """
        return len(self.hosts)

    def get_hosts(self) -> List[str]:
        """
        Get the list of scheduled hosts.

        Returns:
            List of host names
        """
        return self.hosts.copy()

    def reset(self) -> None:
        """
        Reset the scheduler state, clearing all hosts and timing data.
        """
        self.hosts = []
        self.host_data = {}
        self.start_time = None
