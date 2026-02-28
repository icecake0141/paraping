"""
Event application engine for the v2 rewrite.

This module encapsulates state mutation rules so behavior can be tested
without terminal rendering concerns.
"""

from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional

from paraping_v2.domain import HostStats, PingEvent


@dataclass
class HostTimeline:
    """Per-host event timeline and metadata."""

    symbols: Deque[str]
    sequence_history: Deque[Optional[int]]
    rtt_history: Deque[Optional[float]]
    time_history: Deque[float]
    ttl_history: Deque[Optional[int]]
    pending_by_sequence: Dict[int, int] = field(default_factory=dict)


class MonitorState:
    """
    Mutable monitor state for v2.

    The key compatibility rule implemented here is:
    - `sent` creates a pending slot (`-`)
    - `success/slow/fail` replaces the pending slot for the same sequence when
      present, otherwise appends a new slot.
    """

    def __init__(self, host_ids: list[int], timeline_width: int = 120) -> None:
        width = max(1, int(timeline_width))
        self._symbols = {"sent": "-", "success": ".", "slow": "!", "fail": "x"}
        self.timelines: Dict[int, HostTimeline] = {
            host_id: HostTimeline(
                symbols=deque(maxlen=width),
                sequence_history=deque(maxlen=width),
                rtt_history=deque(maxlen=width),
                time_history=deque(maxlen=width),
                ttl_history=deque(maxlen=width),
            )
            for host_id in host_ids
        }
        self.stats: Dict[int, HostStats] = {host_id: HostStats() for host_id in host_ids}

    def clone(self) -> "MonitorState":
        """Create a deep-copy clone of this state for history snapshots."""
        host_ids = list(self.timelines.keys())
        width = 1
        if host_ids:
            width = self.timelines[host_ids[0]].symbols.maxlen or 1
        cloned = MonitorState(host_ids=host_ids, timeline_width=width)

        for host_id in host_ids:
            src_timeline = self.timelines[host_id]
            dst_timeline = cloned.timelines[host_id]
            dst_timeline.symbols = deque(src_timeline.symbols, maxlen=src_timeline.symbols.maxlen)
            dst_timeline.sequence_history = deque(src_timeline.sequence_history, maxlen=src_timeline.sequence_history.maxlen)
            dst_timeline.rtt_history = deque(src_timeline.rtt_history, maxlen=src_timeline.rtt_history.maxlen)
            dst_timeline.time_history = deque(src_timeline.time_history, maxlen=src_timeline.time_history.maxlen)
            dst_timeline.ttl_history = deque(src_timeline.ttl_history, maxlen=src_timeline.ttl_history.maxlen)
            dst_timeline.pending_by_sequence = deepcopy(src_timeline.pending_by_sequence)
            cloned.stats[host_id] = deepcopy(self.stats[host_id])

        return cloned

    def apply_event(self, event: PingEvent) -> None:
        """Apply one ping event to timeline and aggregate stats."""
        timeline = self.timelines[event.host_id]

        if event.status == "sent":
            timeline.symbols.append(self._symbols["sent"])
            timeline.sequence_history.append(event.sequence)
            timeline.rtt_history.append(None)
            timeline.time_history.append(event.sent_time)
            timeline.ttl_history.append(None)
            timeline.pending_by_sequence[event.sequence] = len(timeline.symbols) - 1
            return

        pending_index = timeline.pending_by_sequence.pop(event.sequence, None)
        if pending_index is not None and pending_index < len(timeline.symbols):
            timeline.symbols[pending_index] = self._symbols[event.status]
            timeline.sequence_history[pending_index] = event.sequence
            timeline.rtt_history[pending_index] = event.rtt_seconds
            timeline.time_history[pending_index] = event.sent_time
            timeline.ttl_history[pending_index] = event.ttl
        else:
            timeline.symbols.append(self._symbols[event.status])
            timeline.sequence_history.append(event.sequence)
            timeline.rtt_history.append(event.rtt_seconds)
            timeline.time_history.append(event.sent_time)
            timeline.ttl_history.append(event.ttl)

        stats = self.stats[event.host_id]
        stats.total += 1
        if event.status == "success":
            stats.success += 1
        elif event.status == "slow":
            stats.slow += 1
        elif event.status == "fail":
            stats.fail += 1
        if event.rtt_seconds is not None:
            stats.rtt_count += 1
            stats.rtt_sum += event.rtt_seconds
            stats.rtt_sum_sq += event.rtt_seconds**2
