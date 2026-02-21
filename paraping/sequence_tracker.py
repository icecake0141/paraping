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
# Review for correctness and security.

"""
Per-host ICMP sequence tracking for ParaPing.

This module provides a SequenceTracker class that manages ICMP sequence numbers
and outstanding ping tracking for each host. It ensures:
- Unique, incrementing sequence numbers per host (with uint16 wraparound)
- Maximum of 3 outstanding (sent but not replied) pings per host
- Safe reply matching by tracking sent sequences
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
        """
        Initialize the SequenceTracker.

        Args:
            max_outstanding: Maximum number of outstanding pings per host (default: 3)
        """
        self.max_outstanding = max_outstanding
        self._lock = threading.Lock()
        # Per-host sequence counter (wraps at 65536 for uint16)
        self._sequences: Dict[str, int] = {}
        # Per-host set of outstanding (sent but not replied) sequence numbers
        self._outstanding: Dict[str, Set[int]] = {}

    def get_next_sequence(self, host: str) -> Optional[int]:
        """
        Get the next sequence number for a host if under the outstanding limit.

        This method checks if the host has fewer than max_outstanding pings
        in flight. If so, it returns the next sequence number and marks it
        as outstanding. Otherwise, it returns None.

        Args:
            host: The hostname or IP address

        Returns:
            The next sequence number (0-65535) if under limit, None otherwise
        """
        with self._lock:
            # Initialize host tracking if not present
            if host not in self._sequences:
                self._sequences[host] = 0
                self._outstanding[host] = set()

            # Check if we're at the outstanding limit
            if len(self._outstanding[host]) >= self.max_outstanding:
                return None

            # Get next sequence number
            seq = self._sequences[host]

            # Mark as outstanding
            self._outstanding[host].add(seq)

            # Increment counter with uint16 wraparound
            self._sequences[host] = (seq + 1) % 65536

            return seq

    def mark_replied(self, host: str, sequence: int) -> bool:
        """
        Mark a ping as replied, removing it from outstanding tracking.

        Args:
            host: The hostname or IP address
            sequence: The sequence number that was replied to

        Returns:
            True if the sequence was in outstanding set, False otherwise
        """
        with self._lock:
            if host not in self._outstanding:
                return False

            if sequence in self._outstanding[host]:
                self._outstanding[host].remove(sequence)
                return True

            return False

    def get_outstanding_count(self, host: str) -> int:
        """
        Get the number of outstanding pings for a host.

        Args:
            host: The hostname or IP address

        Returns:
            Number of outstanding pings (0 if host not tracked)
        """
        with self._lock:
            if host not in self._outstanding:
                return 0
            return len(self._outstanding[host])

    def get_outstanding_sequences(self, host: str) -> Set[int]:
        """
        Get the set of outstanding sequence numbers for a host.

        Args:
            host: The hostname or IP address

        Returns:
            Set of outstanding sequence numbers (empty set if host not tracked)
        """
        with self._lock:
            if host not in self._outstanding:
                return set()
            return self._outstanding[host].copy()

    def reset_host(self, host: str) -> None:
        """
        Reset tracking for a specific host.

        Args:
            host: The hostname or IP address to reset
        """
        with self._lock:
            if host in self._sequences:
                del self._sequences[host]
            if host in self._outstanding:
                del self._outstanding[host]

    def reset_all(self) -> None:
        """
        Reset tracking for all hosts.
        """
        with self._lock:
            self._sequences.clear()
            self._outstanding.clear()

    def can_send_ping(self, host: str) -> bool:
        """
        Check if a ping can be sent to a host (under outstanding limit).

        Args:
            host: The hostname or IP address

        Returns:
            True if the host has fewer than max_outstanding pings in flight
        """
        with self._lock:
            if host not in self._outstanding:
                return True
            return len(self._outstanding[host]) < self.max_outstanding
