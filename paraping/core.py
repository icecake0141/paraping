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
Core functionality for ParaPing.

This module contains core functions for parsing input, building host information,
managing state snapshots, and history navigation.
"""

import copy
import ipaddress
import socket
import sys
from collections import deque
from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

import paraping.ui_render
from paraping.ui_render import (
    build_display_entries,
    build_display_names,
    compute_main_layout,
    compute_panel_sizes,
    should_show_asn,
)

# Constants for time navigation feature
HISTORY_DURATION_MINUTES = 30  # Store up to 30 minutes of history
SNAPSHOT_INTERVAL_SECONDS = 1.0  # Take snapshot every second
MAX_HOST_THREADS = 128  # Hard cap to avoid unbounded thread growth.
TIMELINE_LABEL_ESTIMATE_WIDTH = 15  # Estimated label column + spacing width.

# Global rate limit for flood protection
MAX_GLOBAL_PINGS_PER_SECOND = 50  # Maximum allowed ICMP pings per second globally


class TerminalSizeLike(Protocol):
    """Protocol for terminal size objects with columns/lines attributes."""

    @property
    def columns(self) -> int: ...

    @property
    def lines(self) -> int: ...


def _build_term_size(columns_value: Any, lines_value: Any) -> Optional[SimpleNamespace]:
    """Build a terminal size namespace from column and line values."""
    try:
        columns = int(columns_value)
        lines = int(lines_value)
    except (ValueError, TypeError):
        return None
    if columns <= 0 or lines <= 0:
        return None
    return SimpleNamespace(columns=columns, lines=lines)


def _normalize_term_size(term_size: Any) -> Optional[SimpleNamespace]:
    """
    Normalize terminal size to an object with .columns and .lines attributes.

    Handles tuple-like sequences, dicts, and objects with columns/lines attributes.

    Args:
        term_size: Terminal size as tuple-like sequence, dict, or object with attributes

    Returns:
        Object with .columns and .lines attributes, or None if invalid
    """
    if term_size is None:
        return None
    if hasattr(term_size, "columns") and hasattr(term_size, "lines"):
        return _build_term_size(term_size.columns, term_size.lines)
    if isinstance(term_size, dict):
        return _build_term_size(term_size.get("columns"), term_size.get("lines"))
    if isinstance(term_size, Sequence) and not isinstance(term_size, (str, bytes)):
        if len(term_size) >= 2:
            try:
                return _build_term_size(term_size[0], term_size[1])
            except TypeError:
                return None
    return None


def _extract_timeline_width_from_layout(layout: Any, main_width: int) -> int:
    """
    Defensively extract timeline width from compute_main_layout result.

    Supports tuple/list indexing and attribute-style extraction with fallbacks.

    Args:
        layout: Result from compute_main_layout (tuple, list, or object)
        main_width: Main panel width for fallback calculation

    Returns:
        int: Timeline width (always >= 1)
    """
    timeline_width = None

    # Method 1: Try tuple/list indexing (expected case)
    if isinstance(layout, (tuple, list)) and len(layout) > 2:
        try:
            timeline_width = layout[2]
        except (TypeError, IndexError):
            timeline_width = None

    # Method 2: Try attribute access (for named tuples or objects)
    if timeline_width is None:
        timeline_width = getattr(layout, "timeline_width", None)

    # Method 3: Fallback to a conservative default based on main_width
    if timeline_width is None:
        # Estimate: main_width minus label column and spacing
        timeline_width = max(1, main_width - TIMELINE_LABEL_ESTIMATE_WIDTH)

    # Ensure timeline_width is a valid integer
    try:
        timeline_width = int(timeline_width)
    except (TypeError, ValueError):
        timeline_width = max(1, main_width - TIMELINE_LABEL_ESTIMATE_WIDTH)

    return max(1, timeline_width)


def parse_host_file_line(line: str, line_number: int, input_file: str) -> Optional[Dict[str, str]]:
    """
    Parse a single line from the host input file.

    Args:
        line: Line of text from the file
        line_number: Line number in the file
        input_file: Path to the input file (for error messages)

    Returns:
        Dict with keys 'host', 'alias', 'ip' or None if invalid/comment
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = [part.strip() for part in stripped.split(",")]
    if len(parts) != 2:
        print(
            f"Warning: Invalid host entry at {input_file}:{line_number}. " "Expected format 'IP,alias'.",
            file=sys.stderr,
        )
        return None
    ip_text, alias = parts
    if not ip_text or not alias:
        print(
            f"Warning: Invalid host entry at {input_file}:{line_number}. " "IP address and alias are required.",
            file=sys.stderr,
        )
        return None
    try:
        ip_obj = ipaddress.ip_address(ip_text)
    except ValueError:
        print(
            f"Warning: Invalid IP address at {input_file}:{line_number}: '{ip_text}'.",
            file=sys.stderr,
        )
        return None
    if ip_obj.version != 4:
        print(
            f"Warning: IPv6 address at {input_file}:{line_number}: '{ip_text}'. "
            "IPv6 is not supported by ping_helper; this entry will likely fail during ping.",
            file=sys.stderr,
        )
    return {"host": ip_text, "alias": alias, "ip": ip_text}


