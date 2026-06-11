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
from concurrent.futures import ThreadPoolExecutor  # noqa: F401 - tests patch this symbol.
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from paraping import cli_args as _cli_args
from paraping.cli_args import add_option_from_spec, apply_config_to_args, apply_option_defaults
from paraping.cli_frame import build_override_lines, clamp_host_scroll_offset, resolve_display_timestamp, should_render_frame
from paraping.cli_grouping import build_group_by_modes, count_entry_tags, sync_group_by_modes
from paraping.cli_hosts import (
    active_host_count,
    all_active_hosts_completed,
    build_host_info_from_entry,
    purge_expired_removed_hosts,
    rebuild_host_info_map,
)
from paraping.cli_input_contexts import (
    handle_graph_context,
    handle_help_context,
    handle_host_select_context,
    mark_updated,
    resolve_input_context,
)
from paraping.cli_interaction import toggle_display_pause, toggle_dormant_mode
from paraping.cli_render_state import (
    drain_asn_results,
    drain_ping_results,
    drain_rdns_results,
    enqueue_pending_asn_requests,
    update_history_projection,
)
from paraping.cli_runtime import (
    build_runtime_config_overrides,
    check_terminal_resize_and_request_redraw,
    compute_scheduler_stagger,
    configure_logging,
    round_interval_seconds,
    update_runtime_interval,
)
from paraping.cli_setup import setup_hosts_and_state
from paraping.cli_state import build_initial_state
from paraping.config import DEFAULT_CONFIG_PATH, load_config, save_config_overrides
from paraping.core import (
    _normalize_term_size,
    build_host_infos,
    get_cached_page_step,
    read_input_file,
    read_input_file_with_report,
)
from paraping.input_keys import read_key
from paraping.keymap import resolve_action
from paraping.network_asn import asn_worker, should_retry_asn
from paraping.pinger import rdns_worker, scheduler_driven_worker_ping
from paraping.runtime.event_mirror import mirror_ping_event
from paraping.runtime.history import update_history_buffer
from paraping.runtime.render_projection import project_render_state
from paraping.runtime.render_state import resolve_render_state
from paraping.runtime.scheduler import Scheduler
from paraping.runtime.sequence_tracker import SequenceTracker
from paraping.types import HostInfo
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

REMOVED_HOST_RETENTION_SECONDS = 10.0
INTERVAL_STEP_SECONDS = 0.1
MIN_INTERVAL_SECONDS = 0.1
MAX_INTERVAL_SECONDS = 60.0


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

    This is used to keep runtime timeline buffers aligned with runtime terminal
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


_build_runtime_config_overrides = build_runtime_config_overrides


def _check_terminal_resize_and_request_redraw(state: Dict[str, Any], now_monotonic: float) -> None:
    """Periodically detect terminal size changes and request a full redraw."""
    check_terminal_resize_and_request_redraw(
        state,
        now_monotonic,
        get_terminal_size_func=get_terminal_size,
        normalize_term_size=_normalize_term_size,
        reset_render_cache_func=reset_render_cache,
    )


_compute_scheduler_stagger = compute_scheduler_stagger
_round_interval_seconds = round_interval_seconds


def _update_runtime_interval(
    state: Dict[str, Any],
    scheduler: Scheduler,
    ping_lock: threading.Lock,
    next_interval_seconds: float,
) -> str:
    """Apply a runtime interval update when it passes bounds and rate-limit validation."""
    return update_runtime_interval(
        state,
        scheduler,
        ping_lock,
        next_interval_seconds,
        active_host_count_func=_active_host_count,
        now_func=time.time,
        min_interval_seconds=MIN_INTERVAL_SECONDS,
        max_interval_seconds=MAX_INTERVAL_SECONDS,
    )


def _configure_logging(
    log_level: str,
    log_file: Optional[str],
    interactive_ui: bool = False,
    verbose_ui_errors: bool = False,
) -> None:
    """Configure logging handlers for CLI execution."""
    configure_logging(log_level, log_file, interactive_ui, verbose_ui_errors, logging_module=logging)


_add_option_from_spec = add_option_from_spec
_apply_option_defaults = apply_option_defaults
_count_entry_tags = count_entry_tags
_build_group_by_modes = build_group_by_modes
_sync_group_by_modes = sync_group_by_modes
_apply_config_to_args = apply_config_to_args


