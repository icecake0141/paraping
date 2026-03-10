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
import re
import sys
import termios
import threading
import time
import tty
import warnings
from collections import deque
from concurrent.futures import ThreadPoolExecutor  # noqa: F401 - Backward-compatibility for tests patching this symbol.
from datetime import datetime, timezone, tzinfo
from typing import Any, Callable, Dict, List, Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from paraping.cli_options import CLI_OPTION_SPECS, OptionSpec
from paraping.config import load_config
from paraping.core import (
    _normalize_term_size,
    build_host_infos,
    get_cached_page_step,
    read_input_file,
    read_input_file_with_report,
)
from paraping.input_keys import read_key
from paraping.keymap import KeyContext, resolve_action
from paraping.network_asn import asn_worker, should_retry_asn
from paraping.pinger import rdns_worker, scheduler_driven_worker_ping
from paraping.ui_render import (
    build_display_entries,
    build_display_lines,
    build_display_names,
    compute_host_scroll_bounds,
    compute_main_layout,
    compute_panel_sizes,
    compute_pulse_panel_sizes,
    cycle_panel_position,
    flash_screen,
    format_timestamp,
    get_terminal_size,
    prepare_terminal_for_exit,
    render_display,
    render_fullscreen_rtt_graph,
    render_help_view,
    render_host_selection_view,
    reset_render_cache,
    ring_bell,
    should_flash_on_fail,
    should_show_asn,
    toggle_panel_visibility,
)
from paraping_v2.constants import HISTORY_DURATION_MINUTES, MAX_HOST_THREADS, SNAPSHOT_INTERVAL_SECONDS
from paraping_v2.engine import MonitorState
from paraping_v2.history import update_history_buffer_v2
from paraping_v2.legacy_adapter import project_legacy_state_from_v2
from paraping_v2.rate_limit import validate_global_rate_limit
from paraping_v2.render_state import resolve_v2_render_state
from paraping_v2.scheduler import Scheduler
from paraping_v2.sequence_tracker import SequenceTracker
from paraping_v2.shadow import apply_shadow_v2_event

REMOVED_HOST_RETENTION_SECONDS = 10.0


def _compute_initial_timeline_width(
    host_labels: List[str], term_size: Any, panel_position: str, pulse_position: str = "none"
) -> int:
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
    main_width, main_height, _, _, _ = compute_pulse_panel_sizes(main_width, main_height, pulse_position)
    # Always use header_lines=2 for consistent initial sizing
    _, _, timeline_width, _ = compute_main_layout(host_labels, main_width, main_height, header_lines=2)
    try:
        return max(1, int(timeline_width))
    except (TypeError, ValueError):
        return 1


def _compute_runtime_timeline_width(state: Dict[str, Any], term_size: Any) -> int:
    """
    Compute the current timeline width from live terminal/layout state.

    This is used to keep v2 timeline buffers aligned with runtime terminal
    resizing so history capacity does not remain stuck at startup width.
    """
    normalized_size = _normalize_term_size(term_size)
    if normalized_size is None:
        return 1

    status_box_height = 3 if normalized_size.lines >= 4 and normalized_size.columns >= 2 else 1
    panel_height = max(1, normalized_size.lines - status_box_height)
    main_width, main_height, _, _, _ = compute_panel_sizes(normalized_size.columns, panel_height, state["panel_position"])
    main_width, main_height, _, _, _ = compute_pulse_panel_sizes(main_width, main_height, state.get("pulse_position", "none"))
    mode_label = state["modes"][state["mode_index"]]
    include_asn = should_show_asn(state["host_infos"], mode_label, state["show_asn"], normalized_size.columns, asn_width=8)
    display_names = build_display_names(state["host_infos"], mode_label, include_asn, asn_width=8)
    host_labels = list(display_names.values()) or [info["alias"] for info in state["host_infos"]]
    _, _, timeline_width, _ = compute_main_layout(host_labels, main_width, main_height, header_lines=2)
    try:
        return max(1, int(timeline_width))
    except (TypeError, ValueError):
        return 1


def _check_terminal_resize_and_request_redraw(state: Dict[str, Any], now_monotonic: float) -> None:
    """
    Periodically detect terminal size changes and request a full redraw.

    This intentionally runs at low frequency (default: once per second) to
    keep overhead low while still recovering from resize-related render
    artifacts.
    """
    next_check = float(state.get("next_resize_check_time", 0.0))
    if now_monotonic < next_check:
        return

    check_interval = max(0.1, float(state.get("resize_check_interval", 1.0)))
    state["next_resize_check_time"] = now_monotonic + check_interval

    current_size = _normalize_term_size(get_terminal_size(fallback=(80, 24)))
    previous_size = _normalize_term_size(state.get("last_observed_term_size"))
    state["last_observed_term_size"] = current_size

    if current_size is None or previous_size is None:
        return
    if current_size.columns == previous_size.columns and current_size.lines == previous_size.lines:
        return

    # Match hotkey `u` behavior for resize recovery.
    reset_render_cache()
    state["cached_page_step"] = None
    state["last_term_size"] = None
    state["force_render"] = True
    state["updated"] = True


def _configure_logging(
    log_level: str,
    log_file: Optional[str],
    interactive_ui: bool = False,
    verbose_ui_errors: bool = False,
) -> None:
    """Configure logging handlers for CLI execution."""
    handlers: List[logging.Handler] = []
    # Avoid polluting the live TUI with asynchronous log lines.
    if (not interactive_ui) or verbose_ui_errors:
        handlers.append(logging.StreamHandler())
    if log_file:
        handlers.append(logging.FileHandler(os.path.expanduser(log_file), encoding="utf-8"))
    if not handlers:
        handlers.append(logging.NullHandler())
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(message)s",
        handlers=handlers,
        force=True,
    )