def read_input_file(input_file: str) -> List[Dict[str, str]]:
    """
    Read and parse hosts from an input file.

    Args:
        input_file: Path to the file containing host entries

    Returns:
        List of host info dictionaries
    """
    host_list = []
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                entry = parse_host_file_line(line, line_number, input_file)
                if entry is not None:
                    host_list.append(entry)
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        return []
    except PermissionError:
        print(f"Error: Permission denied reading file '{input_file}'.")
        return []
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error reading input file '{input_file}': {e}")
        return []

    return host_list


def compute_history_page_step(
    host_infos: List[Dict[str, Any]],
    buffers: Dict[int, Any],
    stats: Dict[int, Any],
    symbols: Dict[str, str],
    panel_position: str,
    mode_label: str,
    sort_mode: str,
    filter_mode: str,
    slow_threshold: float,
    show_asn: bool,
    asn_width: int = 8,
    header_lines: int = 2,
) -> int:
    """Compute the page step for history navigation based on timeline width."""
    term_size = paraping.ui_render.get_terminal_size(fallback=(80, 24))
    term_width = term_size.columns
    term_height = term_size.lines
    status_box_height = 3 if term_height >= 4 and term_width >= 2 else 1
    panel_height = max(1, term_height - status_box_height)

    include_asn = should_show_asn(host_infos, mode_label, show_asn, term_width, asn_width=asn_width)
    display_names = build_display_names(host_infos, mode_label, include_asn, asn_width)
    main_width, main_height, _, _, _ = compute_panel_sizes(term_width, panel_height, panel_position)
    display_entries = build_display_entries(
        host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        sort_mode,
        filter_mode,
        slow_threshold,
    )
    host_labels = [entry[1] for entry in display_entries]
    if not host_labels:
        host_labels = [info["alias"] for info in host_infos]

    # Compute layout and extract timeline width defensively
    layout_result = compute_main_layout(host_labels, main_width, main_height, header_lines)
    timeline_width = _extract_timeline_width_from_layout(layout_result, main_width)

    return timeline_width


