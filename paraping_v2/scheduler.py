"""
Scheduler module for ParaPing v2.

This implementation is API-compatible with ``paraping.scheduler.Scheduler``.
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
        self.interval = interval
        self.stagger = stagger
        self.hosts: List[str] = []
        self.host_data: Dict[str, Dict[str, Any]] = {}
        self.start_time: Optional[float] = None

    def add_host(self, host: str, host_id: Optional[int] = None) -> None:
        if host not in self.hosts:
            self.hosts.append(host)
            self.host_data[host] = {
                "id": host_id if host_id is not None else len(self.hosts) - 1,
                "last_ping_time": None,
                "next_ping_time": None,
                "ping_count": 0,
            }

    def remove_host(self, host: str) -> None:
        """Remove a host from scheduler tracking."""
        if host in self.hosts:
            self.hosts.remove(host)
            self.host_data.pop(host, None)

    def set_interval(self, interval: float) -> None:
        self.interval = interval

    def set_stagger(self, stagger: float) -> None:
        self.stagger = stagger

    def reset_timing(self, current_time: Optional[float] = None) -> None:
        if current_time is None:
            current_time = time.time()

        self.start_time = current_time
        for host_info in self.host_data.values():
            host_info["last_ping_time"] = None
            host_info["next_ping_time"] = None

    def get_next_ping_times(self, current_time: Optional[float] = None) -> Dict[str, float]:
        if current_time is None:
            current_time = time.time()

        if self.start_time is None:
            self.start_time = current_time

        next_times = {}
        for idx, host in enumerate(self.hosts):
            host_info = self.host_data[host]
            last_ping = host_info["last_ping_time"]

            if last_ping is None:
                next_time = self.start_time + (idx * self.stagger)
            else:
                next_time = last_ping + self.interval
                if next_time < current_time:
                    next_time = current_time + (idx * self.stagger)

            next_times[host] = next_time
            host_info["next_ping_time"] = next_time

        return next_times

    def mark_ping_sent(self, host: str, sent_time: Optional[float] = None) -> None:
        if sent_time is None:
            sent_time = time.time()

        if host in self.host_data:
            self.host_data[host]["last_ping_time"] = sent_time
            self.host_data[host]["ping_count"] += 1

    def emit_mock_send_events(self, count: int = 1) -> List[Dict[str, Any]]:
        events = []
        current_time = time.time()

        for _ in range(count):
            next_times = self.get_next_ping_times(current_time)
            sorted_hosts = sorted(next_times.items(), key=lambda x: x[1])

            for host, scheduled_time in sorted_hosts:
                event = {
                    "host": host,
                    "scheduled_time": scheduled_time,
                    "sequence": self.host_data[host]["ping_count"] + 1,
                    "event_type": "send",
                }
                events.append(event)
                self.mark_ping_sent(host, scheduled_time)

            if sorted_hosts:
                current_time = sorted_hosts[-1][1] + self.stagger

        return events

    def get_host_count(self) -> int:
        return len(self.hosts)

    def get_hosts(self) -> List[str]:
        return self.hosts.copy()

    def reset(self) -> None:
        self.hosts = []
        self.host_data = {}
        self.start_time = None
