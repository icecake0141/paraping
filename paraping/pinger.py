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
Ping functionality for ParaPing.

This module contains functions for pinging hosts and managing ping worker threads.
A new optional parameter `emit_pending` allows the caller to receive a short-lived
"sent" event immediately when a ping is dispatched so that the UI can reserve a
time-slot (pending marker) and avoid timeline drift when replies are delayed.
"""

import logging
import os
import queue
import socket
import threading
import time
from queue import Queue
from typing import Any, Dict, Iterator, Optional, Tuple

from paraping.ping_wrapper import PingHelperError, ping_with_helper
from paraping.scheduler import Scheduler
from paraping.sequence_tracker import SequenceTracker

logger = logging.getLogger(__name__)


def ping_host(
    host: str,
    timeout: float,
    count: int,
    slow_threshold: float,
    verbose: bool,
    pause_event: Optional[threading.Event] = None,
    stop_event: Optional[threading.Event] = None,
    interval: float = 1.0,
    helper_path: str = "./bin/ping_helper",
    emit_pending: bool = False,
) -> Iterator[Dict[str, Any]]:
    """
    Ping a single host with the specified parameters.

    Args:
        host: The hostname or IP address to ping
        timeout: Timeout in seconds for each ping
        count: Number of ping attempts (0 for infinite)
        slow_threshold: RTT threshold (seconds) to classify as 'slow'
        verbose: Whether to show detailed output
        pause_event: Event to pause pinging
        stop_event: Event to stop pinging and exit
        interval: Interval in seconds between pings
        helper_path: Path to ping_helper binary
        emit_pending: If True, yield a 'sent' event before attempting the ping
                      so the caller can create a pending timeline slot.

    Yields:
        A dict with host, sequence, status, and rtt/ttl (rtt is seconds) or None
    """
    if verbose:
        logger.info("\n--- Pinging %s ---", host)

    if not os.path.exists(helper_path):
        message = f"ping_helper binary not found at {helper_path}. " "Please run 'make build' and 'sudo make setcap'."
        if verbose:
            logger.info(message)
        yield {
            "host": host,
            "sequence": 1,
            "status": "fail",
            "rtt": None,
            "ttl": None,
        }
        return

    i = 0
    while True:
        if stop_event is not None and stop_event.is_set():
            break
        # Check if we should stop (only when count is not 0)
        if count > 0 and i >= count:
            break

        if pause_event is not None:
            while pause_event.is_set():
                if stop_event is not None and stop_event.is_set():
                    return
                time.sleep(0.05)

        # Emit a short-lived 'sent' event before performing the blocking ping.
        # This allows the UI to append a pending marker synchronously with the
        # send time and keep timeline columns aligned across hosts.
        if emit_pending:
            sent_time = time.time()
            yield {
                "host": host,
                "sequence": i + 1,
                "status": "sent",
                "rtt": None,
                "ttl": None,
                "sent_time": sent_time,
            }

        try:
            rtt_ms, ttl = ping_with_helper(host, timeout_ms=int(timeout * 1000), helper_path=helper_path)
            if rtt_ms is not None:
                rtt = rtt_ms / 1000.0
                status = "slow" if rtt >= slow_threshold else "success"
                if verbose:
                    logger.info("Reply from %s: seq=%d rtt=%.3fs ttl=%s", host, i + 1, rtt, ttl)
                yield {
                    "host": host,
                    "sequence": i + 1,
                    "status": status,
                    "rtt": rtt,
                    "ttl": ttl,
                }
            else:
                if verbose:
                    logger.info("No reply from %s: seq=%d", host, i + 1)
                yield {
                    "host": host,
                    "sequence": i + 1,
                    "status": "fail",
                    "rtt": None,
                    "ttl": None,
                }
        except (OSError, PingHelperError, ValueError) as e:
            if verbose:
                logger.info("Error pinging %s: %s", host, e)
            logger.warning("Error pinging %s (seq=%d): %s", host, i + 1, e)
            yield {
                "host": host,
                "sequence": i + 1,
                "status": "fail",
                "rtt": None,
                "ttl": None,
            }

        i += 1

        # Sleep for interval between pings (but not after the last ping when count > 0)
        if count == 0 or i < count:
            if stop_event is None or not stop_event.is_set():
                time.sleep(interval)


def worker_ping(
    host_info: Dict[str, Any],
    timeout: float,
    count: int,
    slow_threshold: float,
    verbose: bool,
    pause_event: Optional[threading.Event],
    stop_event: Optional[threading.Event],
    result_queue: "Queue[Dict[str, Any]]",
    interval: float,
    helper_path: str,
) -> None:
    """Worker function to ping a host and put results in a queue."""
    for result in ping_host(
        host_info["host"],
        timeout,
        count,
        slow_threshold,
        verbose,
        pause_event,
        stop_event,
        interval,
        helper_path,
        emit_pending=True,  # Emit pending events when running as a worker
    ):
        result_queue.put({**result, "host_id": host_info["id"]})
    result_queue.put({"host_id": host_info["id"], "status": "done"})


def resolve_rdns(ip_address: str) -> Optional[str]:
    """Resolve reverse DNS for an IP address."""
    try:
        return socket.gethostbyaddr(ip_address)[0]
    except (socket.herror, socket.gaierror, OSError):
        return None


def rdns_worker(
    request_queue: "Queue[Optional[Tuple[str, str]]]",
    result_queue: "Queue[Tuple[str, Optional[str]]]",
    stop_event: threading.Event,
) -> None:
    """Worker thread for processing reverse DNS requests."""
    while not stop_event.is_set():
        try:
            item = request_queue.get(timeout=0.1)
        except queue.Empty:
            continue
        if item is None:
            request_queue.task_done()
            break
        host, ip_address = item
        try:
            result = resolve_rdns(ip_address)
        except (socket.herror, socket.gaierror, OSError) as e:
            logger.warning("rDNS lookup failed for %s: %s", ip_address, e)
            result = None
        result_queue.put((host, result))
        request_queue.task_done()


def scheduler_driven_ping_host(
    host_info: Dict[str, Any],
    scheduler: Scheduler,
    timeout: float,
    count: int,
    slow_threshold: float,
    pause_event: Optional[threading.Event],
    stop_event: Optional[threading.Event],
    result_queue: "Queue[Dict[str, Any]]",
    helper_path: str,
    ping_lock: Any,
    sequence_tracker: Optional[SequenceTracker] = None,
) -> None:
    """
    Ping a host using scheduler-driven timing with real-time event loop.

    This function uses a monotonic clock and the Scheduler API to send pings
    at precisely scheduled times without waiting for previous ping responses.
    It uses a SequenceTracker to manage per-host ICMP sequence numbers and
    enforce a maximum of 3 outstanding pings per host.

    Args:
        host_info: Dict with 'host' and 'id' keys
        scheduler: Scheduler instance managing timing for all hosts
        timeout: Timeout in seconds for each ping
        count: Number of pings (0 for infinite)
        slow_threshold: RTT threshold to classify as 'slow'
        pause_event: Event to pause pinging
        stop_event: Event to stop pinging
        result_queue: Queue to put ping results
        helper_path: Path to ping_helper binary
        ping_lock: Lock to synchronize access to scheduler
        sequence_tracker: Optional SequenceTracker instance for managing sequences
                         and outstanding pings (creates new if None)
    """
    host = host_info["host"]
    host_id = host_info["id"]

    # Create sequence tracker if not provided
    if sequence_tracker is None:
        sequence_tracker = SequenceTracker(max_outstanding=3)

    if not os.path.exists(helper_path):
        result_queue.put(
            {
                "host": host,
                "host_id": host_id,
                "sequence": 1,
                "status": "fail",
                "rtt": None,
                "ttl": None,
            }
        )
        result_queue.put({"host_id": host_id, "status": "done"})
        return

    ping_count = 0

    while True:
        # Check stop condition
        if stop_event is not None and stop_event.is_set():
            break

        # Check count limit
        if count > 0 and ping_count >= count:
            break

        # Handle pause
        if pause_event is not None:
            paused_during_wait = False
            while pause_event.is_set():
                if not paused_during_wait:
                    paused_during_wait = True
                if stop_event is not None and stop_event.is_set():
                    result_queue.put({"host_id": host_id, "status": "done"})
                    return
                time.sleep(0.05)
            if paused_during_wait:
                # Restart the loop to reschedule based on the current time after a pause.
                continue

        # Get next scheduled ping time from scheduler
        with ping_lock:
            current_realtime = time.time()
            next_times = scheduler.get_next_ping_times(current_realtime)
            next_ping_time = next_times.get(host)

        if next_ping_time is None:
            # Host not in scheduler, shouldn't happen
            break

        # Convert to monotonic time for accurate sleep
        # Note: This conversion assumes system clock doesn't change significantly during execution.
        # If system time adjustments occur, scheduling accuracy may be affected.
        current_monotonic = time.monotonic()
        current_realtime = time.time()
        time_until_ping = next_ping_time - current_realtime
        target_monotonic = current_monotonic + time_until_ping

        # Sleep until scheduled time (with small granularity for responsiveness)
        while True:
            if stop_event is not None and stop_event.is_set():
                result_queue.put({"host_id": host_id, "status": "done"})
                return

            current_monotonic = time.monotonic()
            remaining = target_monotonic - current_monotonic

            if remaining <= 0:
                break

            # Sleep in small increments to remain responsive
            sleep_time = min(0.01, remaining)
            time.sleep(sleep_time)

        # Check pause again before sending
        if pause_event is not None:
            while pause_event.is_set():
                if stop_event is not None and stop_event.is_set():
                    result_queue.put({"host_id": host_id, "status": "done"})
                    return
                time.sleep(0.05)

        # Get next sequence number (enforces max 3 outstanding pings)
        icmp_seq = sequence_tracker.get_next_sequence(host)
        if icmp_seq is None:
            # At max outstanding limit, skip this ping
            # Mark ping as sent in scheduler to keep timing aligned
            with ping_lock:
                scheduler.mark_ping_sent(host, time.time())
            continue

        ping_count += 1
        sent_time = time.time()

        # Emit 'sent' event for UI pending marker
        result_queue.put(
            {
                "host": host,
                "host_id": host_id,
                "sequence": icmp_seq,
                "status": "sent",
                "rtt": None,
                "ttl": None,
                "sent_time": sent_time,
            }
        )

        # Mark ping as sent in scheduler
        with ping_lock:
            scheduler.mark_ping_sent(host, sent_time)

        # Perform the actual ping in a background thread to not block scheduling
        def execute_ping_async(seq_num: int) -> None:
            try:
                rtt_ms, ttl = ping_with_helper(host, timeout_ms=int(timeout * 1000), helper_path=helper_path, icmp_seq=seq_num)
                # Mark as replied regardless of success/failure
                sequence_tracker.mark_replied(host, seq_num)

                if rtt_ms is not None:
                    rtt = rtt_ms / 1000.0
                    status = "slow" if rtt >= slow_threshold else "success"
                    result_queue.put(
                        {
                            "host": host,
                            "host_id": host_id,
                            "sequence": seq_num,
                            "status": status,
                            "rtt": rtt,
                            "ttl": ttl,
                        }
                    )
                else:
                    result_queue.put(
                        {
                            "host": host,
                            "host_id": host_id,
                            "sequence": seq_num,
                            "status": "fail",
                            "rtt": None,
                            "ttl": None,
                        }
                    )
            except (OSError, PingHelperError, ValueError) as e:
                # Mark as replied on exception too
                logger.warning("Error in async ping for %s (seq=%d): %s", host, seq_num, e)
                sequence_tracker.mark_replied(host, seq_num)
                result_queue.put(
                    {
                        "host": host,
                        "host_id": host_id,
                        "sequence": seq_num,
                        "status": "fail",
                        "rtt": None,
                        "ttl": None,
                    }
                )

        # Launch ping in background thread
        ping_thread = threading.Thread(target=execute_ping_async, args=(icmp_seq,), daemon=True)
        ping_thread.start()

    result_queue.put({"host_id": host_id, "status": "done"})


def scheduler_driven_worker_ping(
    host_info: Dict[str, Any],
    scheduler: Scheduler,
    timeout: float,
    count: int,
    slow_threshold: float,
    pause_event: Optional[threading.Event],
    stop_event: Optional[threading.Event],
    result_queue: "Queue[Dict[str, Any]]",
    helper_path: str,
    ping_lock: Any,
    sequence_tracker: Optional[SequenceTracker] = None,
) -> None:
    """
    Worker wrapper for scheduler-driven ping.

    This is the entry point for threading, calling scheduler_driven_ping_host.

    Args:
        host_info: Dict with 'host' and 'id' keys
        scheduler: Scheduler instance managing timing for all hosts
        timeout: Timeout in seconds for each ping
        count: Number of pings (0 for infinite)
        slow_threshold: RTT threshold to classify as 'slow'
        pause_event: Event to pause pinging
        stop_event: Event to stop pinging
        result_queue: Queue to put ping results
        helper_path: Path to ping_helper binary
        ping_lock: Lock to synchronize access to scheduler
        sequence_tracker: Optional shared SequenceTracker instance
    """
    scheduler_driven_ping_host(
        host_info,
        scheduler,
        timeout,
        count,
        slow_threshold,
        pause_event,
        stop_event,
        result_queue,
        helper_path,
        ping_lock,
        sequence_tracker,
    )
