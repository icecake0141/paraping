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
ParaPing - Interactive terminal-based ICMP ping monitor.

This module provides an interactive, terminal-based ICMP monitor that pings multiple
hosts concurrently and visualizes results as a live timeline or sparkline. It includes
useful operator controls like sorting, filtering, pause modes, snapshots, and optional
ASN/rDNS display for fast network triage.

Features:
- Concurrent ICMP ping to multiple hosts using a capability-based helper binary
- Live timeline or sparkline visualization with success/slow/fail markers
- Real-time statistics and aggregate counts with TTL display
- Sort and filter results by failures, streaks, latency, or host name
- Toggle display name mode: IP, reverse DNS, or alias
- Optional ASN display (fetched from Team Cymru)
- Configurable timezone for timestamps and snapshot naming
- History navigation to review past ping results
- Pause modes and snapshot export functionality
"""

import argparse
import copy
import ipaddress
import math
import os
import queue
import re
import select
import socket
import sys
import termios
import threading
import time
import tty
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ping_wrapper import ping_with_helper
from network_asn import resolve_asn, asn_worker, should_retry_asn
from input_keys import parse_escape_sequence, read_key
from stats import (
    compute_fail_streak,
    latest_ttl_value,
    latest_rtt_value,
    build_streak_label,
    build_summary_suffix,
    build_summary_all_suffix,
    compute_summary_data,
)
from ui_render import (
    strip_ansi,
    visible_len,
    truncate_visible,
    pad_visible,
    rjust_visible,
    colorize_text,
    status_from_symbol,
    latest_status_from_timeline,
    build_colored_timeline,
    build_colored_sparkline,
    build_activity_indicator,
    compute_activity_indicator_width,
    get_terminal_size,
    compute_main_layout,
    compute_panel_sizes,
    resolve_boxed_dimensions,
    compute_host_scroll_bounds,
    pad_lines,
    box_lines,
    resize_buffers,
    build_sparkline,
    build_ascii_graph,
    resample_values,
    can_render_full_summary,
    format_summary_line,
    format_status_line,
    build_status_line,
    build_display_entries,
    render_timeline_view,
    render_sparkline_view,
    render_main_view,
    render_summary_view,
    render_help_view,
    render_host_selection_view,
    render_fullscreen_rtt_graph,
    render_status_box,
    build_display_lines,
    render_display,
    format_timezone_label,
    format_timestamp,
    prepare_terminal_for_exit,
    flash_screen,
    ring_bell,
    should_flash_on_fail,
    toggle_panel_visibility,
    cycle_panel_position,
    should_show_asn,
    resolve_display_name,
    format_asn_label,
    format_display_name,
    build_display_names,
)


# Constants for time navigation feature
HISTORY_DURATION_MINUTES = 30  # Store up to 30 minutes of history
SNAPSHOT_INTERVAL_SECONDS = 1.0  # Take snapshot every second
MAX_HOST_THREADS = 128  # Hard cap to avoid unbounded thread growth.


def handle_options():

    parser = argparse.ArgumentParser(
        description="ParaPing - Perform ICMP ping operations to multiple hosts concurrently"
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=1,
        help="Timeout in seconds for each ping (default: 1)",
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=0,
        help="Number of ping attempts per host (default: 0 for infinite)",
    )
    parser.add_argument(
        "-s",
        "--slow-threshold",
        type=float,
        default=0.5,
        help="Threshold in seconds for slow ping (default: 0.5)",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=1.0,
        help="Interval in seconds between pings per host (default: 1.0, range: 0.1-60.0)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output, showing detailed ping results",
    )
    parser.add_argument(
        "-f",
        "--input",
        type=str,
        help="Input file containing list of hosts (one per line, format: IP,alias)",
        required=False,
    )
    parser.add_argument(
        "-P",
        "--panel-position",
        type=str,
        default="right",
        choices=["right", "left", "top", "bottom", "none"],
        help="Summary panel position (right|left|top|bottom|none)",
    )
    parser.add_argument(
        "-m",
        "--pause-mode",
        type=str,
        default="display",
        choices=["display", "ping"],
        help="Pause behavior: display (stop updates only) or ping (pause ping + updates)",
    )
    parser.add_argument(
        "-z",
        "--timezone",
        type=str,
        default=None,
        help="Display timezone (IANA name, e.g. Asia/Tokyo). Defaults to UTC.",
    )
    parser.add_argument(
        "-Z",
        "--snapshot-timezone",
        type=str,
        default="utc",
        choices=["utc", "display"],
        help="Timezone used in snapshot filename (utc|display). Defaults to utc.",
    )
    parser.add_argument(
        "-F",
        "--flash-on-fail",
        action="store_true",
        help="Flash screen (white background) when ping fails",
    )
    parser.add_argument(
        "-B",
        "--bell-on-fail",
        action="store_true",
        help="Ring terminal bell when ping fails",
    )
    parser.add_argument(
        "-C",
        "--color",
        action="store_true",
        help="Enable colored output (blue=success, yellow=slow, red=fail)",
    )
    parser.add_argument(
        "-H",
        "--ping-helper",
        type=str,
        default="./ping_helper",
        help="Path to ping_helper binary (default: ./ping_helper)",
    )
    parser.add_argument(
        "hosts", nargs="*", help="Hosts to ping (IP addresses or hostnames)"
    )

    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be a positive integer.")
    if not 0.1 <= args.interval <= 60.0:
        parser.error("--interval must be between 0.1 and 60.0 seconds.")
    return args


# Read input file. The file contains a list of hosts (IP addresses and aliases)


def parse_host_file_line(line, line_number, input_file):
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = [part.strip() for part in stripped.split(",")]
    if len(parts) != 2:
        print(
            f"Warning: Invalid host entry at {input_file}:{line_number}. "
            "Expected format 'IP,alias'.",
            file=sys.stderr,
        )
        return None
    ip_text, alias = parts
    if not ip_text or not alias:
        print(
            f"Warning: Invalid host entry at {input_file}:{line_number}. "
            "IP address and alias are required.",
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
            f"Warning: Unsupported IP version at {input_file}:{line_number}: '{ip_text}'.",
            file=sys.stderr,
        )
        return None
    return {"host": ip_text, "alias": alias, "ip": ip_text}


def read_input_file(input_file):
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
    except Exception as e:
        print(f"Error reading input file '{input_file}': {e}")
        return []

    return host_list


# Ping a single host


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
        message = (
            f"ping_helper binary not found at {helper_path}. "
            "Please run 'make build' and 'sudo make setcap'."
        )
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
            rtt_ms, ttl = ping_with_helper(
                host, timeout_ms=int(timeout * 1000), helper_path=helper_path
            )
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


def compute_history_page_step(
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
    asn_width=8,
    header_lines=2,
):
    term_size = get_terminal_size(fallback=(80, 24))
    term_width = term_size.columns
    term_height = term_size.lines
    status_box_height = 3 if term_height >= 4 and term_width >= 2 else 1
    panel_height = max(1, term_height - status_box_height)

    include_asn = should_show_asn(
        host_infos, mode_label, show_asn, term_width, asn_width=asn_width
    )
    display_names = build_display_names(host_infos, mode_label, include_asn, asn_width)
    main_width, main_height, _, _, _ = compute_panel_sizes(
        term_width, panel_height, panel_position
    )
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
    _, _, timeline_width, _ = compute_main_layout(
        host_labels, main_width, main_height, header_lines
    )
    return max(1, timeline_width)


def get_cached_page_step(
    cached_page_step,
    last_term_size,
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
):
    """
    Get the page step for history navigation, using cached value if available.

    The page step is only recalculated if the terminal size has changed.
    This prevents expensive recalculation on every arrow key press.

    Returns:
        tuple: (page_step, new_cached_page_step, new_last_term_size)
    """
    def should_recalculate_page_step(cached_value, last_size, current_size):
        """Check if page step needs recalculation due to cache miss or terminal resize"""
        if cached_value is None or last_size is None:
            return True  # First time - need to calculate
        if current_size.columns != last_size.columns:
            return True  # Terminal width changed
        if current_size.lines != last_size.lines:
            return True  # Terminal height changed
        return False

    current_term_size = get_terminal_size(fallback=(80, 24))

    # Check if we need to recalculate
    if should_recalculate_page_step(cached_page_step, last_term_size, current_term_size):
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


def build_host_infos(hosts):
    host_infos = []
    host_map = {}
    for index, entry in enumerate(hosts):
        if isinstance(entry, str):
            host = entry
            alias = entry
            ip_address = None
        else:
            host = entry.get("host") or entry.get("ip")
            alias = entry.get("alias") or host
            ip_address = entry.get("ip")
        if not ip_address:
            try:
                ip_address = socket.gethostbyname(host)
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


def resolve_rdns(ip_address):
    try:
        return socket.gethostbyaddr(ip_address)[0]
    except (socket.herror, socket.gaierror, OSError):
        return None


def rdns_worker(request_queue, result_queue, stop_event):
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


def create_state_snapshot(buffers, stats, timestamp):
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
            "timeline": deque(
                host_buffers["timeline"],
                maxlen=host_buffers["timeline"].maxlen
            ),
            "rtt_history": deque(
                host_buffers["rtt_history"],
                maxlen=host_buffers["rtt_history"].maxlen
            ),
            "time_history": deque(
                host_buffers["time_history"],
                maxlen=host_buffers["time_history"].maxlen
            ),
            "ttl_history": deque(
                host_buffers["ttl_history"],
                maxlen=host_buffers["ttl_history"].maxlen
            ),
            "categories": {
                status: deque(cat_deque, maxlen=cat_deque.maxlen)
                for status, cat_deque in host_buffers["categories"].items()
            }
        }

    # Deep copy stats
    stats_copy = copy.deepcopy(stats)

    return {
        "timestamp": timestamp,
        "buffers": buffers_copy,
        "stats": stats_copy,
    }


def update_history_buffer(
    history_buffer,
    buffers,
    stats,
    now,
    last_snapshot_time,
    history_offset,
):
    if (now - last_snapshot_time) < SNAPSHOT_INTERVAL_SECONDS:
        return last_snapshot_time, history_offset

    snapshot = create_state_snapshot(buffers, stats, now)
    history_buffer.append(snapshot)
    last_snapshot_time = now
    if history_offset > 0:
        history_offset = min(history_offset + 1, len(history_buffer) - 1)
    return last_snapshot_time, history_offset


def resolve_render_state(history_offset, history_buffer, buffers, stats, paused):
    if history_offset > 0 and history_offset <= len(history_buffer):
        snapshot = history_buffer[-(history_offset + 1)]
        return snapshot["buffers"], snapshot["stats"], True
    return buffers, stats, paused


def main(args):

    # Validate count parameter - allow 0 for infinite
    if args.count < 0:
        print("Error: Count must be a non-negative number (0 for infinite).")
        return
    if args.timeout <= 0:
        print("Error: Timeout must be a positive number of seconds.")
        return

    # Validate interval parameter
    if args.interval < 0.1 or args.interval > 60.0:
        print("Error: Interval must be between 0.1 and 60.0 seconds.")
        return

    # Collect all hosts to ping
    all_hosts = []

    # Add hosts from command line arguments
    if args.hosts:
        all_hosts.extend({"host": host, "alias": host} for host in args.hosts)

    # Add hosts from input file if provided
    if args.input:
        file_hosts = read_input_file(args.input)
        all_hosts.extend(file_hosts)

    # Check if we have any hosts to ping
    if not all_hosts:
        print(
            "Error: No hosts specified. Provide hosts as arguments or use -f/--input option."
        )
        return
    if len(all_hosts) > MAX_HOST_THREADS:
        print(
            "Error: Host count exceeds maximum supported threads "
            f"({len(all_hosts)} > {MAX_HOST_THREADS}). Reduce the host list."
        )
        return

    display_tz = timezone.utc
    if args.timezone:
        try:
            display_tz = ZoneInfo(args.timezone)
        except ZoneInfoNotFoundError:
            print(
                f"Error: Unknown timezone '{args.timezone}'. Use an IANA name like 'Asia/Tokyo'."
            )
            return
    snapshot_tz = display_tz if args.snapshot_timezone == "display" else timezone.utc

    symbols = {"success": ".", "fail": "x", "slow": "!"}
    term_size = get_terminal_size(fallback=(80, 24))
    host_infos, host_info_map = build_host_infos(all_hosts)
    host_labels = [info["alias"] for info in host_infos]
    _, _, timeline_width, _ = compute_main_layout(
        host_labels, term_size.columns, term_size.lines
    )
    buffers = {
        info["id"]: {
            "timeline": deque(maxlen=timeline_width),
            "rtt_history": deque(maxlen=timeline_width),
            "time_history": deque(maxlen=timeline_width),
            "ttl_history": deque(maxlen=timeline_width),
            "categories": {status: deque(maxlen=timeline_width) for status in symbols},
        }
        for info in host_infos
    }
    stats = {
        info["id"]: {
            "success": 0,
            "fail": 0,
            "slow": 0,
            "total": 0,
            "rtt_sum": 0.0,
            "rtt_sum_sq": 0.0,
            "rtt_count": 0,
        }
        for info in host_infos
    }
    result_queue = queue.Queue()

    count_display = "infinite" if args.count == 0 else str(args.count)
    print(
        f"ParaPing - Pinging {len(all_hosts)} host(s) with timeout={args.timeout}s, "
        f"count={count_display}, interval={args.interval}s, slow-threshold={args.slow_threshold}s"
    )

    modes = ["ip", "rdns", "alias"]
    mode_index = 0
    show_help = False
    display_modes = ["timeline", "sparkline"]
    display_mode_index = 0
    summary_modes = ["rates", "rtt", "ttl", "streak"]
    summary_mode_index = 0
    summary_fullscreen = False
    sort_modes = ["failures", "streak", "latency", "host"]
    sort_mode_index = 0
    filter_modes = ["failures", "latency", "all"]
    filter_mode_index = 2
    running = True
    paused = False
    pause_mode = args.pause_mode
    pause_event = threading.Event()
    stop_event = threading.Event()
    status_message = None
    force_render = False
    show_asn = True
    color_supported = sys.stdout.isatty()
    use_color = args.color and color_supported
    flash_on_fail = getattr(args, "flash_on_fail", False)
    bell_on_fail = getattr(args, "bell_on_fail", False)
    asn_cache = {}
    asn_timeout = 3.0
    asn_failure_ttl = 300.0
    panel_position = args.panel_position
    panel_toggle_default = args.panel_position if args.panel_position != "none" else "right"
    last_panel_position = panel_position if panel_position != "none" else None
    host_select_active = False
    host_select_index = 0
    graph_host_id = None

    # History navigation state
    # Store snapshots at regular intervals for time navigation
    max_history_snapshots = int(
        HISTORY_DURATION_MINUTES * 60 / SNAPSHOT_INTERVAL_SECONDS
    )
    history_buffer = deque(maxlen=max_history_snapshots)
    history_offset = 0  # 0 = live, >0 = viewing history
    last_snapshot_time = 0.0
    # Cache page step to avoid expensive recalculation on every arrow key press
    cached_page_step = None
    last_term_size = None
    host_scroll_offset = 0

    rdns_request_queue = queue.Queue()
    rdns_result_queue = queue.Queue()
    asn_request_queue = queue.Queue()
    asn_result_queue = queue.Queue()
    worker_stop = threading.Event()
    rdns_thread = threading.Thread(
        target=rdns_worker,
        args=(rdns_request_queue, rdns_result_queue, worker_stop),
        daemon=True,
    )
    asn_thread = threading.Thread(
        target=asn_worker,
        args=(asn_request_queue, asn_result_queue, worker_stop, asn_timeout),
        daemon=True,
    )
    rdns_thread.start()
    asn_thread.start()

    stdin_fd = None
    original_term = None
    if sys.stdin.isatty():
        stdin_fd = sys.stdin.fileno()
        original_term = termios.tcgetattr(stdin_fd)

    with ThreadPoolExecutor(max_workers=len(all_hosts)) as executor:
        for host, infos in host_info_map.items():
            info = infos[0]
            for entry in infos:
                entry["rdns_pending"] = True
            rdns_request_queue.put((host, info["ip"]))
            now = time.time()
            if info["ip"] in asn_cache and asn_cache[info["ip"]]["value"] is not None:
                cached_asn = asn_cache[info["ip"]]["value"]
                for entry in infos:
                    entry["asn"] = cached_asn
                    entry["asn_pending"] = False
            elif should_retry_asn(info["ip"], asn_cache, now, asn_failure_ttl):
                for entry in infos:
                    entry["asn_pending"] = True
                asn_request_queue.put((host, info["ip"]))
        for info in host_infos:
            executor.submit(
                worker_ping,
                info,
                args.timeout,
                args.count,
                args.slow_threshold,
                args.verbose,
                pause_event,
                stop_event,
                result_queue,
                args.interval,
                args.ping_helper,
            )

        completed_hosts = 0
        updated = True
        last_render = 0.0
        refresh_interval = 0.15
        # When count is 0 (infinite), workers never complete, so we wait for user to quit
        expect_completion = args.count > 0
        try:
            if stdin_fd is not None:
                tty.setcbreak(stdin_fd)
            while running and (not expect_completion or completed_hosts < len(host_infos)):
                key = read_key()
                if key:
                    if key in ("q", "Q"):
                        running = False
                        stop_event.set()
                    elif show_help:
                        show_help = False
                        force_render = True
                        updated = True
                        continue
                    elif host_select_active:
                        render_buffers, render_stats, _ = resolve_render_state(
                            history_offset,
                            history_buffer,
                            buffers,
                            stats,
                            paused,
                        )
                        term_size = get_terminal_size(fallback=(80, 24))
                        include_asn = should_show_asn(
                            host_infos,
                            modes[mode_index],
                            show_asn,
                            term_size.columns,
                        )
                        display_names = build_display_names(
                            host_infos, modes[mode_index], include_asn, asn_width=8
                        )
                        display_entries = build_display_entries(
                            host_infos,
                            display_names,
                            render_buffers,
                            render_stats,
                            symbols,
                            sort_modes[sort_mode_index],
                            filter_modes[filter_mode_index],
                            args.slow_threshold,
                        )
                        if not display_entries:
                            host_select_index = 0
                        else:
                            host_select_index = min(
                                max(host_select_index, 0), len(display_entries) - 1
                            )
                        if key in ("p", "P") and display_entries:
                            # 'p' moves up (previous)
                            host_select_index = max(0, host_select_index - 1)
                            force_render = True
                            updated = True
                        elif key in ("n", "N") and display_entries:
                            # 'n' moves down (next)
                            host_select_index = min(
                                len(display_entries) - 1, host_select_index + 1
                            )
                            force_render = True
                            updated = True
                        elif key in ("\r", "\n"):
                            if display_entries:
                                graph_host_id = display_entries[host_select_index][0]
                                host_select_active = False
                                force_render = True
                                updated = True
                        elif key == "\x1b":
                            # ESC exits host selection
                            host_select_active = False
                            force_render = True
                            updated = True
                        # All host selection keys are handled above.
                        # The 'continue' statement below ensures we don't fall through
                        # to the main key handlers (e.g., 'n' for mode cycling).
                        continue
                    elif graph_host_id is not None:
                        if key == "\x1b":
                            graph_host_id = None
                            force_render = True
                            updated = True
                            continue
                        if key in ("g", "G"):
                            host_select_active = True
                            graph_host_id = None
                            force_render = True
                            updated = True
                            continue
                    elif key in ("H", "h"):
                        show_help = True
                        force_render = True
                        updated = True
                    elif key == "n":
                        mode_index = (mode_index + 1) % len(modes)
                        cached_page_step = None  # Invalidate cache - display mode changed
                        updated = True
                    elif key == "v":
                        display_mode_index = (display_mode_index + 1) % len(
                            display_modes
                        )
                        updated = True
                    elif key == "o":
                        sort_mode_index = (sort_mode_index + 1) % len(sort_modes)
                        cached_page_step = None  # Invalidate cache - sort mode changed
                        updated = True
                    elif key == "f":
                        filter_mode_index = (filter_mode_index + 1) % len(filter_modes)
                        cached_page_step = None  # Invalidate cache - filter mode changed
                        updated = True
                    elif key == "a":
                        show_asn = not show_asn
                        cached_page_step = None  # Invalidate cache - ASN display toggled
                        updated = True
                    elif key == "m":
                        summary_mode_index = (summary_mode_index + 1) % len(
                            summary_modes
                        )
                        status_message = (
                            f"Summary: {summary_modes[summary_mode_index].upper()}"
                        )
                        updated = True
                    elif key == "c":
                        if not color_supported:
                            status_message = "Color output unavailable (no TTY)"
                        else:
                            use_color = not use_color
                            status_message = (
                                "Color output enabled"
                                if use_color
                                else "Color output disabled"
                            )
                        force_render = True
                        updated = True
                    elif key == "b":
                        bell_on_fail = not bell_on_fail
                        status_message = (
                            "Bell on fail enabled"
                            if bell_on_fail
                            else "Bell on fail disabled"
                        )
                        force_render = True
                        updated = True
                    elif key == "F":
                        summary_fullscreen = not summary_fullscreen
                        status_message = (
                            "Summary fullscreen view enabled"
                            if summary_fullscreen
                            else "Summary fullscreen view disabled"
                        )
                        force_render = True
                        updated = True
                    elif key == "w":
                        panel_position, last_panel_position = toggle_panel_visibility(
                            panel_position,
                            last_panel_position,
                            default_position=panel_toggle_default,
                        )
                        status_message = (
                            "Summary panel hidden"
                            if panel_position == "none"
                            else "Summary panel shown"
                        )
                        cached_page_step = None  # Invalidate cache - panel visibility changed
                        force_render = True
                        updated = True
                    elif key == "W":
                        reference_position = (
                            panel_position
                            if panel_position != "none"
                            else last_panel_position or panel_toggle_default
                        )
                        panel_position = cycle_panel_position(
                            reference_position, default_position=panel_toggle_default
                        )
                        last_panel_position = panel_position
                        status_message = (
                            f"Summary panel position: {panel_position.upper()}"
                        )
                        cached_page_step = None  # Invalidate cache - panel position changed
                        force_render = True
                        updated = True
                    elif key == "p":
                        paused = not paused
                        status_message = "Paused" if paused else "Resumed"
                        if pause_mode == "ping":
                            if paused:
                                pause_event.set()
                            else:
                                pause_event.clear()
                        force_render = True
                        updated = True
                    elif key == "s":
                        now_utc = datetime.now(timezone.utc)
                        snapshot_dt = now_utc.astimezone(snapshot_tz)
                        snapshot_name = snapshot_dt.strftime(
                            "paraping_snapshot_%Y%m%d_%H%M%S.txt"
                        )
                        snapshot_lines = build_display_lines(
                            host_infos,
                            buffers,
                            stats,
                            symbols,
                            panel_position,
                            modes[mode_index],
                            display_modes[display_mode_index],
                            summary_modes[summary_mode_index],
                            sort_modes[sort_mode_index],
                            filter_modes[filter_mode_index],
                            args.slow_threshold,
                            show_help,
                            show_asn,
                            paused,
                            status_message,
                            format_timestamp(now_utc, display_tz),
                            now_utc,
                            False,
                            host_scroll_offset,
                            summary_fullscreen,
                        )
                        with open(
                            snapshot_name, "w", encoding="utf-8"
                        ) as snapshot_file:
                            snapshot_file.write("\n".join(snapshot_lines) + "\n")
                        status_message = f"Saved: {snapshot_name}"
                        updated = True
                    elif key == "arrow_left":
                        # Go back in time (increase offset)
                        if history_offset < len(history_buffer) - 1:
                            page_step, cached_page_step, last_term_size = get_cached_page_step(
                                cached_page_step,
                                last_term_size,
                                host_infos,
                                buffers,
                                stats,
                                symbols,
                                panel_position,
                                modes[mode_index],
                                sort_modes[sort_mode_index],
                                filter_modes[filter_mode_index],
                                args.slow_threshold,
                                show_asn,
                            )
                            history_offset = min(
                                history_offset + page_step,
                                len(history_buffer) - 1,
                            )
                            force_render = True
                            updated = True
                            snapshot = history_buffer[-(history_offset + 1)]
                            elapsed_seconds = int(time.time() - snapshot["timestamp"])
                            status_message = f"Viewing {elapsed_seconds}s ago"
                    elif key == "arrow_right":
                        # Go forward in time (decrease offset, toward live)
                        if history_offset > 0:
                            page_step, cached_page_step, last_term_size = get_cached_page_step(
                                cached_page_step,
                                last_term_size,
                                host_infos,
                                buffers,
                                stats,
                                symbols,
                                panel_position,
                                modes[mode_index],
                                sort_modes[sort_mode_index],
                                filter_modes[filter_mode_index],
                                args.slow_threshold,
                                show_asn,
                            )
                            history_offset = max(0, history_offset - page_step)
                            force_render = True
                            updated = True
                            if history_offset == 0:
                                status_message = "Returned to LIVE view"
                            else:
                                snapshot = history_buffer[-(history_offset + 1)]
                                elapsed_seconds = int(time.time() - snapshot["timestamp"])
                                status_message = f"Viewing {elapsed_seconds}s ago"
                    elif key == "arrow_up":
                        scroll_buffers = buffers
                        scroll_stats = stats
                        if history_offset > 0 and history_offset <= len(history_buffer):
                            snapshot = history_buffer[-(history_offset + 1)]
                            scroll_buffers = snapshot["buffers"]
                            scroll_stats = snapshot["stats"]
                        max_offset, visible_hosts, total_hosts = compute_host_scroll_bounds(
                            host_infos,
                            scroll_buffers,
                            scroll_stats,
                            symbols,
                            panel_position,
                            modes[mode_index],
                            sort_modes[sort_mode_index],
                            filter_modes[filter_mode_index],
                            args.slow_threshold,
                            show_asn,
                        )
                        if host_scroll_offset > 0 and total_hosts > 0:
                            host_scroll_offset = max(0, host_scroll_offset - 1)
                            end_index = min(
                                host_scroll_offset + visible_hosts, total_hosts
                            )
                            status_message = (
                                f"Hosts {host_scroll_offset + 1}-{end_index} "
                                f"of {total_hosts}"
                            )
                            force_render = True
                            updated = True
                    elif key == "arrow_down":
                        scroll_buffers = buffers
                        scroll_stats = stats
                        if history_offset > 0 and history_offset <= len(history_buffer):
                            snapshot = history_buffer[-(history_offset + 1)]
                            scroll_buffers = snapshot["buffers"]
                            scroll_stats = snapshot["stats"]
                        max_offset, visible_hosts, total_hosts = compute_host_scroll_bounds(
                            host_infos,
                            scroll_buffers,
                            scroll_stats,
                            symbols,
                            panel_position,
                            modes[mode_index],
                            sort_modes[sort_mode_index],
                            filter_modes[filter_mode_index],
                            args.slow_threshold,
                            show_asn,
                        )
                        if host_scroll_offset < max_offset and total_hosts > 0:
                            host_scroll_offset = min(max_offset, host_scroll_offset + 1)
                            end_index = min(
                                host_scroll_offset + visible_hosts, total_hosts
                            )
                            status_message = (
                                f"Hosts {host_scroll_offset + 1}-{end_index} "
                                f"of {total_hosts}"
                            )
                            force_render = True
                            updated = True
                    elif key in ("g", "G"):
                        host_select_active = True
                        host_select_index = 0
                        force_render = True
                        updated = True

                while True:
                    try:
                        host, rdns_value = rdns_result_queue.get_nowait()
                    except queue.Empty:
                        break
                    for info in host_info_map.get(host, []):
                        info["rdns"] = rdns_value
                        info["rdns_pending"] = False
                    if not paused:
                        updated = True

                while True:
                    try:
                        host, asn_value = asn_result_queue.get_nowait()
                    except queue.Empty:
                        break
                    for info in host_info_map.get(host, []):
                        info["asn"] = asn_value
                        info["asn_pending"] = False
                    if host_info_map.get(host):
                        ip_address = host_info_map[host][0]["ip"]
                    else:
                        ip_address = host
                    asn_cache[ip_address] = {
                        "value": asn_value,
                        "fetched_at": time.time(),
                    }
                    if not paused:
                        updated = True

                now = time.time()
                for host, infos in host_info_map.items():
                    if any(info["asn_pending"] for info in infos):
                        continue
                    if any(info["asn"] is not None for info in infos):
                        continue
                    ip_address = infos[0]["ip"]
                    if should_retry_asn(ip_address, asn_cache, now, asn_failure_ttl):
                        for info in infos:
                            info["asn_pending"] = True
                        asn_request_queue.put((host, ip_address))

                while True:
                    try:
                        result = result_queue.get_nowait()
                    except queue.Empty:
                        break
                    host_id = result["host_id"]
                    if result.get("status") == "done":
                        completed_hosts += 1
                        continue

                    status = result["status"]
                    buffers[host_id]["timeline"].append(symbols[status])
                    buffers[host_id]["rtt_history"].append(result.get("rtt"))
                    buffers[host_id]["time_history"].append(time.time())
                    buffers[host_id]["ttl_history"].append(result.get("ttl"))
                    buffers[host_id]["categories"][status].append(result["sequence"])
                    stats[host_id][status] += 1
                    stats[host_id]["total"] += 1
                    if result.get("rtt") is not None:
                        stats[host_id]["rtt_sum"] += result["rtt"]
                        stats[host_id]["rtt_sum_sq"] += result["rtt"] ** 2
                        stats[host_id]["rtt_count"] += 1

                    # Trigger flash or bell on ping failure
                    if should_flash_on_fail(status, flash_on_fail, show_help):
                        flash_screen()
                    if status == "fail" and bell_on_fail and not show_help:
                        ring_bell()

                    if not paused:
                        updated = True

                now = time.time()

                # Periodically save snapshots for history navigation
                last_snapshot_time, history_offset = update_history_buffer(
                    history_buffer,
                    buffers,
                    stats,
                    now,
                    last_snapshot_time,
                    history_offset,
                )

                # Determine which buffers/stats to use for rendering
                render_buffers, render_stats, render_paused = resolve_render_state(
                    history_offset,
                    history_buffer,
                    buffers,
                    stats,
                    paused,
                )

                if force_render or (
                    not paused and (updated or (now - last_render) >= refresh_interval)
                ):
                    display_timestamp = format_timestamp(
                        datetime.now(timezone.utc), display_tz
                    )
                    if history_offset > 0 and history_offset <= len(history_buffer):
                        snapshot = history_buffer[-(history_offset + 1)]
                        snapshot_dt = datetime.fromtimestamp(
                            snapshot["timestamp"], timezone.utc
                        )
                        display_timestamp = format_timestamp(snapshot_dt, display_tz)
                    max_offset, _visible_hosts, _total_hosts = compute_host_scroll_bounds(
                        host_infos,
                        render_buffers,
                        render_stats,
                        symbols,
                        panel_position,
                        modes[mode_index],
                        sort_modes[sort_mode_index],
                        filter_modes[filter_mode_index],
                        args.slow_threshold,
                        show_asn,
                    )
                    if host_scroll_offset > max_offset:
                        host_scroll_offset = max_offset
                    override_lines = None
                    term_size = get_terminal_size(fallback=(80, 24))
                    if show_help:
                        override_lines = render_help_view(
                            term_size.columns, term_size.lines
                        )
                    elif host_select_active:
                        include_asn = should_show_asn(
                            host_infos,
                            modes[mode_index],
                            show_asn,
                            term_size.columns,
                        )
                        display_names = build_display_names(
                            host_infos, modes[mode_index], include_asn, asn_width=8
                        )
                        display_entries = build_display_entries(
                            host_infos,
                            display_names,
                            render_buffers,
                            render_stats,
                            symbols,
                            sort_modes[sort_mode_index],
                            filter_modes[filter_mode_index],
                            args.slow_threshold,
                        )
                        override_lines = render_host_selection_view(
                            display_entries,
                            host_select_index,
                            term_size.columns,
                            term_size.lines,
                            modes[mode_index],
                        )
                    elif graph_host_id is not None:
                        include_asn = should_show_asn(
                            host_infos,
                            modes[mode_index],
                            show_asn,
                            term_size.columns,
                        )
                        display_names = build_display_names(
                            host_infos, modes[mode_index], include_asn, asn_width=8
                        )
                        host_label = display_names.get(
                            graph_host_id, host_infos[graph_host_id]["alias"]
                        )
                        rtt_values = render_buffers[graph_host_id]["rtt_history"]
                        time_history = render_buffers[graph_host_id]["time_history"]
                        override_lines = render_fullscreen_rtt_graph(
                            host_label,
                            rtt_values,
                            time_history,
                            term_size.columns,
                            term_size.lines,
                            display_modes[display_mode_index],
                            render_paused,
                            display_timestamp,
                        )
                    render_display(
                        host_infos,
                        render_buffers,
                        render_stats,
                        symbols,
                        panel_position,
                        modes[mode_index],
                        display_modes[display_mode_index],
                        summary_modes[summary_mode_index],
                        sort_modes[sort_mode_index],
                        filter_modes[filter_mode_index],
                        args.slow_threshold,
                        show_help,
                        show_asn,
                        render_paused,
                        status_message,
                        display_tz,
                        use_color,
                        host_scroll_offset,
                        summary_fullscreen,
                        override_lines=override_lines,
                    )
                    last_render = now
                    updated = False
                    force_render = False

                time.sleep(0.05)
        except KeyboardInterrupt:
            running = False
            stop_event.set()
        finally:
            stop_event.set()
            worker_stop.set()
            rdns_request_queue.put(None)
            asn_request_queue.put(None)
            rdns_thread.join(timeout=1.0)
            asn_thread.join(timeout=1.0)
            if stdin_fd is not None and original_term is not None:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, original_term)

    prepare_terminal_for_exit()
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for info in host_infos:
        host_id = info["id"]
        success = stats[host_id]["success"]
        slow = stats[host_id]["slow"]
        fail = stats[host_id]["fail"]
        total = stats[host_id]["total"]
        percentage = (success / total * 100) if total > 0 else 0
        status = "OK" if success > 0 else "FAILED"
        print(
            f"{info['alias']:30} {success}/{total} replies, {slow} slow, {fail} failed "
            f"({percentage:.1f}%) [{status}]"
        )


if __name__ == "__main__":
    # Handle command line options
    options = handle_options()
    main(options)
