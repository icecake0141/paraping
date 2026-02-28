"""
Domain objects for the v2 rewrite.

These structures are intentionally UI-agnostic and network-agnostic so they
can be reused by both CLI and future interfaces.
"""

from dataclasses import dataclass
from typing import Literal, Optional

PingStatus = Literal["sent", "success", "slow", "fail"]


@dataclass(frozen=True)
class HostInfo:
    """Host identity used in monitoring state."""

    host_id: int
    host: str
    alias: str


@dataclass
class HostStats:
    """Aggregated counters and RTT moments for one host."""

    success: int = 0
    slow: int = 0
    fail: int = 0
    total: int = 0
    rtt_sum: float = 0.0
    rtt_sum_sq: float = 0.0
    rtt_count: int = 0


@dataclass(frozen=True)
class PingEvent:
    """Normalized ping event produced by workers."""

    host_id: int
    sequence: int
    status: PingStatus
    sent_time: float
    rtt_seconds: Optional[float] = None
    ttl: Optional[int] = None
