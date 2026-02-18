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
Command-line interface for ParaPing.

This module contains the main entry point and command-line argument handling.
"""

import argparse
import os
import queue
import sys
import termios
import threading
import time
import tty
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from paraping.core import (
    HISTORY_DURATION_MINUTES,
    MAX_HOST_THREADS,
    SNAPSHOT_INTERVAL_SECONDS,
    _normalize_term_size,
    build_host_infos,
    get_cached_page_step,
    read_input_file,
    resolve_render_state,
    update_history_buffer,
    validate_global_rate_limit,
)
from paraping.input_keys import read_key
from paraping.network_asn import asn_worker, should_retry_asn
from paraping.pinger import rdns_worker, scheduler_driven_worker_ping
from paraping.scheduler import Scheduler
from paraping.sequence_tracker import SequenceTracker
from paraping.ui_render import (
    build_display_entries,
    build_display_lines,
    build_display_names,
    compute_host_scroll_bounds,
    compute_main_layout,
    compute_panel_sizes,
    cycle_panel_position,
    flash_screen,
    format_timestamp,
    get_terminal_size,
    prepare_terminal_for_exit,
    render_display,
    render_fullscreen_rtt_graph,
    render_help_view,
    render_host_selection_view,
    ring_bell,
    should_flash_on_fail,
    should_show_asn,
    toggle_panel_visibility,
)


def _compute_initial_timeline_width(host_labels, term_size, panel_position):
    """
    Compute the initial timeline width for buffer sizing.

    Always uses header_lines=2 to ensure consistent layout sizing at startup.

    Args:
        host_labels: List of host labels to size the label column.
        term_size: Terminal size object with columns/lines attributes.
        panel_position: Current summary panel position selection.

    Returns:
        Positive integer timeline width for buffer maxlen sizing.
    """
    # Normalize term_size defensively
    normalized_size = _normalize_term_size(term_size)
    if normalized_size is None:
        # Fallback to reasonable default timeline width
        # Typical 80-column terminal minus label area (~20 chars) = ~60
        return 60

    status_box_height = 3 if normalized_size.lines >= 4 and normalized_size.columns >= 2 else 1
    panel_height = max(1, normalized_size.lines - status_box_height)
    main_width, main_height, _, _, _ = compute_panel_sizes(normalized_size.columns, panel_height, panel_position)
    # Always use header_lines=2 for consistent initial sizing
    _, _, timeline_width, _ = compute_main_layout(host_labels, main_width, main_height, header_lines=2)
    try:
        return max(1, int(timeline_width))
    except (TypeError, ValueError):
        return 1


def handle_options():
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(
        description="ParaPing - Perform ICMP ping operations to multiple hosts concurrently",
        epilog="Note: ParaPing enforces a global rate limit of 50 pings/sec for flood protection. "
        "The tool will exit with an error if (host_count / interval) > 50.",
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
        help="Interval in seconds between pings per host (default: 1.0, range: 0.1-60.0). "
        "Note: Global rate limit is 50 pings/sec (host_count / interval <= 50)",
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
    parser.add_argument("hosts", nargs="*", help="Hosts to ping (IP addresses or hostnames)")

    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be a positive integer.")
    if not 0.1 <= args.interval <= 60.0:
        parser.error("--interval must be between 0.1 and 60.0 seconds.")
    return args


def run(args):
    """Run the ParaPing monitor with parsed arguments."""
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
        print("Error: No hosts specified. Provide hosts as arguments or use -f/--input option.")
        return
    if len(all_hosts) > MAX_HOST_THREADS:
        print(
            "Error: Host count exceeds maximum supported threads "
            f"({len(all_hosts)} > {MAX_HOST_THREADS}). Reduce the host list."
        )
        return

    # Validate global rate limit before starting
    is_valid, _computed_rate, error_message = validate_global_rate_limit(len(all_hosts), args.interval)
    if not is_valid:
        print(error_message, file=sys.stderr)
        sys.exit(1)

    display_tz = timezone.utc
    if args.timezone:
        try:
            display_tz = ZoneInfo(args.timezone)
        except ZoneInfoNotFoundError:
            print(f"Error: Unknown timezone '{args.timezone}'. Use an IANA name like 'Asia/Tokyo'.")
            return
    snapshot_tz = display_tz if args.snapshot_timezone == "display" else timezone.utc
    ping_helper_path = os.path.expanduser(args.ping_helper)
    panel_position = args.panel_position
    panel_toggle_default = args.panel_position if args.panel_position != "none" else "right"
    last_panel_position = panel_position if panel_position != "none" else None

    symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}
    initial_term_size = get_terminal_size(fallback=(80, 24))
    host_infos, host_info_map = build_host_infos(all_hosts)
    host_labels = [info["alias"] for info in host_infos]
    timeline_width = _compute_initial_timeline_width(host_labels, initial_term_size, panel_position)
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

    count_label = "infinite" if args.count == 0 else str(args.count)
    print(
        f"ParaPing - Pinging {len(all_hosts)} host(s) with timeout={args.timeout}s, "
        f"count={count_label}, interval={args.interval}s, slow-threshold={args.slow_threshold}s"
    )

    modes = ["ip", "rdns", "alias"]
    mode_index = 2
    show_help = False
    display_modes = ["timeline", "sparkline", "square"]
    display_mode_index = 0
    summary_modes = ["rates", "rtt", "ttl", "streak"]
    summary_mode_index = 0
    summary_fullscreen = False
    sort_modes = ["config", "failures", "streak", "latency", "host"]
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
    host_select_active = False
    host_select_index = 0
    graph_host_id = None

    # History navigation state
    # Store snapshots at regular intervals for time navigation
    max_history_snapshots = int(HISTORY_DURATION_MINUTES * 60 / SNAPSHOT_INTERVAL_SECONDS)
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

    # Initialize scheduler for real-time event-driven pinging
    num_hosts = len(host_infos)
    stagger = args.interval / num_hosts if num_hosts > 0 else 0.0
    scheduler = Scheduler(interval=args.interval, stagger=stagger)
    ping_lock = threading.Lock()

    # Initialize shared sequence tracker for per-host ICMP sequence management
    # with max 3 outstanding pings per host
    sequence_tracker = SequenceTracker(max_outstanding=3)

    # Add all hosts to the scheduler
    for info in host_infos:
        scheduler.add_host(info["host"], host_id=info["id"])

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

        # Use scheduler-driven worker instead of traditional worker_ping
        for info in host_infos:
            executor.submit(
                scheduler_driven_worker_ping,
                info,
                scheduler,
                args.timeout,
                args.count,
                args.slow_threshold,
                pause_event,
                stop_event,
                result_queue,
                ping_helper_path,
                ping_lock,
                sequence_tracker,
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
                        display_names = build_display_names(host_infos, modes[mode_index], include_asn, asn_width=8)
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
                            host_select_index = min(max(host_select_index, 0), len(display_entries) - 1)
                        if key in ("p", "P") and display_entries:
                            # 'p' moves up (previous)
                            host_select_index = max(0, host_select_index - 1)
                            force_render = True
                            updated = True
                        elif key in ("n", "N") and display_entries:
                            # 'n' moves down (next)
                            host_select_index = min(len(display_entries) - 1, host_select_index + 1)
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
                        display_mode_index = (display_mode_index + 1) % len(display_modes)
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
                        summary_mode_index = (summary_mode_index + 1) % len(summary_modes)
                        status_message = f"Summary: {summary_modes[summary_mode_index].upper()}"
                        updated = True
                    elif key == "c":
                        if not color_supported:
                            status_message = "Color output unavailable (no TTY)"
                        else:
                            use_color = not use_color
                            status_message = "Color output enabled" if use_color else "Color output disabled"
                        force_render = True
                        updated = True
                    elif key == "b":
                        bell_on_fail = not bell_on_fail
                        status_message = "Bell on fail enabled" if bell_on_fail else "Bell on fail disabled"
                        force_render = True
                        updated = True
                    elif key == "F":
                        summary_fullscreen = not summary_fullscreen
                        status_message = (
                            "Summary fullscreen view enabled" if summary_fullscreen else "Summary fullscreen view disabled"
                        )
                        force_render = True
                        updated = True
                    elif key == "w":
                        panel_position, last_panel_position = toggle_panel_visibility(
                            panel_position,
                            last_panel_position,
                            default_position=panel_toggle_default,
                        )
                        status_message = "Summary panel hidden" if panel_position == "none" else "Summary panel shown"
                        cached_page_step = None  # Invalidate cache - panel visibility changed
                        force_render = True
                        updated = True
                    elif key == "W":
                        reference_position = (
                            panel_position if panel_position != "none" else last_panel_position or panel_toggle_default
                        )
                        panel_position = cycle_panel_position(reference_position, default_position=panel_toggle_default)
                        last_panel_position = panel_position
                        status_message = f"Summary panel position: {panel_position.upper()}"
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
                        snapshot_name = snapshot_dt.strftime("paraping_snapshot_%Y%m%d_%H%M%S.txt")
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
                            interval_seconds=args.interval,
                        )
                        with open(snapshot_name, "w", encoding="utf-8") as snapshot_file:
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
                        if 0 < history_offset <= len(history_buffer):
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
                            end_index = min(host_scroll_offset + visible_hosts, total_hosts)
                            status_message = f"Hosts {host_scroll_offset + 1}-{end_index} " f"of {total_hosts}"
                            force_render = True
                            updated = True
                    elif key == "arrow_down":
                        scroll_buffers = buffers
                        scroll_stats = stats
                        if 0 < history_offset <= len(history_buffer):
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
                            end_index = min(host_scroll_offset + visible_hosts, total_hosts)
                            status_message = f"Hosts {host_scroll_offset + 1}-{end_index} " f"of {total_hosts}"
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
                    host_buf = buffers[host_id]

                    # Handle 'sent' pending event: append a pending slot so timelines stay aligned
                    if status == "sent":
                        host_buf["timeline"].append(symbols["pending"])
                        host_buf["rtt_history"].append(None)
                        host_buf["time_history"].append(result.get("sent_time", time.time()))
                        host_buf["ttl_history"].append(None)
                        host_buf["categories"]["pending"].append(result["sequence"])
                        # Do not update stats yet
                        if not paused:
                            updated = True
                        continue

                    # For final statuses (success/slow/fail), prefer to finalize the last pending slot when possible
                    try:
                        last_symbol = host_buf["timeline"][-1]
                    except IndexError:
                        last_symbol = None

                    if last_symbol == symbols.get("pending"):
                        # Overwrite the pending slot with final symbol
                        host_buf["timeline"][-1] = symbols[status]
                        host_buf["rtt_history"][-1] = result.get("rtt")
                        host_buf["time_history"][-1] = time.time()
                        host_buf["ttl_history"][-1] = result.get("ttl")
                        # Move sequence from pending category to concrete status category if possible
                        try:
                            buffers[host_id]["categories"]["pending"].pop()
                        except IndexError:
                            pass
                        host_buf["categories"][status].append(result["sequence"])
                    else:
                        # No pending slot to finalize — append as before
                        host_buf["timeline"].append(symbols[status])
                        host_buf["rtt_history"].append(result.get("rtt"))
                        host_buf["time_history"].append(time.time())
                        host_buf["ttl_history"].append(result.get("ttl"))
                        host_buf["categories"][status].append(result["sequence"])

                    # Update stats for final statuses
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

                if force_render or (not paused and (updated or (now - last_render) >= refresh_interval)):
                    display_timestamp = format_timestamp(datetime.now(timezone.utc), display_tz)
                    if 0 < history_offset <= len(history_buffer):
                        snapshot = history_buffer[-(history_offset + 1)]
                        snapshot_dt = datetime.fromtimestamp(snapshot["timestamp"], timezone.utc)
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
                    host_scroll_offset = min(host_scroll_offset, max_offset)
                    override_lines = None
                    term_size = get_terminal_size(fallback=(80, 24))
                    if show_help:
                        override_lines = render_help_view(term_size.columns, term_size.lines)
                    elif host_select_active:
                        include_asn = should_show_asn(
                            host_infos,
                            modes[mode_index],
                            show_asn,
                            term_size.columns,
                        )
                        display_names = build_display_names(host_infos, modes[mode_index], include_asn, asn_width=8)
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
                        display_names = build_display_names(host_infos, modes[mode_index], include_asn, asn_width=8)
                        host_label = display_names.get(graph_host_id, host_infos[graph_host_id]["alias"])
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
                        interval_seconds=args.interval,
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
        print(f"{info['alias']:30} {success}/{total} replies, {slow} slow, {fail} failed " f"({percentage:.1f}%) [{status}]")


def main():
    """Main entrypoint for the CLI - parses arguments and runs the application."""
    args = handle_options()
    run(args)