def get_cached_page_step(
    cached_page_step: Optional[int],
    last_term_size: Optional[TerminalSizeLike],
    host_infos: List[Dict[str, Any]],
    buffers: Dict[int, Any],
    stats: Dict[int, Any],
    symbols: Dict[str, str],
    panel_position: str,
    mode_label: str,
    sort_mode: str,
    filter_mode: str,
    slow_threshold: float,
    show_asn: bool,
) -> Tuple[int, int, Optional[TerminalSizeLike]]:
    """
    Get the page step for history navigation, using cached value if available.

    The page step is only recalculated if the terminal size has changed.
    This prevents expensive recalculation on every arrow key press.

    Returns:
        tuple: (page_step, new_cached_page_step, new_last_term_size)
    """

    def should_recalculate_page_step(last_size: Optional[TerminalSizeLike], current_size: TerminalSizeLike) -> bool:
        """Return True when the terminal size change requires recomputing the page step."""
        if last_size is None:
            return True
        # Normalize last_size to ensure we can access .columns and .lines
        normalized_last = _normalize_term_size(last_size)
        if normalized_last is None:
            return True  # Invalid last_size, recalculate
        if current_size.columns != normalized_last.columns:
            return True  # Terminal width changed
        if current_size.lines != normalized_last.lines:
            return True  # Terminal height changed
        return False

    current_term_size = paraping.ui_render.get_terminal_size(fallback=(80, 24))

    # Check if we need to recalculate
    if cached_page_step is None or should_recalculate_page_step(last_term_size, current_term_size):
        # Terminal size changed or first time - recalculate
        page_step = compute_history_page_step(
            host_infos,
            buffers,
            stats,
            symbols,
            panel_position,
            mode_label,
            sort_mode,
            filter_mode,
            slow_threshold,
            show_asn,
        )
        return page_step, page_step, current_term_size

    # Use cached value
    return cached_page_step, cached_page_step, last_term_size


def build_host_infos(hosts: List[Union[str, Dict[str, str]]]) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """Build host information structures from a list of hosts."""
    host_infos = []
    host_map: Dict[str, List[Dict[str, Any]]] = {}

    def address_from_sockaddr(sockaddr: Tuple[Any, ...]) -> str:
        """Extract a string address from a getaddrinfo sockaddr tuple."""
        address_value = sockaddr[0]
        if isinstance(address_value, str):
            return address_value
        return str(address_value)

    for index, entry in enumerate(hosts):
        if isinstance(entry, str):
            host = entry
            alias = entry
            ip_address: Optional[str] = None
        else:
            host_value = entry.get("host") or entry.get("ip")
            if not host_value:
                entry_keys = ", ".join(sorted(entry.keys()))
                detail = f"Received keys: {entry_keys}" if entry_keys else "Received empty entry"
                raise ValueError(f"Invalid host entry: must contain a non-empty 'host' or 'ip' key. {detail}")
            host = host_value
            alias = entry.get("alias") or host
            ip_address = entry.get("ip")
        if not ip_address:
            try:
                # Use getaddrinfo to get all available addresses (IPv4 and IPv6)
                # Prefer IPv4 addresses when both are available
                addr_info = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_RAW)

                # Extract addresses by family
                # getaddrinfo returns tuples: (family, type, proto, canonname, sockaddr)
                # sockaddr for IPv4 is (address, port), for IPv6 is (address, port, flow, scope)
                ipv4_addresses = []
                ipv6_addresses = []
                for family, _socktype, _proto, _canonname, sockaddr in addr_info:
                    if family == socket.AF_INET:
                        ipv4_addresses.append(address_from_sockaddr(sockaddr))
                    elif family == socket.AF_INET6:
                        ipv6_addresses.append(address_from_sockaddr(sockaddr))

                # Prefer IPv4 over IPv6
                if ipv4_addresses:
                    ip_address = ipv4_addresses[0]
                elif ipv6_addresses:
                    ip_address = ipv6_addresses[0]
                    print(
                        f"Warning: Host '{host}' resolved to IPv6 address '{ip_address}'. "
                        "IPv6 is not supported by ping_helper; pinging will likely fail.",
                        file=sys.stderr,
                    )
                else:
                    ip_address = host
            except (socket.gaierror, OSError):
                ip_address = host
        info = {
            "id": index,
            "host": host,
            "alias": alias,
            "ip": ip_address,
            "rdns": None,
            "rdns_pending": False,
            "asn": None,
            "asn_pending": False,
        }
        host_infos.append(info)
        host_map.setdefault(host, []).append(info)
    return host_infos, host_map


