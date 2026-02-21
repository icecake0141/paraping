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
Reverse DNS resolution for ParaPing.

This module provides functions for performing reverse DNS lookups
and managing rDNS worker threads.
"""

import queue
import socket
import threading
from queue import Queue
from typing import Optional, Tuple


def resolve_rdns(ip_address: str) -> Optional[str]:
    """
    Perform reverse DNS lookup for an IP address.

    Args:
        ip_address: IP address string to lookup

    Returns:
        Hostname string if successful, None if lookup fails
    """
    try:
        return socket.gethostbyaddr(ip_address)[0]
    except (socket.herror, socket.gaierror, OSError):
        return None


def rdns_worker(
    request_queue: "Queue[Optional[Tuple[str, str]]]",
    result_queue: "Queue[Tuple[str, Optional[str]]]",
    stop_event: threading.Event,
) -> None:
    """
    Worker thread for processing rDNS requests.

    Args:
        request_queue: Queue of (host, ip_address) tuples to process
        result_queue: Queue for results as (host, rdns_result) tuples
        stop_event: Threading event to signal worker shutdown
    """
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
        except Exception:  # pylint: disable=broad-exception-caught
            result = None
        result_queue.put((host, result))
        request_queue.task_done()
