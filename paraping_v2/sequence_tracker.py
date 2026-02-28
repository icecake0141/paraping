"""
Per-host ICMP sequence tracking for ParaPing v2.

This implementation is API-compatible with ``paraping.sequence_tracker.SequenceTracker``.
"""

import threading
from typing import Dict, Optional, Set


class SequenceTracker:
    """
    Tracks ICMP sequence numbers and outstanding pings per host.

    This class manages per-host sequence counters and tracks which pings
    are currently in-flight (sent but not yet replied). It enforces a
    maximum of 3 outstanding pings per host to prevent queue buildup.
    """

    def __init__(self, max_outstanding: int = 3) -> None:
        self.max_outstanding = max_outstanding
        self._lock = threading.Lock()
        self._sequences: Dict[str, int] = {}
        self._outstanding: Dict[str, Set[int]] = {}

    def get_next_sequence(self, host: str) -> Optional[int]:
        with self._lock:
            if host not in self._sequences:
                self._sequences[host] = 0
                self._outstanding[host] = set()

            if len(self._outstanding[host]) >= self.max_outstanding:
                return None

            seq = self._sequences[host]
            self._outstanding[host].add(seq)
            self._sequences[host] = (seq + 1) % 65536
            return seq

    def mark_replied(self, host: str, sequence: int) -> bool:
        with self._lock:
            if host not in self._outstanding:
                return False

            if sequence in self._outstanding[host]:
                self._outstanding[host].remove(sequence)
                return True

            return False

    def get_outstanding_count(self, host: str) -> int:
        with self._lock:
            if host not in self._outstanding:
                return 0
            return len(self._outstanding[host])

    def get_outstanding_sequences(self, host: str) -> Set[int]:
        with self._lock:
            if host not in self._outstanding:
                return set()
            return self._outstanding[host].copy()

    def reset_host(self, host: str) -> None:
        with self._lock:
            if host in self._sequences:
                del self._sequences[host]
            if host in self._outstanding:
                del self._outstanding[host]

    def reset_all(self) -> None:
        with self._lock:
            self._sequences.clear()
            self._outstanding.clear()

    def can_send_ping(self, host: str) -> bool:
        with self._lock:
            if host not in self._outstanding:
                return True
            return len(self._outstanding[host]) < self.max_outstanding
