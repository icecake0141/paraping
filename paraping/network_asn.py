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
ASN lookup for ParaPing.

This module provides functions for performing ASN lookups via Team Cymru's
whois service and managing ASN worker threads with caching. The module is
designed with separation of concerns:
- Pure parsing functions (unit-testable without network)
- Network client (can be mocked for testing)
- Caching/retry policy (unit-testable with mocked time)
"""

import queue
import socket


def parse_asn_response(response):
    """
    Parse ASN from Team Cymru whois response.

    This is a pure function that takes raw response text and extracts the ASN.
    It can be unit-tested without any network I/O.

    Args:
        response: String containing the whois response

    Returns:
        ASN string (e.g., "AS15133") if successful, None if parsing fails

    Examples:
        >>> parse_asn_response("AS      | IP               | BGP Prefix\\n15133   | 8.8.8.8          | 8.8.8.0/24")
        'AS15133'
        >>> parse_asn_response("NA | 127.0.0.1 | NA")
        None
        >>> parse_asn_response("")
        None
    """
    lines = [line for line in response.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    parts = [part.strip() for part in lines[1].split("|")]
    if not parts:
        return None
    asn = parts[0].replace("AS", "").strip()
    if not asn or asn.upper() == "NA":
        return None
    return f"AS{asn}"


def fetch_asn_via_whois(ip_address, timeout=3.0, max_bytes=65536, host="whois.cymru.com", port=43):
    """
    Fetch raw ASN response from Team Cymru whois service via socket.

    This function handles network I/O and can be mocked in tests.

    Args:
        ip_address: IP address string to lookup
        timeout: Socket timeout in seconds
        max_bytes: Maximum bytes to read from socket
        host: Whois server hostname
        port: Whois server port

    Returns:
        Raw response string if successful, None if network error occurs
    """
    query = f" -v {ip_address}\n".encode("utf-8")
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(query)
            chunks = []
            total_read = 0
            while True:
                remaining = max_bytes - total_read
                if remaining <= 0:
                    break
                chunk = sock.recv(min(4096, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                total_read += len(chunk)
    except (socket.timeout, OSError):
        return None

    return b"".join(chunks).decode("utf-8", errors="ignore")


def resolve_asn(ip_address, timeout=3.0, max_bytes=65536):
    """
    Resolve ASN for an IP address via Team Cymru whois service.

    This is the high-level function that combines network fetch and parsing.

    Args:
        ip_address: IP address string to lookup
        timeout: Socket timeout in seconds
        max_bytes: Maximum bytes to read from socket

    Returns:
        ASN string (e.g., "AS15133") if successful, None if lookup fails
    """
    response = fetch_asn_via_whois(ip_address, timeout, max_bytes)
    if response is None:
        return None
    return parse_asn_response(response)


def asn_worker(request_queue, result_queue, stop_event, timeout):
    """
    Worker thread for processing ASN requests.

    Args:
        request_queue: Queue of (host, ip_address) tuples to process
        result_queue: Queue for results as (host, asn_result) tuples
        stop_event: Threading event to signal worker shutdown
        timeout: Timeout for ASN lookups
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
        result_queue.put((host, resolve_asn(ip_address, timeout=timeout)))
        request_queue.task_done()


def should_retry_asn(ip_address, asn_cache, now, failure_ttl):
    """
    Determine if an ASN lookup should be retried.

    Args:
        ip_address: IP address to check
        asn_cache: Dictionary of cached ASN results
        now: Current timestamp
        failure_ttl: Time-to-live for failed lookups

    Returns:
        True if lookup should be retried, False otherwise
    """
    cached = asn_cache.get(ip_address)
    if cached is None:
        return True
    if cached["value"] is None and (now - cached["fetched_at"]) >= failure_ttl:
        return True
    return False
