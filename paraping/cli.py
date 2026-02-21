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
import logging
import os
import queue
import sys
import termios
import threading
import time
import tty
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, tzinfo
from typing import Any, Dict, List, Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from paraping.config import load_config
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


def _compute_initial_timeline_width(host_labels: List[str], term_size: Any, panel_position: str) -> int:
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


def _configure_logging(log_level: str, log_file: Optional[str]) -> None:
    """Configure logging handlers for CLI execution."""
    handlers: List[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.insert(0, logging.FileHandler(os.path.expanduser(log_file), encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(message)s",
        handlers=handlers,
        force=True,
    )


# Hardcoded defaults for config-overridable fields.
# Applied after config merging for any field still set to None.
_HARDCODED_DEFAULTS: Dict[str, Any] = {
    "timeout": 1,
    "slow_threshold": 0.5,
    "interval": 1.0,
    "panel_position": "right",
    "pause_mode": "display",
    "snapshot_timezone": "utc",
    "ping_helper": "./bin/ping_helper",
    "log_level": "INFO",
    "flash_on_fail": False,
    "bell_on_fail": False,
    "color": False,
}


def _apply_config_to_args(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    """
    Overlay config file values onto a parsed argument namespace.

    Only fields that are still ``None`` (i.e. not explicitly set on the CLI)
    are updated.  Config-supplied ``hosts`` are applied only when the user has
    not provided any hosts on the CLI and has not used ``--input``/``-f``.

    Args:
        args: Namespace returned by ``argparse.ArgumentParser.parse_args()``.
        config: Dictionary of values loaded from the config file.
    """
    for key, value in config.items():
        if key == "hosts":
            if not getattr(args, "hosts", None) and not getattr(args, "input", None):
                args.hosts = value
        elif hasattr(args, key) and getattr(args, key) is None:
            setattr(args, key, value)


def handle_options() -> argparse.Namespace:
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
        default=None,
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
        default=None,
        help="Threshold in seconds for slow ping (default: 0.5)",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=None,
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
        "--log-level",
        type=str.upper,
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level for verbose and error output (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Optional log file path for persistent logging",
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
        default=None,
        choices=["right", "left", "top", "bottom", "none"],
        help="Summary panel position (right|left|top|bottom|none)",
    )
    parser.add_argument(
        "-m",
        "--pause-mode",
        type=str,
        default=None,
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
        default=None,
        choices=["utc", "display"],
        help="Timezone used in snapshot filename (utc|display). Defaults to utc.",
    )
    parser.add_argument(
        "-F",
        "--flash-on-fail",
        action="store_true",
        default=None,
        help="Flash screen (white background) when ping fails",
    )
    parser.add_argument(
        "-B",
        "--bell-on-fail",
        action="store_true",
        default=None,
        help="Ring terminal bell when ping fails",
    )
    parser.add_argument(
        "-C",
        "--color",
        action="store_true",
        default=None,
        help="Enable colored output (blue=success, yellow=slow, red=fail)",
    )
    parser.add_argument(
        "-H",
        "--ping-helper",
        type=str,
        default=None,
        help="Path to ping_helper binary (default: ./bin/ping_helper)",
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        default=False,
        help="Skip loading ~/.paraping.conf config file",
    )
    parser.add_argument("hosts", nargs="*", help="Hosts to ping (IP addresses or hostnames)")

    args = parser.parse_args()

    # Load and apply config file unless --no-config was given
    if not args.no_config:
        try:
            config = load_config()
            _apply_config_to_args(args, config)
        except (ValueError, ImportError) as exc:
            parser.error(str(exc))

    # Apply hardcoded defaults for any config-overridable field still at None
    for field, default in _HARDCODED_DEFAULTS.items():
        if getattr(args, field, None) is None:
            setattr(args, field, default)

    if args.timeout <= 0:
        parser.error("--timeout must be a positive integer.")
    if not 0.1 <= args.interval <= 60.0:
        parser.error("--interval must be between 0.1 and 60.0 seconds.")
    return args


def _setup_hosts_and_state(args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    """Parse host input and initialize host/runtime state required by the monitor loop."""
    if args.count < 0:
        print("Error: Count must be a non-negative number (0 for infinite).")
        return None
    if args.timeout <= 0:
        print("Error: Timeout must be a positive number of seconds.")
        return None
    if args.interval < 0.1 or args.interval > 60.0:
        print("Error: Interval must be between 0.1 and 60.0 seconds.")
        return None

    all_hosts: List[Union[str, Dict[str, str]]] = []
    if args.hosts:
        all_hosts.extend({"host": host, "alias": host} for host in args.hosts)
    if args.input:
        all_hosts.extend(read_input_file(args.input))
    if not all_hosts:
        print("Error: No hosts specified. Provide hosts as arguments or use -f/--input option.")
        return None
    if len(all_hosts) > MAX_HOST_THREADS:
        print(
            "Error: Host count exceeds maximum supported threads "
            f"({len(all_hosts)} > {MAX_HOST_THREADS}). Reduce the host list."
        )
        return None

    is_valid, _computed_rate, error_message = validate_global_rate_limit(len(all_hosts), args.interval)
    if not is_valid:
        print(error_message, file=sys.stderr)
        sys.exit(1)

    display_tz: tzinfo = timezone.utc
    if args.timezone:
        try:
            display_tz = ZoneInfo(args.timezone)
        except ZoneInfoNotFoundError:
            print(f"Error: Unknown timezone '{args.timezone}'. Use an IANA name like 'Asia/Tokyo'.")
            return None
    snapshot_tz: tzinfo = display_tz if args.snapshot_timezone == "display" else timezone.utc
    panel_position = args.panel_position
    symbols: Dict[str, str] = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}
    host_infos, host_info_map = build_host_infos(all_hosts)
    host_labels = [info["alias"] for info in host_infos]
    timeline_width = _compute_initial_timeline_width(host_labels, get_terminal_size(fallback=(80, 24)), panel_position)
    buffers: Dict[int, Dict[str, Any]] = {
        info["id"]: {
            "timeline": deque(maxlen=timeline_width),
            "rtt_history": deque(maxlen=timeline_width),
            "time_history": deque(maxlen=timeline_width),
            "ttl_history": deque(maxlen=timeline_width),
            "categories": {status: deque(maxlen=timeline_width) for status in symbols},
        }
        for info in host_infos
    }
    stats: Dict[int, Dict[str, Any]] = {
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
    return {
        "all_hosts": all_hosts,
        "display_tz": display_tz,
        "snapshot_tz": snapshot_tz,
        "ping_helper_path": os.path.expanduser(args.ping_helper),
        "panel_position": panel_position,
        "panel_toggle_default": panel_position if panel_position != "none" else "right",
        "last_panel_position": panel_position if panel_position != "none" else None,
        "symbols": symbols,
        "host_infos": host_infos,
        "host_info_map": host_info_map,
        "buffers": buffers,
        "stats": stats,
        "result_queue": queue.Queue(),
    }


def _handle_user_input(key: str, args: argparse.Namespace, state: Dict[str, Any]) -> bool:
    """Process one keyboard input event and return whether the loop should skip to next iteration."""
    skip_iteration = False
    if key in ("q", "Q"):
        state["running"] = False
        state["stop_event"].set()
    elif state["show_help"]:
        state["show_help"] = False
        state["force_render"] = True
        state["updated"] = True
        skip_iteration = True
    elif state["host_select_active"]:
        render_buffers, render_stats, _ = resolve_render_state(
            state["history_offset"],
            state["history_buffer"],
            state["buffers"],
            state["stats"],
            state["paused"],
        )
        term_size = get_terminal_size(fallback=(80, 24))
        include_asn = should_show_asn(
            state["host_infos"],
            state["modes"][state["mode_index"]],
            state["show_asn"],
            term_size.columns,
        )
        display_names = build_display_names(
            state["host_infos"],
            state["modes"][state["mode_index"]],
            include_asn,
            asn_width=8,
        )
        display_entries = build_display_entries(
            state["host_infos"],
            display_names,
            render_buffers,
            render_stats,
            state["symbols"],
            state["sort_modes"][state["sort_mode_index"]],
            state["filter_modes"][state["filter_mode_index"]],
            args.slow_threshold,
        )
        if not display_entries:
            state["host_select_index"] = 0
        else:
            state["host_select_index"] = min(max(state["host_select_index"], 0), len(display_entries) - 1)
        if key in ("p", "P") and display_entries:
            state["host_select_index"] = max(0, state["host_select_index"] - 1)
            state["force_render"] = True
            state["updated"] = True
        elif key in ("n", "N") and display_entries:
            state["host_select_index"] = min(len(display_entries) - 1, state["host_select_index"] + 1)
            state["force_render"] = True
            state["updated"] = True
        elif key in ("\r", "\n"):
            if display_entries:
                state["graph_host_id"] = display_entries[state["host_select_index"]][0]
                state["host_select_active"] = False
                state["force_render"] = True
                state["updated"] = True
        elif key == "\x1b":
            state["host_select_active"] = False
            state["force_render"] = True
            state["updated"] = True
        skip_iteration = True
    elif state["graph_host_id"] is not None:
        if key == "\x1b":
            state["graph_host_id"] = None
            state["force_render"] = True
            state["updated"] = True
            skip_iteration = True
        elif key in ("g", "G"):
            state["host_select_active"] = True
            state["graph_host_id"] = None
            state["force_render"] = True
            state["updated"] = True
            skip_iteration = True
    elif key in ("H", "h"):
        state["show_help"] = True
        state["force_render"] = True
        state["updated"] = True
    elif key == "n":
        state["mode_index"] = (state["mode_index"] + 1) % len(state["modes"])
        state["cached_page_step"] = None
        state["updated"] = True
    elif key == "v":
        state["display_mode_index"] = (state["display_mode_index"] + 1) % len(state["display_modes"])
        state["updated"] = True
    elif key == "o":
        state["sort_mode_index"] = (state["sort_mode_index"] + 1) % len(state["sort_modes"])
        state["cached_page_step"] = None
        state["updated"] = True
    elif key == "f":
        state["filter_mode_index"] = (state["filter_mode_index"] + 1) % len(state["filter_modes"])
        state["cached_page_step"] = None
        state["updated"] = True
    elif key == "a":
        state["show_asn"] = not state["show_asn"]
        state["cached_page_step"] = None
        state["updated"] = True
    elif key == "m":
        state["summary_mode_index"] = (state["summary_mode_index"] + 1) % len(state["summary_modes"])
        state["status_message"] = f"Summary: {state['summary_modes'][state['summary_mode_index']].upper()}"
        state["updated"] = True
    elif key == "c":
        if not state["color_supported"]:
            state["status_message"] = "Color output unavailable (no TTY)"
        else:
            state["use_color"] = not state["use_color"]
            state["status_message"] = "Color output enabled" if state["use_color"] else "Color output disabled"
        state["force_render"] = True
        state["updated"] = True
    elif key == "b":
        state["bell_on_fail"] = not state["bell_on_fail"]
        state["status_message"] = "Bell on fail enabled" if state["bell_on_fail"] else "Bell on fail disabled"
        state["force_render"] = True
        state["updated"] = True
    elif key == "F":
        state["summary_fullscreen"] = not state["summary_fullscreen"]
        state["status_message"] = (
            "Summary fullscreen view enabled" if state["summary_fullscreen"] else "Summary fullscreen view disabled"
        )
        state["force_render"] = True
        state["updated"] = True
    elif key == "w":
        state["panel_position"], state["last_panel_position"] = toggle_panel_visibility(
            state["panel_position"],
            state["last_panel_position"],
            default_position=state["panel_toggle_default"],
        )
        state["status_message"] = "Summary panel hidden" if state["panel_position"] == "none" else "Summary panel shown"
        state["cached_page_step"] = None
        state["force_render"] = True
        state["updated"] = True
    elif key == "W":
        reference_position = (
            state["panel_position"]
            if state["panel_position"] != "none"
            else state["last_panel_position"] or state["panel_toggle_default"]
        )
        state["panel_position"] = cycle_panel_position(reference_position, default_position=state["panel_toggle_default"])
        state["last_panel_position"] = state["panel_position"]
        state["status_message"] = f"Summary panel position: {state['panel_position'].upper()}"
        state["cached_page_step"] = None
        state["force_render"] = True
        state["updated"] = True
    elif key == "p":
        state["display_paused"] = not state["display_paused"]
        state["paused"] = state["display_paused"] or state["dormant"]
        if state["dormant"] or (state["pause_mode"] == "ping" and state["display_paused"]):
            state["pause_event"].set()
        else:
            state["pause_event"].clear()
        state["status_message"] = "Display paused" if state["display_paused"] else "Display resumed"
        state["force_render"] = True
        state["updated"] = True
    elif key == "P":
        state["dormant"] = not state["dormant"]
        state["paused"] = state["display_paused"] or state["dormant"]
        if state["dormant"] or (state["pause_mode"] == "ping" and state["display_paused"]):
            state["pause_event"].set()
        else:
            state["pause_event"].clear()
        state["status_message"] = "Dormant mode enabled" if state["dormant"] else "Dormant mode disabled"
        state["force_render"] = True
        state["updated"] = True
    elif key == "s":
        now_utc = datetime.now(timezone.utc)
        snapshot_name = now_utc.astimezone(state["snapshot_tz"]).strftime("paraping_snapshot_%Y%m%d_%H%M%S.txt")
        snapshot_lines = build_display_lines(
            state["host_infos"],
            state["buffers"],
            state["stats"],
            state["symbols"],
            state["panel_position"],
            state["modes"][state["mode_index"]],
            state["display_modes"][state["display_mode_index"]],
            state["summary_modes"][state["summary_mode_index"]],
            state["sort_modes"][state["sort_mode_index"]],
            state["filter_modes"][state["filter_mode_index"]],
            args.slow_threshold,
            state["show_help"],
            state["show_asn"],
            state["paused"],
            state["status_message"],
            format_timestamp(now_utc, state["display_tz"]),
            now_utc,
            False,
            state["host_scroll_offset"],
            state["summary_fullscreen"],
            interval_seconds=args.interval,
        )
        with open(snapshot_name, "w", encoding="utf-8") as snapshot_file:
            snapshot_file.write("\n".join(snapshot_lines) + "\n")
        state["status_message"] = f"Saved: {snapshot_name}"
        state["updated"] = True
    elif key == "arrow_left":
        if state["history_offset"] < len(state["history_buffer"]) - 1:
            page_step, state["cached_page_step"], state["last_term_size"] = get_cached_page_step(
                state["cached_page_step"],
                state["last_term_size"],
                state["host_infos"],
                state["buffers"],
                state["stats"],
                state["symbols"],
                state["panel_position"],
                state["modes"][state["mode_index"]],
                state["sort_modes"][state["sort_mode_index"]],
                state["filter_modes"][state["filter_mode_index"]],
                args.slow_threshold,
                state["show_asn"],
            )
            state["history_offset"] = min(state["history_offset"] + page_step, len(state["history_buffer"]) - 1)
            state["force_render"] = True
            state["updated"] = True
            snapshot = state["history_buffer"][-(state["history_offset"] + 1)]
            state["status_message"] = f"Viewing {int(time.time() - snapshot['timestamp'])}s ago"
    elif key == "arrow_right":
        if state["history_offset"] > 0:
            page_step, state["cached_page_step"], state["last_term_size"] = get_cached_page_step(
                state["cached_page_step"],
                state["last_term_size"],
                state["host_infos"],
                state["buffers"],
                state["stats"],
                state["symbols"],
                state["panel_position"],
                state["modes"][state["mode_index"]],
                state["sort_modes"][state["sort_mode_index"]],
                state["filter_modes"][state["filter_mode_index"]],
                args.slow_threshold,
                state["show_asn"],
            )
            state["history_offset"] = max(0, state["history_offset"] - page_step)
            state["force_render"] = True
            state["updated"] = True
            if state["history_offset"] == 0:
                state["status_message"] = "Returned to LIVE view"
            else:
                snapshot = state["history_buffer"][-(state["history_offset"] + 1)]
                state["status_message"] = f"Viewing {int(time.time() - snapshot['timestamp'])}s ago"
    elif key in ("arrow_up", "arrow_down"):
        scroll_buffers = state["buffers"]
        scroll_stats = state["stats"]
        if 0 < state["history_offset"] <= len(state["history_buffer"]):
            snapshot = state["history_buffer"][-(state["history_offset"] + 1)]
            scroll_buffers = snapshot["buffers"]
            scroll_stats = snapshot["stats"]
        max_offset, visible_hosts, total_hosts = compute_host_scroll_bounds(
            state["host_infos"],
            scroll_buffers,
            scroll_stats,
            state["symbols"],
            state["panel_position"],
            state["modes"][state["mode_index"]],
            state["sort_modes"][state["sort_mode_index"]],
            state["filter_modes"][state["filter_mode_index"]],
            args.slow_threshold,
            state["show_asn"],
        )
        if key == "arrow_up" and state["host_scroll_offset"] > 0 and total_hosts > 0:
            state["host_scroll_offset"] = max(0, state["host_scroll_offset"] - 1)
            end_index = min(state["host_scroll_offset"] + visible_hosts, total_hosts)
            state["status_message"] = f"Hosts {state['host_scroll_offset'] + 1}-{end_index} of {total_hosts}"
            state["force_render"] = True
            state["updated"] = True
        elif key == "arrow_down" and state["host_scroll_offset"] < max_offset and total_hosts > 0:
            state["host_scroll_offset"] = min(max_offset, state["host_scroll_offset"] + 1)
            end_index = min(state["host_scroll_offset"] + visible_hosts, total_hosts)
            state["status_message"] = f"Hosts {state['host_scroll_offset'] + 1}-{end_index} of {total_hosts}"
            state["force_render"] = True
            state["updated"] = True
    elif key in ("g", "G"):
        state["host_select_active"] = True
        state["host_select_index"] = 0
        state["force_render"] = True
        state["updated"] = True
    return skip_iteration


def _update_render_state(state: Dict[str, Any]) -> None:
    """Update DNS/ASN/ping data, maintain history snapshots, and resolve current render state."""
    while True:
        try:
            host, rdns_value = state["rdns_result_queue"].get_nowait()
        except queue.Empty:
            break
        for info in state["host_info_map"].get(host, []):
            info["rdns"] = rdns_value
            info["rdns_pending"] = False
        if not state["paused"]:
            state["updated"] = True

    while True:
        try:
            host, asn_value = state["asn_result_queue"].get_nowait()
        except queue.Empty:
            break
        for info in state["host_info_map"].get(host, []):
            info["asn"] = asn_value
            info["asn_pending"] = False
        ip_address = state["host_info_map"][host][0]["ip"] if state["host_info_map"].get(host) else host
        state["asn_cache"][ip_address] = {"value": asn_value, "fetched_at": time.time()}
        if not state["paused"]:
            state["updated"] = True

    now = time.time()
    for host, infos in state["host_info_map"].items():
        if any(info["asn_pending"] for info in infos) or any(info["asn"] is not None for info in infos):
            continue
        ip_address = infos[0]["ip"]
        if should_retry_asn(ip_address, state["asn_cache"], now, state["asn_failure_ttl"]):
            for info in infos:
                info["asn_pending"] = True
            state["asn_request_queue"].put((host, ip_address))

    while True:
        try:
            result = state["result_queue"].get_nowait()
        except queue.Empty:
            break
        host_id = result["host_id"]
        if result.get("status") == "done":
            state["completed_hosts"] += 1
            continue

        status = result["status"]
        host_buf = state["buffers"][host_id]
        if status == "sent":
            host_buf["timeline"].append(state["symbols"]["pending"])
            host_buf["rtt_history"].append(None)
            host_buf["time_history"].append(result.get("sent_time", time.time()))
            host_buf["ttl_history"].append(None)
            host_buf["categories"]["pending"].append(result["sequence"])
            if not state["paused"]:
                state["updated"] = True
            continue

        try:
            last_symbol = host_buf["timeline"][-1]
        except IndexError:
            last_symbol = None

        if last_symbol == state["symbols"].get("pending"):
            host_buf["timeline"][-1] = state["symbols"][status]
            host_buf["rtt_history"][-1] = result.get("rtt")
            host_buf["time_history"][-1] = time.time()
            host_buf["ttl_history"][-1] = result.get("ttl")
            try:
                state["buffers"][host_id]["categories"]["pending"].pop()
            except IndexError:
                pass
            host_buf["categories"][status].append(result["sequence"])
        else:
            host_buf["timeline"].append(state["symbols"][status])
            host_buf["rtt_history"].append(result.get("rtt"))
            host_buf["time_history"].append(time.time())
            host_buf["ttl_history"].append(result.get("ttl"))
            host_buf["categories"][status].append(result["sequence"])

        state["stats"][host_id][status] += 1
        state["stats"][host_id]["total"] += 1
        if result.get("rtt") is not None:
            state["stats"][host_id]["rtt_sum"] += result["rtt"]
            state["stats"][host_id]["rtt_sum_sq"] += result["rtt"] ** 2
            state["stats"][host_id]["rtt_count"] += 1
        if should_flash_on_fail(status, state["flash_on_fail"], state["show_help"]):
            flash_screen()
        if status == "fail" and state["bell_on_fail"] and not state["show_help"]:
            ring_bell()
        if not state["paused"]:
            state["updated"] = True

    now = time.time()
    state["last_snapshot_time"], state["history_offset"] = update_history_buffer(
        state["history_buffer"],
        state["buffers"],
        state["stats"],
        now,
        state["last_snapshot_time"],
        state["history_offset"],
    )
    state["render_buffers"], state["render_stats"], state["render_paused"] = resolve_render_state(
        state["history_offset"],
        state["history_buffer"],
        state["buffers"],
        state["stats"],
        state["paused"],
    )


def _render_frame(args: argparse.Namespace, state: Dict[str, Any]) -> None:
    """Render a frame when needed based on update and refresh timing state."""
    now = time.time()
    should_render = state["force_render"] or (
        not state["paused"] and (state["updated"] or (now - state["last_render"]) >= state["refresh_interval"])
    )
    if not should_render:
        return
    display_timestamp = format_timestamp(datetime.now(timezone.utc), state["display_tz"])
    if 0 < state["history_offset"] <= len(state["history_buffer"]):
        snapshot = state["history_buffer"][-(state["history_offset"] + 1)]
        snapshot_dt = datetime.fromtimestamp(snapshot["timestamp"], timezone.utc)
        display_timestamp = format_timestamp(snapshot_dt, state["display_tz"])
    max_offset, _visible_hosts, _total_hosts = compute_host_scroll_bounds(
        state["host_infos"],
        state["render_buffers"],
        state["render_stats"],
        state["symbols"],
        state["panel_position"],
        state["modes"][state["mode_index"]],
        state["sort_modes"][state["sort_mode_index"]],
        state["filter_modes"][state["filter_mode_index"]],
        args.slow_threshold,
        state["show_asn"],
    )
    state["host_scroll_offset"] = min(state["host_scroll_offset"], max_offset)
    override_lines = None
    term_size = get_terminal_size(fallback=(80, 24))
    if state["show_help"]:
        override_lines = render_help_view(term_size.columns, term_size.lines)
    elif state["host_select_active"]:
        include_asn = should_show_asn(
            state["host_infos"],
            state["modes"][state["mode_index"]],
            state["show_asn"],
            term_size.columns,
        )
        display_names = build_display_names(
            state["host_infos"],
            state["modes"][state["mode_index"]],
            include_asn,
            asn_width=8,
        )
        display_entries = build_display_entries(
            state["host_infos"],
            display_names,
            state["render_buffers"],
            state["render_stats"],
            state["symbols"],
            state["sort_modes"][state["sort_mode_index"]],
            state["filter_modes"][state["filter_mode_index"]],
            args.slow_threshold,
        )
        override_lines = render_host_selection_view(
            display_entries,
            state["host_select_index"],
            term_size.columns,
            term_size.lines,
            state["modes"][state["mode_index"]],
        )
    elif state["graph_host_id"] is not None:
        include_asn = should_show_asn(
            state["host_infos"],
            state["modes"][state["mode_index"]],
            state["show_asn"],
            term_size.columns,
        )
        display_names = build_display_names(
            state["host_infos"],
            state["modes"][state["mode_index"]],
            include_asn,
            asn_width=8,
        )
        host_label = display_names.get(state["graph_host_id"], state["host_infos"][state["graph_host_id"]]["alias"])
        override_lines = render_fullscreen_rtt_graph(
            host_label,
            state["render_buffers"][state["graph_host_id"]]["rtt_history"],
            state["render_buffers"][state["graph_host_id"]]["time_history"],
            term_size.columns,
            term_size.lines,
            state["display_modes"][state["display_mode_index"]],
            state["render_paused"],
            display_timestamp,
            dormant=state["dormant"],
        )
    render_display(
        state["host_infos"],
        state["render_buffers"],
        state["render_stats"],
        state["symbols"],
        state["panel_position"],
        state["modes"][state["mode_index"]],
        state["display_modes"][state["display_mode_index"]],
        state["summary_modes"][state["summary_mode_index"]],
        state["sort_modes"][state["sort_mode_index"]],
        state["filter_modes"][state["filter_mode_index"]],
        args.slow_threshold,
        state["show_help"],
        state["show_asn"],
        state["render_paused"],
        state["status_message"],
        state["display_tz"],
        state["use_color"],
        state["host_scroll_offset"],
        state["summary_fullscreen"],
        override_lines=override_lines,
        interval_seconds=args.interval,
        dormant=state["dormant"],
    )
    state["last_render"] = now
    state["updated"] = False
    state["force_render"] = False


def run(args: argparse.Namespace) -> None:
    """Run the ParaPing monitor with parsed arguments."""
    _configure_logging(getattr(args, "log_level", "INFO"), getattr(args, "log_file", None))
    setup = _setup_hosts_and_state(args)
    if setup is None:
        return

    count_label = "infinite" if args.count == 0 else str(args.count)
    print(
        f"ParaPing - Pinging {len(setup['all_hosts'])} host(s) with timeout={args.timeout}s, "
        f"count={count_label}, interval={args.interval}s, slow-threshold={args.slow_threshold}s"
    )
    state = {
        **setup,
        "modes": ["ip", "rdns", "alias"],
        "mode_index": 2,
        "show_help": False,
        "display_modes": ["timeline", "sparkline", "square"],
        "display_mode_index": 0,
        "summary_modes": ["rates", "rtt", "ttl", "streak"],
        "summary_mode_index": 0,
        "summary_fullscreen": False,
        "sort_modes": ["config", "failures", "streak", "latency", "host"],
        "sort_mode_index": 0,
        "filter_modes": ["failures", "latency", "all"],
        "filter_mode_index": 2,
        "running": True,
        "paused": False,
        "dormant": False,
        "display_paused": False,
        "pause_mode": args.pause_mode,
        "pause_event": threading.Event(),
        "stop_event": threading.Event(),
        "status_message": None,
        "force_render": False,
        "show_asn": True,
        "color_supported": sys.stdout.isatty(),
        "use_color": args.color and sys.stdout.isatty(),
        "flash_on_fail": getattr(args, "flash_on_fail", False),
        "bell_on_fail": getattr(args, "bell_on_fail", False),
        "asn_cache": {},
        "asn_failure_ttl": 300.0,
        "host_select_active": False,
        "host_select_index": 0,
        "graph_host_id": None,
        "history_buffer": deque(maxlen=int(HISTORY_DURATION_MINUTES * 60 / SNAPSHOT_INTERVAL_SECONDS)),
        "history_offset": 0,
        "last_snapshot_time": 0.0,
        "cached_page_step": None,
        "last_term_size": None,
        "host_scroll_offset": 0,
        "completed_hosts": 0,
        "updated": True,
        "last_render": 0.0,
        "refresh_interval": 0.15,
        "expect_completion": args.count > 0,
        "rdns_request_queue": queue.Queue(),
        "rdns_result_queue": queue.Queue(),
        "asn_request_queue": queue.Queue(),
        "asn_result_queue": queue.Queue(),
        "worker_stop": threading.Event(),
    }
    state["rdns_thread"] = threading.Thread(
        target=rdns_worker,
        args=(state["rdns_request_queue"], state["rdns_result_queue"], state["worker_stop"]),
        daemon=True,
    )
    state["asn_thread"] = threading.Thread(
        target=asn_worker,
        args=(state["asn_request_queue"], state["asn_result_queue"], state["worker_stop"], 3.0),
        daemon=True,
    )
    state["rdns_thread"].start()
    state["asn_thread"].start()

    stdin_fd: Optional[int] = None
    original_term: Optional[List[Any]] = None
    if sys.stdin.isatty():
        stdin_fd = sys.stdin.fileno()
        original_term = termios.tcgetattr(stdin_fd)

    num_hosts = len(state["host_infos"])
    scheduler = Scheduler(interval=args.interval, stagger=(args.interval / num_hosts if num_hosts > 0 else 0.0))
    ping_lock = threading.Lock()
    sequence_tracker = SequenceTracker(max_outstanding=3)
    for info in state["host_infos"]:
        scheduler.add_host(info["host"], host_id=info["id"])

    with ThreadPoolExecutor(max_workers=len(setup["all_hosts"])) as executor:
        for host, infos in state["host_info_map"].items():
            info = infos[0]
            for entry in infos:
                entry["rdns_pending"] = True
            state["rdns_request_queue"].put((host, info["ip"]))
            now = time.time()
            if info["ip"] in state["asn_cache"] and state["asn_cache"][info["ip"]]["value"] is not None:
                for entry in infos:
                    entry["asn"] = state["asn_cache"][info["ip"]]["value"]
                    entry["asn_pending"] = False
            elif should_retry_asn(info["ip"], state["asn_cache"], now, state["asn_failure_ttl"]):
                for entry in infos:
                    entry["asn_pending"] = True
                state["asn_request_queue"].put((host, info["ip"]))
        for info in state["host_infos"]:
            executor.submit(
                scheduler_driven_worker_ping,
                info,
                scheduler,
                args.timeout,
                args.count,
                args.slow_threshold,
                state["pause_event"],
                state["stop_event"],
                state["result_queue"],
                state["ping_helper_path"],
                ping_lock,
                sequence_tracker,
            )
        try:
            if stdin_fd is not None:
                tty.setcbreak(stdin_fd)
            while state["running"] and (
                not state["expect_completion"] or state["completed_hosts"] < len(state["host_infos"])
            ):
                key = read_key()
                if key and _handle_user_input(key, args, state):
                    continue
                _update_render_state(state)
                _render_frame(args, state)
                time.sleep(0.05)
        except KeyboardInterrupt:
            state["running"] = False
            state["stop_event"].set()
        finally:
            state["stop_event"].set()
            state["worker_stop"].set()
            state["rdns_request_queue"].put(None)
            state["asn_request_queue"].put(None)
            state["rdns_thread"].join(timeout=1.0)
            state["asn_thread"].join(timeout=1.0)
            if stdin_fd is not None and original_term is not None:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, original_term)

    prepare_terminal_for_exit()
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for info in state["host_infos"]:
        host_id = info["id"]
        success = state["stats"][host_id]["success"]
        slow = state["stats"][host_id]["slow"]
        fail = state["stats"][host_id]["fail"]
        total = state["stats"][host_id]["total"]
        percentage = (success / total * 100) if total > 0 else 0
        status = "OK" if success > 0 else "FAILED"
        print(f"{info['alias']:30} {success}/{total} replies, {slow} slow, {fail} failed " f"({percentage:.1f}%) [{status}]")


def main() -> None:
    """Main entrypoint for the CLI - parses arguments and runs the application."""
    args = handle_options()
    run(args)
