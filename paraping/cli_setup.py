#!/usr/bin/env python3
# Copyright 2026 icecake0141
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

"""Startup host and runtime setup for the ParaPing CLI."""

import os
import queue
import sys
from datetime import timezone, tzinfo
from typing import Any, Callable, Dict, List, Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from paraping.runtime.constants import MAX_HOST_THREADS
from paraping.runtime.engine import MonitorState
from paraping.runtime.rate_limit import validate_global_rate_limit


def collect_hosts(args: Any, read_input_file_with_report_func: Callable[[str], Any]) -> List[Union[str, Dict[str, Any]]]:
    """Collect hosts from CLI arguments and an optional input file."""
    all_hosts: List[Union[str, Dict[str, Any]]] = []
    if args.hosts:
        all_hosts.extend({"host": host, "alias": host} for host in args.hosts)
    if not args.input:
        return all_hosts

    parsed_hosts, parse_report = read_input_file_with_report_func(args.input)
    if parse_report.has_errors:
        print(f"Error: {args.input} contains {parse_report.error_count} format error(s).", file=sys.stderr)
        for issue in parse_report.issues:
            if issue.severity != "error":
                continue
            line_label = issue.line_number if issue.line_number > 0 else "-"
            print(f"{args.input}:{line_label}: {issue.reason} | {issue.raw_line}", file=sys.stderr)
        sys.exit(1)
    all_hosts.extend(parsed_hosts)
    return all_hosts


def resolve_display_timezone(timezone_name: Optional[str]) -> Optional[tzinfo]:
    """Resolve a configured display timezone."""
    if not timezone_name:
        return timezone.utc
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        print(f"Error: Unknown timezone '{timezone_name}'. Use an IANA name like 'Asia/Tokyo'.")
        return None


def resolve_ping_helper_path(args: Any, os_module: Any) -> Optional[str]:
    """Resolve and validate the ping helper executable path."""
    ping_helper_path = os_module.path.abspath(os_module.path.expanduser(args.ping_helper))
    if not os_module.path.exists(ping_helper_path):
        print(
            "Error: ping_helper binary not found at "
            f"'{ping_helper_path}'. Run 'make build' first. "
            "On macOS, run ParaPing with sudo because setcap is unavailable.",
            file=sys.stderr,
        )
        return None
    if not os_module.access(ping_helper_path, os_module.X_OK):
        print(
            "Error: ping_helper is not executable at "
            f"'{ping_helper_path}'. Run 'chmod +x {ping_helper_path}' "
            "or rebuild with 'make build'.",
            file=sys.stderr,
        )
        return None
    return str(ping_helper_path)


def setup_hosts_and_state(
    args: Any,
    read_input_file_with_report_func: Callable[[str], Any],
    build_host_infos_func: Callable[[List[Union[str, Dict[str, Any]]]], Any],
    compute_initial_timeline_width_func: Callable[[List[str], Any, str, str], int],
    get_terminal_size_func: Callable[..., Any],
    os_module: Any = os,
    queue_factory: Callable[[], Any] = queue.Queue,
) -> Optional[Dict[str, Any]]:
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

    all_hosts = collect_hosts(args, read_input_file_with_report_func)
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

    display_tz = resolve_display_timezone(args.timezone)
    if display_tz is None:
        return None
    snapshot_tz: tzinfo = display_tz if args.snapshot_timezone == "display" else timezone.utc
    panel_position = args.panel_position
    pulse_position = "bottom" if getattr(args, "kitt", False) else "none"
    symbols: Dict[str, str] = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}
    host_infos, host_info_map = build_host_infos_func(all_hosts)
    host_labels = [info["alias"] for info in host_infos]
    timeline_width = compute_initial_timeline_width_func(
        host_labels, get_terminal_size_func(fallback=(80, 24)), panel_position, pulse_position
    )
    ping_helper_path = resolve_ping_helper_path(args, os_module)
    if ping_helper_path is None:
        return None
    return {
        "all_hosts": all_hosts,
        "display_tz": display_tz,
        "snapshot_tz": snapshot_tz,
        "ping_helper_path": ping_helper_path,
        "panel_position": panel_position,
        "panel_toggle_default": panel_position if panel_position != "none" else "right",
        "last_panel_position": panel_position if panel_position != "none" else None,
        "pulse_position": pulse_position,
        "pulse_toggle_default": "bottom",
        "last_pulse_position": pulse_position if pulse_position != "none" else "bottom",
        "symbols": symbols,
        "host_infos": host_infos,
        "host_info_map": host_info_map,
        # Shadow state for incremental runtime migration. This does not affect
        # rendering yet; it only mirrors ping events for parity validation.
        "monitor_state": MonitorState(host_ids=[info["id"] for info in host_infos], timeline_width=timeline_width),
        "result_queue": queue_factory(),
    }