def _add_option_from_spec(parser: argparse.ArgumentParser, spec: OptionSpec) -> None:
    """Register one option spec on the argparse parser."""
    kwargs: Dict[str, Any] = {
        "dest": spec.dest,
        "default": None,
        "help": spec.help_text,
    }
    if spec.boolean:
        kwargs["action"] = argparse.BooleanOptionalAction
    else:
        if spec.value_type is not None:
            kwargs["type"] = str.upper if spec.dest == "log_level" else spec.value_type
        if spec.choices:
            kwargs["choices"] = list(spec.choices)
    parser.add_argument(*spec.flags, **kwargs)


def _apply_option_defaults(args: argparse.Namespace) -> None:
    """Apply defaults for unset values after config overlay."""
    for spec in CLI_OPTION_SPECS:
        if getattr(args, spec.dest, None) is None:
            setattr(args, spec.dest, spec.default)


def _count_entry_tags(host_info: Dict[str, Any]) -> int:
    """Count non-empty tag values in one host record."""
    tags = host_info.get("tags") or []
    if not isinstance(tags, list):
        tags = [tags]
    return sum(1 for tag in tags if str(tag).strip())


def _build_group_by_modes(host_infos: List[Dict[str, Any]]) -> List[str]:
    """Build group-key cycle modes, including tagN and hierarchical modes."""
    max_tag_count = max((_count_entry_tags(info) for info in host_infos), default=0)
    tag_count = max(1, max_tag_count)
    tag_modes = [f"tag{index}" for index in range(1, tag_count + 1)]
    return ["none", "asn", "site", *tag_modes, "site>tag1", "tag1>site"]


def _sync_group_by_modes(state: Dict[str, Any], preferred_group_by: Optional[str] = None) -> None:
    """Refresh group-key modes from host data while preserving the current selection."""
    current_group_by = preferred_group_by
    if current_group_by is None:
        modes = state.get("group_by_modes") or []
        mode_index = int(state.get("group_by_mode_index", 0))
        if modes:
            current_group_by = str(modes[mode_index % len(modes)])
    if current_group_by == "tag":
        current_group_by = "tag1"

    modes = _build_group_by_modes(state.get("host_infos", []))
    state["group_by_modes"] = modes
    if current_group_by in modes:
        state["group_by_mode_index"] = modes.index(current_group_by)
    else:
        state["group_by_mode_index"] = 0


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
        if key == "verbose_ui_errors":
            key = "ui_log_errors"
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
    for spec in CLI_OPTION_SPECS:
        _add_option_from_spec(parser, spec)

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--verbose-ui-errors",
        action="store_true",
        dest="deprecated_verbose_ui_errors",
        default=False,
        help=argparse.SUPPRESS,
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

    if args.verbose:
        warnings.warn("--verbose is deprecated; use --log-level DEBUG instead.", DeprecationWarning, stacklevel=2)
        if getattr(args, "log_level", None) is None:
            args.log_level = "DEBUG"
    if args.deprecated_verbose_ui_errors:
        warnings.warn(
            "--verbose-ui-errors is deprecated; use --ui-log-errors instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        args.ui_log_errors = True

    _apply_option_defaults(args)
    args.log_level = str(args.log_level).upper()
    if args.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        parser.error("--log-level must be one of DEBUG|INFO|WARNING|ERROR")
    args.verbose_ui_errors = args.ui_log_errors

    if args.timeout <= 0:
        parser.error("--timeout must be a positive integer.")
    if not 0.1 <= args.interval <= 60.0:
        parser.error("--interval must be between 0.1 and 60.0 seconds.")
    if args.group_by not in ("none", "asn", "site", "tag", "site>tag1", "tag1>site") and not re.match(
        r"^tag\d+$", args.group_by
    ):
        parser.error("--group-by must be one of none|asn|site|tag|tagN|site>tag1|tag1>site")
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

    all_hosts: List[Union[str, Dict[str, Any]]] = []
    if args.hosts:
        all_hosts.extend({"host": host, "alias": host} for host in args.hosts)
    if args.input:
        parsed_hosts, parse_report = read_input_file_with_report(args.input)
        if parse_report.has_errors:
            print(f"Error: {args.input} contains {parse_report.error_count} format error(s).", file=sys.stderr)
            for issue in parse_report.issues:
                if issue.severity != "error":
                    continue
                line_label = issue.line_number if issue.line_number > 0 else "-"
                print(f"{args.input}:{line_label}: {issue.reason} | {issue.raw_line}", file=sys.stderr)
            sys.exit(1)
        all_hosts.extend(parsed_hosts)
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
    pulse_position = "bottom" if getattr(args, "kitt", False) else "none"
    symbols: Dict[str, str] = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}
    host_infos, host_info_map = build_host_infos(all_hosts)
    host_labels = [info["alias"] for info in host_infos]
    timeline_width = _compute_initial_timeline_width(
        host_labels, get_terminal_size(fallback=(80, 24)), panel_position, pulse_position
    )
    ping_helper_path = os.path.abspath(os.path.expanduser(args.ping_helper))
    if not os.path.exists(ping_helper_path):
        print(
            "Error: ping_helper binary not found at "
            f"'{ping_helper_path}'. Run 'make build' first. "
            "On macOS, run ParaPing with sudo because setcap is unavailable.",
            file=sys.stderr,
        )
        return None
    if not os.access(ping_helper_path, os.X_OK):
        print(
            "Error: ping_helper is not executable at "
            f"'{ping_helper_path}'. Run 'chmod +x {ping_helper_path}' "
            "or rebuild with 'make build'.",
            file=sys.stderr,
        )
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
        # Shadow state for incremental v2 migration. This does not affect
        # rendering yet; it only mirrors ping events for parity validation.
        "v2_state": MonitorState(host_ids=[info["id"] for info in host_infos], timeline_width=timeline_width),
        "result_queue": queue.Queue(),
    }