def create_state_snapshot(buffers: Dict[int, Any], stats: Dict[int, Any], timestamp: float) -> Dict[str, Any]:
    """
    Create a deep copy snapshot of current buffers and stats.

    Args:
        buffers: Current buffer state
        stats: Current statistics
        timestamp: Timestamp for this snapshot

    Returns:
        Dict with snapshot data
    """
    # Deep copy buffers (deques and their contents)
    buffers_copy = {}
    for host_id, host_buffers in buffers.items():
        buffers_copy[host_id] = {
            "timeline": deque(host_buffers["timeline"], maxlen=host_buffers["timeline"].maxlen),
            "rtt_history": deque(host_buffers["rtt_history"], maxlen=host_buffers["rtt_history"].maxlen),
            "time_history": deque(host_buffers["time_history"], maxlen=host_buffers["time_history"].maxlen),
            "ttl_history": deque(host_buffers["ttl_history"], maxlen=host_buffers["ttl_history"].maxlen),
            "categories": {
                status: deque(cat_deque, maxlen=cat_deque.maxlen) for status, cat_deque in host_buffers["categories"].items()
            },
        }

    # Deep copy stats
    stats_copy = copy.deepcopy(stats)

    return {
        "timestamp": timestamp,
        "buffers": buffers_copy,
        "stats": stats_copy,
    }


def update_history_buffer(
    history_buffer: "deque[Dict[str, Any]]",
    buffers: Dict[int, Any],
    stats: Dict[int, Any],
    now: float,
    last_snapshot_time: float,
    history_offset: int,
) -> Tuple[float, int]:
    """Update history buffer with new snapshot if enough time has elapsed."""
    if (now - last_snapshot_time) < SNAPSHOT_INTERVAL_SECONDS:
        return last_snapshot_time, history_offset

    snapshot = create_state_snapshot(buffers, stats, now)
    history_buffer.append(snapshot)
    last_snapshot_time = now
    if history_offset > 0:
        history_offset = min(history_offset + 1, len(history_buffer) - 1)
    return last_snapshot_time, history_offset


def resolve_render_state(
    history_offset: int,
    history_buffer: "deque[Dict[str, Any]]",
    buffers: Dict[int, Any],
    stats: Dict[int, Any],
    paused: bool,
) -> Tuple[Dict[int, Any], Dict[int, Any], bool]:
    """Resolve the current render state based on history offset."""
    if 0 < history_offset <= len(history_buffer):
        snapshot = history_buffer[-(history_offset + 1)]
        return snapshot["buffers"], snapshot["stats"], True
    return buffers, stats, paused


def validate_global_rate_limit(host_count: int, interval: float) -> Tuple[bool, float, str]:
    """
    Validate that the requested ping rate does not exceed the global limit.

    Args:
        host_count: Number of hosts to ping
        interval: Interval in seconds between pings per host

    Returns:
        Tuple of (is_valid, computed_rate, error_message)
        - is_valid: True if rate is within limit, False otherwise
        - computed_rate: The computed pings per second rate
        - error_message: Error message if invalid, empty string if valid
    """
    if host_count <= 0 or interval <= 0:
        return False, 0.0, "Invalid parameters: host_count and interval must be positive"

    # Calculate max pings per second: host_count / interval
    # Each host sends 1 ping every 'interval' seconds
    # With N hosts, we send N pings every 'interval' seconds
    # So pings/sec = N / interval
    computed_rate = host_count / interval

    if computed_rate > MAX_GLOBAL_PINGS_PER_SECOND:
        error_msg = (
            f"Error: Global rate limit exceeded.\n"
            f"  Requested rate: {computed_rate:.2f} pings/sec "
            f"({host_count} hosts at {interval}s interval)\n"
            f"  Maximum allowed: {MAX_GLOBAL_PINGS_PER_SECOND} pings/sec\n"
            f"  To fix: Reduce host count or increase interval.\n"
            f"  Examples:\n"
            f"    - Use interval >= {host_count / MAX_GLOBAL_PINGS_PER_SECOND:.2f}s with {host_count} hosts\n"
            f"    - Use <= {int(MAX_GLOBAL_PINGS_PER_SECOND * interval)} hosts with {interval}s interval"
        )
        return False, computed_rate, error_msg

    return True, computed_rate, ""
