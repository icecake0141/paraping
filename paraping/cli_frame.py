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

"""Frame rendering helpers for the ParaPing CLI."""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


def should_render_frame(state: Dict[str, Any], now: float) -> bool:
    """Return whether a frame should be rendered at the current time."""
    refresh_interval = 0.05 if state["kitt_mode_enabled"] else state["refresh_interval"]
    return bool(
        state["force_render"]
        or (not state["paused"] and (state["updated"] or (now - state["last_render"]) >= refresh_interval))
    )


def resolve_display_timestamp(
    state: Dict[str, Any],
    format_timestamp_func: Callable[[datetime, Any], str],
    now_utc: Optional[datetime] = None,
) -> str:
    """Resolve the timestamp shown in the current frame."""
    timestamp_dt = now_utc or datetime.now(timezone.utc)
    snapshot_timestamp = state.get("render_snapshot_timestamp")
    if snapshot_timestamp is not None:
        timestamp_dt = datetime.fromtimestamp(snapshot_timestamp, timezone.utc)
    return format_timestamp_func(timestamp_dt, state["display_tz"])


def clamp_host_scroll_offset(
    args: Any,
    state: Dict[str, Any],
    compute_host_scroll_bounds_func: Callable[..., Tuple[int, int, int]],
) -> None:
    """Clamp host scroll offset to the current visible host bounds."""
    max_offset, _visible_hosts, _total_hosts = compute_host_scroll_bounds_func(
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


def build_host_selection_override(
    args: Any,
    state: Dict[str, Any],
    term_size: Any,
    should_show_asn_func: Callable[..., bool],
    build_display_names_func: Callable[..., Dict[int, str]],
    build_display_entries_func: Callable[..., Sequence[Tuple[int, str]]],
    render_host_selection_view_func: Callable[..., List[str]],
) -> List[str]:
    """Build the host-selection overlay frame."""
    include_asn = should_show_asn_func(
        state["host_infos"],
        state["modes"][state["mode_index"]],
        state["show_asn"],
        term_size.columns,
    )
    display_names = build_display_names_func(
        state["host_infos"],
        state["modes"][state["mode_index"]],
        include_asn,
        asn_width=8,
    )
    display_entries = build_display_entries_func(
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
    return render_host_selection_view_func(
        display_entries,
        state["host_select_index"],
        term_size.columns,
        term_size.lines,
        state["modes"][state["mode_index"]],
    )


def build_graph_override(
    state: Dict[str, Any],
    term_size: Any,
    display_timestamp: str,
    should_show_asn_func: Callable[..., bool],
    build_display_names_func: Callable[..., Dict[int, str]],
    render_fullscreen_rtt_graph_func: Callable[..., List[str]],
) -> List[str]:
    """Build the fullscreen RTT graph overlay frame."""
    include_asn = should_show_asn_func(
        state["host_infos"],
        state["modes"][state["mode_index"]],
        state["show_asn"],
        term_size.columns,
    )
    display_names = build_display_names_func(
        state["host_infos"],
        state["modes"][state["mode_index"]],
        include_asn,
        asn_width=8,
    )
    host_info_by_id = {info["id"]: info for info in state["host_infos"]}
    fallback_label = host_info_by_id.get(state["graph_host_id"], {}).get("alias", "unknown-host")
    host_label = display_names.get(state["graph_host_id"], fallback_label)
    return render_fullscreen_rtt_graph_func(
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


def build_override_lines(
    args: Any,
    state: Dict[str, Any],
    term_size: Any,
    display_timestamp: str,
    render_help_view_func: Callable[..., List[str]],
    should_show_asn_func: Callable[..., bool],
    build_display_names_func: Callable[..., Dict[int, str]],
    build_display_entries_func: Callable[..., Sequence[Tuple[int, str]]],
    render_host_selection_view_func: Callable[..., List[str]],
    render_fullscreen_rtt_graph_func: Callable[..., List[str]],
) -> Optional[List[str]]:
    """Build any fullscreen override view for the current frame."""
    if state["show_help"]:
        return render_help_view_func(term_size.columns, term_size.lines)
    if state["host_select_active"]:
        return build_host_selection_override(
            args,
            state,
            term_size,
            should_show_asn_func,
            build_display_names_func,
            build_display_entries_func,
            render_host_selection_view_func,
        )
    if state["graph_host_id"] is not None:
        return build_graph_override(
            state,
            term_size,
            display_timestamp,
            should_show_asn_func,
            build_display_names_func,
            render_fullscreen_rtt_graph_func,
        )
    return None