def _rebuild_host_info_map(host_infos: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Rebuild host-to-info mapping for DNS/ASN updates."""
    host_info_map: Dict[str, List[Dict[str, Any]]] = {}
    for info in host_infos:
        host_info_map.setdefault(info["host"], []).append(info)
    return host_info_map


def _build_host_info_from_entry(entry: Dict[str, Any], host_id: int) -> Dict[str, Any]:
    """Create a host info record from parsed input entry."""
    host = entry.get("host") or entry.get("ip") or ""
    alias = entry.get("alias") or host
    ip_address = entry.get("ip") or host
    return {
        "id": host_id,
        "host": host,
        "alias": alias,
        "ip": ip_address,
        "site": entry.get("site") or "",
        "tags": list(entry.get("tags") or []),
        "rdns": None,
        "rdns_pending": False,
        "asn": None,
        "asn_pending": False,
        "active": True,
        "removed": False,
        "retired_until": None,
    }


def _start_host_worker(
    host_info: Dict[str, Any],
    args: argparse.Namespace,
    state: Dict[str, Any],
    scheduler: Scheduler,
    ping_lock: threading.Lock,
    sequence_tracker: SequenceTracker,
) -> None:
    """Start one scheduler-driven worker thread for a host."""
    thread = threading.Thread(
        target=scheduler_driven_worker_ping,
        args=(
            host_info,
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
        ),
        daemon=True,
    )
    state["worker_threads"][host_info["id"]] = thread
    thread.start()


def _active_host_count(state: Dict[str, Any]) -> int:
    """Count active hosts currently monitored by scheduler workers."""
    return sum(1 for info in state["host_infos"] if info.get("active", True))


def _all_active_hosts_completed(state: Dict[str, Any]) -> bool:
    """Check whether all active hosts have emitted completion markers."""
    active_ids = {info["id"] for info in state["host_infos"] if info.get("active", True)}
    return active_ids.issubset(state["done_host_ids"])


def _apply_manual_reload(
    args: argparse.Namespace,
    state: Dict[str, Any],
    scheduler: Scheduler,
    ping_lock: threading.Lock,
    sequence_tracker: SequenceTracker,
) -> str:
    """Reload hosts from input file and apply add/remove/update deltas."""
    if not args.input:
        return "Reload unavailable: start with -f/--input"

    loaded_hosts = read_input_file(args.input)
    if not loaded_hosts:
        return "Reload failed: input file is empty or invalid"

    desired_by_ip: Dict[str, Dict[str, str]] = {}
    for entry in loaded_hosts:
        ip_address = entry.get("ip") or entry.get("host")
        if not ip_address:
            continue
        if ip_address in desired_by_ip:
            continue
        desired_by_ip[ip_address] = entry

    if not desired_by_ip:
        return "Reload failed: no valid hosts"

    existing_by_ip = {info["ip"]: info for info in state["host_infos"]}
    active_ips = {info["ip"] for info in state["host_infos"] if info.get("active", True)}
    desired_ips = set(desired_by_ip.keys())

    added_count = 0
    removed_count = 0

    for ip_address in sorted(active_ips - desired_ips):
        info = existing_by_ip.get(ip_address)
        if info is None:
            continue
        info["active"] = False
        info["removed"] = True
        info["retired_until"] = time.time() + REMOVED_HOST_RETENTION_SECONDS
        with ping_lock:
            scheduler.remove_host(info["host"])
            host_count = scheduler.get_host_count()
            scheduler.set_stagger(args.interval / host_count if host_count > 0 else 0.0)
        removed_count += 1

    now = time.time()
    for ip_address in sorted(desired_ips):
        entry = desired_by_ip[ip_address]
        info = existing_by_ip.get(ip_address)
        if info is not None:
            info["host"] = entry.get("host") or info["host"]
            info["alias"] = entry.get("alias") or info["alias"]
            info["ip"] = ip_address
            info["site"] = entry.get("site") or ""
            info["tags"] = list(entry.get("tags") or [])
            if not info.get("active", True):
                info["active"] = True
                info["removed"] = False
                info["retired_until"] = None
                with ping_lock:
                    scheduler.add_host(info["host"], host_id=info["id"])
                    host_count = scheduler.get_host_count()
                    scheduler.set_stagger(args.interval / host_count if host_count > 0 else 0.0)
                state["done_host_ids"].discard(info["id"])
                _start_host_worker(info, args, state, scheduler, ping_lock, sequence_tracker)
                info["rdns_pending"] = True
                state["rdns_request_queue"].put((info["host"], info["ip"]))
                if should_retry_asn(info["ip"], state["asn_cache"], now, state["asn_failure_ttl"]):
                    info["asn_pending"] = True
                    state["asn_request_queue"].put((info["host"], info["ip"]))
                added_count += 1
            continue

        new_info = _build_host_info_from_entry(entry, state["next_host_id"])
        state["next_host_id"] += 1
        state["host_infos"].append(new_info)
        state["v2_state"].add_host(new_info["id"])
        with ping_lock:
            scheduler.add_host(new_info["host"], host_id=new_info["id"])
            host_count = scheduler.get_host_count()
            scheduler.set_stagger(args.interval / host_count if host_count > 0 else 0.0)
        state["done_host_ids"].discard(new_info["id"])
        _start_host_worker(new_info, args, state, scheduler, ping_lock, sequence_tracker)
        new_info["rdns_pending"] = True
        state["rdns_request_queue"].put((new_info["host"], new_info["ip"]))
        if should_retry_asn(new_info["ip"], state["asn_cache"], now, state["asn_failure_ttl"]):
            new_info["asn_pending"] = True
            state["asn_request_queue"].put((new_info["host"], new_info["ip"]))
        added_count += 1

    state["host_info_map"] = _rebuild_host_info_map(state["host_infos"])
    _sync_group_by_modes(state)
    state["cached_page_step"] = None
    state["updated"] = True
    state["force_render"] = True
    return f"Reloaded: +{added_count} -{removed_count} (total {_active_host_count(state)})"


def _purge_expired_removed_hosts(state: Dict[str, Any]) -> None:
    """Permanently remove hosts after retirement window expires."""
    now = time.time()
    remaining_infos: List[Dict[str, Any]] = []
    purged_ids: List[int] = []
    for info in state["host_infos"]:
        if info.get("active", True):
            remaining_infos.append(info)
            continue
        retired_until = info.get("retired_until")
        if retired_until is None or now < retired_until:
            remaining_infos.append(info)
            continue
        purged_ids.append(info["id"])

    if not purged_ids:
        return

    state["host_infos"] = remaining_infos
    for host_id in purged_ids:
        state["v2_state"].remove_host(host_id)
        state["worker_threads"].pop(host_id, None)
        state["done_host_ids"].discard(host_id)
        if state.get("graph_host_id") == host_id:
            state["graph_host_id"] = None
    state["host_info_map"] = _rebuild_host_info_map(state["host_infos"])
    _sync_group_by_modes(state)
    state["cached_page_step"] = None
    state["updated"] = True


def _handle_user_input(
    key: str,
    args: argparse.Namespace,
    state: Dict[str, Any],
    scheduler: Optional[Scheduler] = None,
    ping_lock: Optional[threading.Lock] = None,
    sequence_tracker: Optional[SequenceTracker] = None,
) -> bool:
    """Process one keyboard input event and return True when the current loop iteration should be skipped."""
    skip_iteration = False
    context: KeyContext = "main"
    if state.get("show_help"):
        context = "help"
    elif state.get("host_select_active"):
        context = "host_select"
    elif state.get("graph_host_id") is not None:
        context = "graph"

    action = resolve_action(key, context) or ""

    if action == "quit":
        state["running"] = False
        state["stop_event"].set()
        return skip_iteration

    if context == "help":
        if action in ("help_toggle", "back"):
            state["show_help"] = False
            state["force_render"] = True
            state["updated"] = True
            skip_iteration = True
        return skip_iteration

    if action == "help_toggle":
        state["show_help"] = True
        state["force_render"] = True
        state["updated"] = True
        return skip_iteration

    if context == "host_select":
        render_buffers = state["render_buffers"]
        render_stats = state["render_stats"]
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
            group_by=state["group_by_modes"][state["group_by_mode_index"]],
            group_sort_enabled=state["summary_scope_modes"][state["summary_scope_mode_index"]] == "group",
        )
        if not display_entries:
            state["host_select_index"] = 0
        else:
            state["host_select_index"] = min(max(state["host_select_index"], 0), len(display_entries) - 1)
        if action == "select_prev" and display_entries:
            state["host_select_index"] = max(0, state["host_select_index"] - 1)
            state["force_render"] = True
            state["updated"] = True
        elif action == "select_next" and display_entries:
            state["host_select_index"] = min(len(display_entries) - 1, state["host_select_index"] + 1)
            state["force_render"] = True
            state["updated"] = True
        elif action == "select_confirm":
            if display_entries:
                state["graph_host_id"] = display_entries[state["host_select_index"]][0]
                state["host_select_active"] = False
                state["force_render"] = True
                state["updated"] = True
        elif action == "back":
            state["host_select_active"] = False
            state["force_render"] = True
            state["updated"] = True
        if action:
            skip_iteration = True
        return skip_iteration

    if context == "graph":
        if action == "back":
            state["graph_host_id"] = None
            state["force_render"] = True
            state["updated"] = True
            skip_iteration = True
        elif action == "host_select_open":
            state["host_select_active"] = True
            state["graph_host_id"] = None
            state["force_render"] = True
            state["updated"] = True
            skip_iteration = True
        elif action == "graph_toggle":
            state["display_mode_index"] = (state["display_mode_index"] + 1) % len(state["display_modes"])
            state["updated"] = True
        return skip_iteration

    action_handlers: Dict[str, Callable[[], None]] = {}

    def _handle_reload() -> None:
        if scheduler is None or ping_lock is None or sequence_tracker is None:
            state["status_message"] = "Reload unavailable in this context"
        else:
            state["status_message"] = _apply_manual_reload(args, state, scheduler, ping_lock, sequence_tracker)
        state["updated"] = True
        state["force_render"] = True

    def _handle_force_redraw() -> None:
        reset_render_cache()
        state["status_message"] = "Full redraw requested"
        state["force_render"] = True
        state["updated"] = True

    def _handle_display_mode_cycle() -> None:
        state["mode_index"] = (state["mode_index"] + 1) % len(state["modes"])
        state["cached_page_step"] = None
        state["updated"] = True

    def _handle_view_cycle() -> None:
        state["display_mode_index"] = (state["display_mode_index"] + 1) % len(state["display_modes"])
        state["updated"] = True

    def _handle_kitt_toggle() -> None:
        state["kitt_mode_enabled"] = not state["kitt_mode_enabled"]
        pulse_position = state.get("pulse_position", "none")
        last_pulse_position = state.get("last_pulse_position", "bottom")
        pulse_toggle_default = state.get("pulse_toggle_default", "bottom")
        if state["kitt_mode_enabled"] and pulse_position == "none":
            restored_position = last_pulse_position or pulse_toggle_default
            state["pulse_position"] = restored_position
            state["last_pulse_position"] = restored_position
        state["status_message"] = "Pulse mode enabled" if state["kitt_mode_enabled"] else "Pulse mode disabled"
        state["cached_page_step"] = None
        state["force_render"] = True
        state["updated"] = True

    def _handle_kitt_style_cycle() -> None:
        if state["kitt_mode_enabled"]:
            state["kitt_style_index"] = (state["kitt_style_index"] + 1) % len(state["kitt_style_modes"])
            current_style = state["kitt_style_modes"][state["kitt_style_index"]]
            state["status_message"] = f"Pulse style: {current_style}"
        else:
            state["status_message"] = "Pulse mode is off (press 'y' first)"
        state["force_render"] = True
        state["updated"] = True

    def _handle_sort_cycle() -> None:
        state["sort_mode_index"] = (state["sort_mode_index"] + 1) % len(state["sort_modes"])
        state["cached_page_step"] = None
        state["updated"] = True

    def _handle_filter_cycle() -> None:
        state["filter_mode_index"] = (state["filter_mode_index"] + 1) % len(state["filter_modes"])
        state["cached_page_step"] = None
        state["updated"] = True

    def _handle_asn_toggle() -> None:
        state["show_asn"] = not state["show_asn"]
        state["cached_page_step"] = None
        state["updated"] = True

    def _handle_summary_mode_cycle() -> None:
        state["summary_mode_index"] = (state["summary_mode_index"] + 1) % len(state["summary_modes"])
        state["status_message"] = f"Summary: {state['summary_modes'][state['summary_mode_index']].upper()}"
        state["updated"] = True

    def _handle_summary_scope_cycle() -> None:
        state["summary_scope_mode_index"] = (state["summary_scope_mode_index"] + 1) % len(state["summary_scope_modes"])
        scope = state["summary_scope_modes"][state["summary_scope_mode_index"]]
        state["status_message"] = f"Summary scope: {scope.upper()}"
        state["cached_page_step"] = None
        state["updated"] = True

    def _handle_group_key_cycle() -> None:
        state["group_by_mode_index"] = (state["group_by_mode_index"] + 1) % len(state["group_by_modes"])
        group_by = state["group_by_modes"][state["group_by_mode_index"]]
        state["status_message"] = f"Group key: {group_by}"
        state["cached_page_step"] = None
        state["updated"] = True

    def _handle_color_toggle() -> None:
        if not state["color_supported"]:
            state["status_message"] = "Color output unavailable (no TTY)"
        else:
            state["use_color"] = not state["use_color"]
            state["status_message"] = "Color output enabled" if state["use_color"] else "Color output disabled"
        state["force_render"] = True
        state["updated"] = True

    def _handle_bell_toggle() -> None:
        state["bell_on_fail"] = not state["bell_on_fail"]
        state["status_message"] = "Bell on fail enabled" if state["bell_on_fail"] else "Bell on fail disabled"
        state["force_render"] = True
        state["updated"] = True

    def _handle_summary_fullscreen_toggle() -> None:
        state["summary_fullscreen"] = not state["summary_fullscreen"]
        state["status_message"] = (
            "Summary fullscreen view enabled" if state["summary_fullscreen"] else "Summary fullscreen view disabled"
        )
        state["force_render"] = True
        state["updated"] = True

    def _handle_panel_toggle() -> None:
        state["panel_position"], state["last_panel_position"] = toggle_panel_visibility(
            state["panel_position"],
            state["last_panel_position"],
            default_position=state["panel_toggle_default"],
        )
        state["status_message"] = "Summary panel hidden" if state["panel_position"] == "none" else "Summary panel shown"
        state["cached_page_step"] = None
        state["force_render"] = True
        state["updated"] = True

    def _handle_panel_position_cycle() -> None:
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

    def _handle_pulse_panel_toggle() -> None:
        state["pulse_position"], state["last_pulse_position"] = toggle_panel_visibility(
            state["pulse_position"],
            state["last_pulse_position"],
            default_position=state["pulse_toggle_default"],
        )
        state["status_message"] = "Pulse panel hidden" if state["pulse_position"] == "none" else "Pulse panel shown"
        state["cached_page_step"] = None
        state["force_render"] = True
        state["updated"] = True

    def _handle_pulse_panel_position_cycle() -> None:
        reference_position = (
            state["pulse_position"]
            if state["pulse_position"] != "none"
            else state["last_pulse_position"] or state["pulse_toggle_default"]
        )
        state["pulse_position"] = cycle_panel_position(reference_position, default_position=state["pulse_toggle_default"])
        state["last_pulse_position"] = state["pulse_position"]
        state["status_message"] = f"Pulse panel position: {state['pulse_position'].upper()}"
        state["cached_page_step"] = None
        state["force_render"] = True
        state["updated"] = True

    def _handle_display_pause_toggle() -> None:
        state["display_paused"] = not state["display_paused"]
        state["paused"] = state["display_paused"] or state["dormant"]
        if state["dormant"] or (state["pause_mode"] == "ping" and state["display_paused"]):
            state["pause_event"].set()
        else:
            state["pause_event"].clear()
        state["status_message"] = "Display paused" if state["display_paused"] else "Display resumed"
        state["force_render"] = True
        state["updated"] = True

    def _handle_dormant_toggle() -> None:
        state["dormant"] = not state["dormant"]
        state["paused"] = state["display_paused"] or state["dormant"]
        if state["dormant"] or (state["pause_mode"] == "ping" and state["display_paused"]):
            state["pause_event"].set()
        else:
            state["pause_event"].clear()
        state["status_message"] = "Dormant mode enabled" if state["dormant"] else "Dormant mode disabled"
        state["force_render"] = True
        state["updated"] = True

    def _handle_snapshot_save() -> None:
        now_utc = datetime.now(timezone.utc)
        snapshot_name = now_utc.astimezone(state["snapshot_tz"]).strftime("paraping_snapshot_%Y%m%d_%H%M%S.txt")
        snapshot_lines = build_display_lines(
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
            format_timestamp(now_utc, state["display_tz"]),
            now_utc,
            False,
            state["host_scroll_offset"],
            state["summary_fullscreen"],
            interval_seconds=args.interval,
            summary_scope=state["summary_scope_modes"][state["summary_scope_mode_index"]],
            group_by=state["group_by_modes"][state["group_by_mode_index"]],
            group_sort_enabled=state["summary_scope_modes"][state["summary_scope_mode_index"]] == "group",
            kitt_mode_enabled=state["kitt_mode_enabled"],
            kitt_style=state["kitt_style_modes"][state["kitt_style_index"]],
            pulse_position=state["pulse_position"],
        )
        with open(snapshot_name, "w", encoding="utf-8") as snapshot_file:
            snapshot_file.write("\n".join(snapshot_lines) + "\n")
        state["status_message"] = f"Saved: {snapshot_name}"
        state["updated"] = True

    def _handle_history_prev() -> None:
        if state["v2_history_offset"] < len(state["v2_history_buffer"]) - 1:
            page_step, state["cached_page_step"], state["last_term_size"] = get_cached_page_step(
                state["cached_page_step"],
                state["last_term_size"],
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
                pulse_position=state["pulse_position"],
            )
            state["v2_history_offset"] = min(state["v2_history_offset"] + page_step, len(state["v2_history_buffer"]) - 1)
            state["force_render"] = True
            state["updated"] = True
            if 0 < state["v2_history_offset"] <= len(state["v2_history_buffer"]):
                snapshot = state["v2_history_buffer"][-(state["v2_history_offset"] + 1)]
                state["status_message"] = f"Viewing {int(time.time() - snapshot['timestamp'])}s ago"

    def _handle_history_next() -> None:
        if state["v2_history_offset"] > 0:
            page_step, state["cached_page_step"], state["last_term_size"] = get_cached_page_step(
                state["cached_page_step"],
                state["last_term_size"],
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
                pulse_position=state["pulse_position"],
            )
            state["v2_history_offset"] = max(0, state["v2_history_offset"] - page_step)
            state["force_render"] = True
            state["updated"] = True
            if state["v2_history_offset"] == 0:
                state["status_message"] = "Returned to LIVE view"
            else:
                if 0 < state["v2_history_offset"] <= len(state["v2_history_buffer"]):
                    snapshot = state["v2_history_buffer"][-(state["v2_history_offset"] + 1)]
                    state["status_message"] = f"Viewing {int(time.time() - snapshot['timestamp'])}s ago"

    def _handle_host_scroll(delta: int) -> None:
        scroll_buffers = state["render_buffers"]
        scroll_stats = state["render_stats"]
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
            summary_mode=state["summary_modes"][state["summary_mode_index"]],
            summary_scope=state["summary_scope_modes"][state["summary_scope_mode_index"]],
            group_by=state["group_by_modes"][state["group_by_mode_index"]],
            group_sort_enabled=state["summary_scope_modes"][state["summary_scope_mode_index"]] == "group",
            pulse_position=state["pulse_position"],
        )
        if delta < 0 and state["host_scroll_offset"] > 0 and total_hosts > 0:
            state["host_scroll_offset"] = max(0, state["host_scroll_offset"] - 1)
            end_index = min(state["host_scroll_offset"] + visible_hosts, total_hosts)
            state["status_message"] = f"Hosts {state['host_scroll_offset'] + 1}-{end_index} of {total_hosts}"
            state["force_render"] = True
            state["updated"] = True
        elif delta > 0 and state["host_scroll_offset"] < max_offset and total_hosts > 0:
            state["host_scroll_offset"] = min(max_offset, state["host_scroll_offset"] + 1)
            end_index = min(state["host_scroll_offset"] + visible_hosts, total_hosts)
            state["status_message"] = f"Hosts {state['host_scroll_offset'] + 1}-{end_index} of {total_hosts}"
            state["force_render"] = True
            state["updated"] = True

    def _handle_host_select_open() -> None:
        state["host_select_active"] = True
        state["host_select_index"] = 0
        state["force_render"] = True
        state["updated"] = True

    action_handlers = {
        "reload_hosts": _handle_reload,
        "force_redraw": _handle_force_redraw,
        "display_name_cycle": _handle_display_mode_cycle,
        "display_view_cycle": _handle_view_cycle,
        "kitt_toggle": _handle_kitt_toggle,
        "kitt_style_cycle": _handle_kitt_style_cycle,
        "sort_cycle": _handle_sort_cycle,
        "filter_cycle": _handle_filter_cycle,
        "asn_toggle": _handle_asn_toggle,
        "summary_info_cycle": _handle_summary_mode_cycle,
        "summary_scope_cycle": _handle_summary_scope_cycle,
        "group_key_cycle": _handle_group_key_cycle,
        "color_toggle": _handle_color_toggle,
        "bell_toggle": _handle_bell_toggle,
        "summary_fullscreen_toggle": _handle_summary_fullscreen_toggle,
        "panel_toggle": _handle_panel_toggle,
        "panel_position_cycle": _handle_panel_position_cycle,
        "pulse_panel_toggle": _handle_pulse_panel_toggle,
        "pulse_panel_position_cycle": _handle_pulse_panel_position_cycle,
        "display_pause_toggle": _handle_display_pause_toggle,
        "dormant_toggle": _handle_dormant_toggle,
        "snapshot_save": _handle_snapshot_save,
        "history_prev": _handle_history_prev,
        "history_next": _handle_history_next,
        "host_select_open": _handle_host_select_open,
        "host_scroll_up": lambda: _handle_host_scroll(-1),
        "host_scroll_down": lambda: _handle_host_scroll(1),
    }
    handler = action_handlers.get(action)
    if handler is not None:
        handler()
    return skip_iteration


def _update_render_state(state: Dict[str, Any]) -> None:
    """Update DNS/ASN/ping data, maintain history snapshots, and resolve current render state."""
    _check_terminal_resize_and_request_redraw(state, time.monotonic())

    runtime_timeline_width = _compute_runtime_timeline_width(state, get_terminal_size(fallback=(80, 24)))
    if state["v2_state"].resize_timeline_width(runtime_timeline_width):
        state["updated"] = True
        state["force_render"] = True

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
        if not any(info.get("active", True) for info in infos):
            continue
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
            state["done_host_ids"].add(host_id)
            continue

        status = result["status"]
        apply_shadow_v2_event(state["v2_state"], result, status, host_id)
        if should_flash_on_fail(status, state["flash_on_fail"], state["show_help"]):
            flash_screen()
        if status == "fail" and state["bell_on_fail"] and not state["show_help"]:
            ring_bell()
        if not state["paused"]:
            state["updated"] = True

    now = time.time()
    state["v2_last_snapshot_time"], state["v2_history_offset"] = update_history_buffer_v2(
        state["v2_history_buffer"],
        state["v2_state"],
        now,
        state["v2_last_snapshot_time"],
        state["v2_history_offset"],
    )
    render_v2_state, state["render_paused"], state["render_snapshot_timestamp"] = resolve_v2_render_state(
        state["v2_history_offset"],
        state["v2_history_buffer"],
        state["v2_state"],
        state["paused"],
    )
    state["render_buffers"], state["render_stats"] = project_legacy_state_from_v2(render_v2_state, state["symbols"])
    _purge_expired_removed_hosts(state)


def _render_frame(args: argparse.Namespace, state: Dict[str, Any]) -> None:
    """Render a frame when needed based on update and refresh timing state."""
    now = time.time()
    refresh_interval = 0.05 if state["kitt_mode_enabled"] else state["refresh_interval"]
    should_render = state["force_render"] or (
        not state["paused"] and (state["updated"] or (now - state["last_render"]) >= refresh_interval)
    )
    if not should_render:
        return
    display_timestamp = format_timestamp(datetime.now(timezone.utc), state["display_tz"])
    snapshot_timestamp = state.get("render_snapshot_timestamp")
    if snapshot_timestamp is not None:
        snapshot_dt = datetime.fromtimestamp(snapshot_timestamp, timezone.utc)
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
        summary_mode=state["summary_modes"][state["summary_mode_index"]],
        summary_scope=state["summary_scope_modes"][state["summary_scope_mode_index"]],
        group_by=state["group_by_modes"][state["group_by_mode_index"]],
        group_sort_enabled=state["summary_scope_modes"][state["summary_scope_mode_index"]] == "group",
        pulse_position=state["pulse_position"],
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
            group_by=state["group_by_modes"][state["group_by_mode_index"]],
            group_sort_enabled=state["summary_scope_modes"][state["summary_scope_mode_index"]] == "group",
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
        host_info_by_id = {info["id"]: info for info in state["host_infos"]}
        fallback_label = host_info_by_id.get(state["graph_host_id"], {}).get("alias", "unknown-host")
        host_label = display_names.get(state["graph_host_id"], fallback_label)
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
        summary_scope=state["summary_scope_modes"][state["summary_scope_mode_index"]],
        group_by=state["group_by_modes"][state["group_by_mode_index"]],
        group_sort_enabled=state["summary_scope_modes"][state["summary_scope_mode_index"]] == "group",
        kitt_mode_enabled=state["kitt_mode_enabled"],
        kitt_style=state["kitt_style_modes"][state["kitt_style_index"]],
        pulse_position=state["pulse_position"],
    )
    state["last_render"] = now
    state["updated"] = False
    state["force_render"] = False


def run(args: argparse.Namespace) -> None:
    """Run the ParaPing monitor with parsed arguments."""
    _configure_logging(
        getattr(args, "log_level", "INFO"),
        getattr(args, "log_file", None),
        interactive_ui=sys.stdout.isatty(),
        verbose_ui_errors=getattr(args, "ui_log_errors", False),
    )
    setup = _setup_hosts_and_state(args)
    if setup is None:
        return

    count_label = "infinite" if args.count == 0 else str(args.count)
    print(
        f"ParaPing - Pinging {len(setup['all_hosts'])} host(s) with timeout={args.timeout}s, "
        f"count={count_label}, interval={args.interval}s, slow-threshold={args.slow_threshold}s"
    )
    initial_render_buffers, initial_render_stats = project_legacy_state_from_v2(setup["v2_state"], setup["symbols"])
    initial_term_size = get_terminal_size(fallback=(80, 24))
    now_monotonic = time.monotonic()
    modes = ["ip", "rdns", "alias"]
    display_modes = ["timeline", "sparkline", "square"]
    summary_modes = ["rates", "rtt", "ttl", "streak"]
    summary_scope_modes = ["host", "group"]
    sort_modes = ["config", "failures", "streak", "latency", "host"]
    filter_modes = ["failures", "latency", "all"]
    kitt_style_modes = ["scanner", "gradient"]
    arg_values = vars(args) if hasattr(args, "__dict__") else {}
    initial_display_name = arg_values.get("display_name", "alias")
    initial_view = arg_values.get("view", "timeline")
    initial_summary_mode = arg_values.get("summary_mode", "rates")
    initial_summary_scope = arg_values.get("summary_scope", "host")
    initial_sort = arg_values.get("sort", "config")
    initial_filter = arg_values.get("filter", "all")
    initial_kitt_style = arg_values.get("kitt_style", "scanner")
    state = {
        **setup,
        "modes": modes,
        "mode_index": modes.index(initial_display_name) if initial_display_name in modes else 2,
        "show_help": False,
        "display_modes": display_modes,
        "display_mode_index": display_modes.index(initial_view) if initial_view in display_modes else 0,
        "summary_modes": summary_modes,
        "summary_mode_index": summary_modes.index(initial_summary_mode) if initial_summary_mode in summary_modes else 0,
        "summary_scope_modes": summary_scope_modes,
        "summary_scope_mode_index": (
            summary_scope_modes.index(initial_summary_scope) if initial_summary_scope in summary_scope_modes else 0
        ),
        "group_by_modes": _build_group_by_modes(setup["host_infos"]),
        "group_by_mode_index": 0,
        "kitt_mode_enabled": bool(arg_values.get("kitt", False)),
        "kitt_style_modes": kitt_style_modes,
        "kitt_style_index": kitt_style_modes.index(initial_kitt_style) if initial_kitt_style in kitt_style_modes else 0,
        "summary_fullscreen": bool(arg_values.get("summary_fullscreen", False)),
        "sort_modes": sort_modes,
        "sort_mode_index": sort_modes.index(initial_sort) if initial_sort in sort_modes else 0,
        "filter_modes": filter_modes,
        "filter_mode_index": filter_modes.index(initial_filter) if initial_filter in filter_modes else 2,
        "running": True,
        "paused": False,
        "dormant": False,
        "display_paused": False,
        "pause_mode": args.pause_mode,
        "pause_event": threading.Event(),
        "stop_event": threading.Event(),
        "status_message": None,
        "force_render": False,
        "show_asn": bool(arg_values.get("show_asn", True)),
        "color_supported": sys.stdout.isatty(),
        "use_color": args.color and sys.stdout.isatty(),
        "flash_on_fail": getattr(args, "flash_on_fail", False),
        "bell_on_fail": getattr(args, "bell_on_fail", False),
        "asn_cache": {},
        "asn_failure_ttl": 300.0,
        "host_select_active": False,
        "host_select_index": 0,
        "graph_host_id": None,
        "v2_history_buffer": deque(maxlen=int(HISTORY_DURATION_MINUTES * 60 / SNAPSHOT_INTERVAL_SECONDS)),
        "v2_history_offset": 0,
        "v2_last_snapshot_time": 0.0,
        "cached_page_step": None,
        "last_term_size": None,
        "host_scroll_offset": 0,
        "render_buffers": initial_render_buffers,
        "render_stats": initial_render_stats,
        "render_snapshot_timestamp": None,
        "render_paused": False,
        "done_host_ids": set(),
        "worker_threads": {},
        "next_host_id": (max((info["id"] for info in setup["host_infos"]), default=-1) + 1),
        "updated": True,
        "last_render": 0.0,
        "refresh_interval": 0.10,
        "last_observed_term_size": initial_term_size,
        "next_resize_check_time": now_monotonic + 1.0,
        "resize_check_interval": 1.0,
        "expect_completion": args.count > 0,
        "rdns_request_queue": queue.Queue(),
        "rdns_result_queue": queue.Queue(),
        "asn_request_queue": queue.Queue(),
        "asn_result_queue": queue.Queue(),
        "worker_stop": threading.Event(),
    }
    initial_group_by = getattr(args, "group_by", "none")
    _sync_group_by_modes(state, preferred_group_by=initial_group_by)
    for info in state["host_infos"]:
        info.setdefault("active", True)
        info.setdefault("removed", False)
        info.setdefault("retired_until", None)
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
        _start_host_worker(info, args, state, scheduler, ping_lock, sequence_tracker)

    try:
        if stdin_fd is not None:
            tty.setcbreak(stdin_fd)
        while state["running"] and (not state["expect_completion"] or not _all_active_hosts_completed(state)):
            key = read_key()
            if key and _handle_user_input(key, args, state, scheduler, ping_lock, sequence_tracker):
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
        for thread in state["worker_threads"].values():
            thread.join(timeout=1.0)
        if stdin_fd is not None and original_term is not None:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, original_term)

    prepare_terminal_for_exit()
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for info in state["host_infos"]:
        if not info.get("active", True):
            continue
        host_id = info["id"]
        host_stats = state["v2_state"].stats[host_id]
        success = host_stats.success
        slow = host_stats.slow
        fail = host_stats.fail
        total = host_stats.total
        percentage = (success / total * 100) if total > 0 else 0
        status = "OK" if success > 0 else "FAILED"
        print(f"{info['alias']:30} {success}/{total} replies, {slow} slow, {fail} failed " f"({percentage:.1f}%) [{status}]")


def main() -> None:
    """Main entrypoint for the CLI - parses arguments and runs the application."""
    args = handle_options()
    run(args)