def handle_options() -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    return _cli_args.handle_options(config_loader=load_config)


def _setup_hosts_and_state(args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    """Parse host input and initialize host/runtime state required by the monitor loop."""
    return setup_hosts_and_state(
        args,
        read_input_file_with_report_func=read_input_file_with_report,
        build_host_infos_func=build_host_infos,
        compute_initial_timeline_width_func=_compute_initial_timeline_width,
        get_terminal_size_func=get_terminal_size,
        os_module=os,
        queue_factory=queue.Queue,
    )


_rebuild_host_info_map = rebuild_host_info_map
_build_host_info_from_entry = build_host_info_from_entry


def _start_host_worker(
    host_info: HostInfo,
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


_active_host_count = active_host_count
_all_active_hosts_completed = all_active_hosts_completed


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
            scheduler.set_stagger(_compute_scheduler_stagger(state["interval_seconds"], host_count))
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
                    scheduler.set_stagger(_compute_scheduler_stagger(state["interval_seconds"], host_count))
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
        state["monitor_state"].add_host(new_info["id"])
        with ping_lock:
            scheduler.add_host(new_info["host"], host_id=new_info["id"])
            host_count = scheduler.get_host_count()
            scheduler.set_stagger(_compute_scheduler_stagger(state["interval_seconds"], host_count))
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
    purge_expired_removed_hosts(state, now=time.time(), sync_group_by_modes=_sync_group_by_modes)


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
    context = resolve_input_context(state)
    action = resolve_action(key, context) or ""

    if action == "quit":
        state["running"] = False
        state["stop_event"].set()
        return skip_iteration

    if context == "help":
        return handle_help_context(action, state)

    if action == "help_toggle":
        state["show_help"] = True
        mark_updated(state, force_render=True)
        return skip_iteration

    if context == "host_select":
        return handle_host_select_context(action, args, state)

    if context == "graph":
        return handle_graph_context(action, state)

    action_handlers: Dict[str, Callable[[], None]] = {}

    def _handle_reload() -> None:
        if scheduler is None or ping_lock is None or sequence_tracker is None:
            state["status_message"] = "Reload unavailable in this context"
        else:
            state["status_message"] = _apply_manual_reload(args, state, scheduler, ping_lock, sequence_tracker)
        mark_updated(state, force_render=True)

    def _handle_force_redraw() -> None:
        reset_render_cache()
        state["status_message"] = "Full redraw requested"
        mark_updated(state, force_render=True)

    def _handle_interval_change(delta_seconds: float) -> None:
        if scheduler is None or ping_lock is None:
            state["status_message"] = "Interval change unavailable in this context"
        else:
            current_interval = float(state.get("interval_seconds", args.interval))
            target_interval = current_interval + delta_seconds
            if delta_seconds < 0:
                target_interval = max(MIN_INTERVAL_SECONDS, target_interval)
            else:
                target_interval = min(MAX_INTERVAL_SECONDS, target_interval)
            state["status_message"] = _update_runtime_interval(state, scheduler, ping_lock, target_interval)
        mark_updated(state, force_render=True)

    def _handle_display_mode_cycle() -> None:
        state["mode_index"] = (state["mode_index"] + 1) % len(state["modes"])
        state["cached_page_step"] = None
        mark_updated(state)

    def _handle_view_cycle() -> None:
        state["display_mode_index"] = (state["display_mode_index"] + 1) % len(state["display_modes"])
        mark_updated(state)

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
        mark_updated(state, force_render=True)

    def _handle_kitt_style_cycle() -> None:
        if state["kitt_mode_enabled"]:
            state["kitt_style_index"] = (state["kitt_style_index"] + 1) % len(state["kitt_style_modes"])
            current_style = state["kitt_style_modes"][state["kitt_style_index"]]
            state["status_message"] = f"Pulse style: {current_style}"
        else:
            state["status_message"] = "Pulse mode is off (press 'y' first)"
        mark_updated(state, force_render=True)

    def _handle_sort_cycle() -> None:
        state["sort_mode_index"] = (state["sort_mode_index"] + 1) % len(state["sort_modes"])
        state["cached_page_step"] = None
        mark_updated(state)

    def _handle_filter_cycle() -> None:
        state["filter_mode_index"] = (state["filter_mode_index"] + 1) % len(state["filter_modes"])
        state["cached_page_step"] = None
        mark_updated(state)

    def _handle_asn_toggle() -> None:
        state["show_asn"] = not state["show_asn"]
        state["cached_page_step"] = None
        mark_updated(state)

    def _handle_summary_mode_cycle() -> None:
        state["summary_mode_index"] = (state["summary_mode_index"] + 1) % len(state["summary_modes"])
        state["status_message"] = f"Summary: {state['summary_modes'][state['summary_mode_index']].upper()}"
        mark_updated(state)

    def _handle_summary_scope_cycle() -> None:
        state["summary_scope_mode_index"] = (state["summary_scope_mode_index"] + 1) % len(state["summary_scope_modes"])
        scope = state["summary_scope_modes"][state["summary_scope_mode_index"]]
        state["status_message"] = f"Summary scope: {scope.upper()}"
        state["cached_page_step"] = None
        mark_updated(state)

    def _handle_group_key_cycle() -> None:
        state["group_by_mode_index"] = (state["group_by_mode_index"] + 1) % len(state["group_by_modes"])
        group_by = state["group_by_modes"][state["group_by_mode_index"]]
        state["status_message"] = f"Group key: {group_by}"
        state["cached_page_step"] = None
        mark_updated(state)

    def _handle_color_toggle() -> None:
        if not state["color_supported"]:
            state["status_message"] = "Color output unavailable (no TTY)"
        else:
            state["use_color"] = not state["use_color"]
            state["status_message"] = "Color output enabled" if state["use_color"] else "Color output disabled"
        mark_updated(state, force_render=True)

    def _handle_bell_toggle() -> None:
        state["bell_on_fail"] = not state["bell_on_fail"]
        state["status_message"] = "Bell on fail enabled" if state["bell_on_fail"] else "Bell on fail disabled"
        mark_updated(state, force_render=True)

    def _handle_summary_fullscreen_toggle() -> None:
        state["summary_fullscreen"] = not state["summary_fullscreen"]
        state["status_message"] = (
            "Summary fullscreen view enabled" if state["summary_fullscreen"] else "Summary fullscreen view disabled"
        )
        mark_updated(state, force_render=True)

    def _handle_panel_toggle() -> None:
        state["panel_position"], state["last_panel_position"] = toggle_panel_visibility(
            state["panel_position"],
            state["last_panel_position"],
            default_position=state["panel_toggle_default"],
        )
        state["status_message"] = "Summary panel hidden" if state["panel_position"] == "none" else "Summary panel shown"
        state["cached_page_step"] = None
        mark_updated(state, force_render=True)

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
        mark_updated(state, force_render=True)

    def _handle_pulse_panel_toggle() -> None:
        state["pulse_position"], state["last_pulse_position"] = toggle_panel_visibility(
            state["pulse_position"],
            state["last_pulse_position"],
            default_position=state["pulse_toggle_default"],
        )
        state["status_message"] = "Pulse panel hidden" if state["pulse_position"] == "none" else "Pulse panel shown"
        state["cached_page_step"] = None
        mark_updated(state, force_render=True)

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
        mark_updated(state, force_render=True)

    def _handle_display_pause_toggle() -> None:
        toggle_display_pause(state)

    def _handle_dormant_toggle() -> None:
        toggle_dormant_mode(state)

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
            interval_seconds=state["interval_seconds"],
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
        mark_updated(state)

    def _handle_settings_save() -> None:
        try:
            save_config_overrides(_build_runtime_config_overrides(state))
        except (ImportError, OSError, ValueError) as exc:
            state["status_message"] = f"Settings save failed: {exc}"
        else:
            state["status_message"] = f"Saved settings: {DEFAULT_CONFIG_PATH}"
        mark_updated(state, force_render=True)

    def _handle_history_prev() -> None:
        if state["history_offset"] < len(state["history_buffer"]) - 1:
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
            state["history_offset"] = min(state["history_offset"] + page_step, len(state["history_buffer"]) - 1)
            mark_updated(state, force_render=True)
            if 0 < state["history_offset"] <= len(state["history_buffer"]):
                snapshot = state["history_buffer"][-(state["history_offset"] + 1)]
                state["status_message"] = f"Viewing {int(time.time() - snapshot['timestamp'])}s ago"

    def _handle_history_next() -> None:
        if state["history_offset"] > 0:
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
            state["history_offset"] = max(0, state["history_offset"] - page_step)
            mark_updated(state, force_render=True)
            if state["history_offset"] == 0:
                state["status_message"] = "Returned to LIVE view"
            else:
                if 0 < state["history_offset"] <= len(state["history_buffer"]):
                    snapshot = state["history_buffer"][-(state["history_offset"] + 1)]
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
            mark_updated(state, force_render=True)
        elif delta > 0 and state["host_scroll_offset"] < max_offset and total_hosts > 0:
            state["host_scroll_offset"] = min(max_offset, state["host_scroll_offset"] + 1)
            end_index = min(state["host_scroll_offset"] + visible_hosts, total_hosts)
            state["status_message"] = f"Hosts {state['host_scroll_offset'] + 1}-{end_index} of {total_hosts}"
            mark_updated(state, force_render=True)

    def _handle_host_select_open() -> None:
        state["host_select_active"] = True
        state["host_select_index"] = 0
        mark_updated(state, force_render=True)

    action_handlers = {
        "reload_hosts": _handle_reload,
        "force_redraw": _handle_force_redraw,
        "interval_decrease": lambda: _handle_interval_change(-INTERVAL_STEP_SECONDS),
        "interval_increase": lambda: _handle_interval_change(INTERVAL_STEP_SECONDS),
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
        "settings_save": _handle_settings_save,
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
    if state["monitor_state"].resize_timeline_width(runtime_timeline_width):
        state["updated"] = True
        state["force_render"] = True

    drain_rdns_results(state)
    drain_asn_results(state, now_func=time.time)

    now = time.time()
    enqueue_pending_asn_requests(state, now, should_retry_asn_func=should_retry_asn)
    drain_ping_results(
        state,
        mirror_ping_event_func=mirror_ping_event,
        should_flash_on_fail_func=should_flash_on_fail,
        flash_screen_func=flash_screen,
        ring_bell_func=ring_bell,
    )

    now = time.time()
    update_history_projection(
        state,
        now,
        update_history_buffer_func=update_history_buffer,
        resolve_render_state_func=resolve_render_state,
        project_render_state_func=project_render_state,
    )
    _purge_expired_removed_hosts(state)


def _render_frame(args: argparse.Namespace, state: Dict[str, Any]) -> None:
    """Render a frame when needed based on update and refresh timing state."""
    now = time.time()
    if not should_render_frame(state, now):
        return
    display_timestamp = resolve_display_timestamp(state, format_timestamp_func=format_timestamp)
    clamp_host_scroll_offset(args, state, compute_host_scroll_bounds_func=compute_host_scroll_bounds)
    term_size = get_terminal_size(fallback=(80, 24))
    override_lines = build_override_lines(
        args,
        state,
        term_size,
        display_timestamp,
        render_help_view_func=render_help_view,
        should_show_asn_func=should_show_asn,
        build_display_names_func=build_display_names,
        build_display_entries_func=build_display_entries,
        render_host_selection_view_func=render_host_selection_view,
        render_fullscreen_rtt_graph_func=render_fullscreen_rtt_graph,
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
        interval_seconds=state["interval_seconds"],
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
    initial_render_buffers, initial_render_stats = project_render_state(setup["monitor_state"], setup["symbols"])
    initial_term_size = get_terminal_size(fallback=(80, 24))
    now_monotonic = time.monotonic()
    stdout_isatty = sys.stdout.isatty()
    state = build_initial_state(
        args,
        setup,
        initial_render_buffers,
        initial_render_stats,
        initial_term_size,
        now_monotonic,
        queue_factory=queue.Queue,
        event_factory=threading.Event,
        stdout_isatty=stdout_isatty,
    )
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
    scheduler = Scheduler(
        interval=state["interval_seconds"],
        stagger=_compute_scheduler_stagger(state["interval_seconds"], num_hosts),
    )
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
        host_stats = state["monitor_state"].stats[host_id]
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
