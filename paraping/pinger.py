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
"""

import os
import queue
import socket
import time

from paraping.ping_wrapper import ping_with_helper


def ping_host(
    host,
    timeout,
    count,
    slow_threshold,
    verbose,
    pause_event=None,
    stop_event=None,
    interval=1.0,
    helper_path="./ping_helper",
):
    """
    Ping a single host with the specified parameters.

    Args:
        host: The hostname or IP address to ping
        timeout: Timeout in seconds for each ping
        count: Number of ping attempts (0 for infinite)
        verbose: Whether to show detailed output
        pause_event: Event to pause pinging
        stop_event: Event to stop pinging and exit
        interval: Interval in seconds between pings
        helper_path: Path to ping_helper binary

    Yields:
        A dict with host, sequence, status, and rtt
    """
    if verbose:
        print(f"\n--- Pinging {host} ---")

    if not os.path.exists(helper_path):
        message = f"ping_helper binary not found at {helper_path}. " "Please run 'make build' and 'sudo make setcap'."
        if verbose:
            print(message)
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
        try:
            rtt_ms, ttl = ping_with_helper(host, timeout_ms=int(timeout * 1000), helper_path=helper_path)
            if rtt_ms is not None:
                rtt = rtt_ms / 1000.0
                status = "slow" if rtt >= slow_threshold else "success"
                if verbose:
                    print(f"Reply from {host}: seq={i+1} rtt={rtt:.3f}s ttl={ttl}")
                yield {
                    "host": host,
                    "sequence": i + 1,
                    "status": status,
                    "rtt": rtt,
                    "ttl": ttl,
                }
            else:
                if verbose:
                    print(f"No reply from {host}: seq={i+1}")
                yield {
                    "host": host,
                    "sequence": i + 1,
                    "status": "fail",
                    "rtt": None,
                    "ttl": None,
                }
        except Exception as e:
            if verbose:
                print(f"Error pinging {host}: {e}")
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
    host_info,
    timeout,
    count,
    slow_threshold,
    verbose,
    pause_event,
    stop_event,
    result_queue,
    interval,
    helper_path,
):
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
    ):
        result_queue.put({**result, "host_id": host_info["id"]})
    result_queue.put({"host_id": host_info["id"], "status": "done"})


def resolve_rdns(ip_address):
    """Resolve reverse DNS for an IP address."""
    try:
        return socket.gethostbyaddr(ip_address)[0]
    except (socket.herror, socket.gaierror, OSError):
        return None


def rdns_worker(request_queue, result_queue, stop_event):
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
        result_queue.put((host, resolve_rdns(ip_address)))
        request_queue.task_done()
