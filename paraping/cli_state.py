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

"""Initial CLI state construction."""

from collections import deque
from typing import Any, Callable, Dict

from paraping.cli_grouping import build_group_by_modes
from paraping.cli_modes import (
    DISPLAY_NAME_MODES,
    DISPLAY_VIEW_MODES,
    FILTER_MODES,
    KITT_STYLE_MODES,
    SORT_MODES,
    SUMMARY_MODES,
    SUMMARY_SCOPE_MODES,
    resolve_mode_index,
)
from paraping.runtime.constants import HISTORY_DURATION_MINUTES, SNAPSHOT_INTERVAL_SECONDS


def build_initial_state(
    args: Any,
    setup: Dict[str, Any],
    initial_render_buffers: Dict[int, Dict[str, Any]],
    initial_render_stats: Dict[int, Dict[str, Any]],
    initial_term_size: Any,
    now_monotonic: float,
    queue_factory: Callable[[], Any],
    event_factory: Callable[[], Any],
    stdout_isatty: bool,
) -> Dict[str, Any]:
    """Build the monitor state dictionary used by the CLI loop."""
    arg_values = vars(args) if hasattr(args, "__dict__") else {}
    initial_display_name = arg_values.get("display_name", "alias")
    initial_view = arg_values.get("view", "timeline")
    initial_summary_mode = arg_values.get("summary_mode", "rates")
    initial_summary_scope = arg_values.get("summary_scope", "host")
    initial_sort = arg_values.get("sort", "config")
    initial_filter = arg_values.get("filter", "all")
    initial_kitt_style = arg_values.get("kitt_style", "scanner")
    return {
        **setup,
        "modes": DISPLAY_NAME_MODES,
        "mode_index": resolve_mode_index(DISPLAY_NAME_MODES, initial_display_name, default_index=2),
        "show_help": False,
        "display_modes": DISPLAY_VIEW_MODES,
        "display_mode_index": resolve_mode_index(DISPLAY_VIEW_MODES, initial_view),
        "summary_modes": SUMMARY_MODES,
        "summary_mode_index": resolve_mode_index(SUMMARY_MODES, initial_summary_mode),
        "summary_scope_modes": SUMMARY_SCOPE_MODES,
        "summary_scope_mode_index": resolve_mode_index(SUMMARY_SCOPE_MODES, initial_summary_scope),
        "group_by_modes": build_group_by_modes(setup["host_infos"]),
        "group_by_mode_index": 0,
        "kitt_mode_enabled": bool(arg_values.get("kitt", False)),
        "kitt_style_modes": KITT_STYLE_MODES,
        "kitt_style_index": resolve_mode_index(KITT_STYLE_MODES, initial_kitt_style),
        "summary_fullscreen": bool(arg_values.get("summary_fullscreen", False)),
        "sort_modes": SORT_MODES,
        "sort_mode_index": resolve_mode_index(SORT_MODES, initial_sort),
        "filter_modes": FILTER_MODES,
        "filter_mode_index": resolve_mode_index(FILTER_MODES, initial_filter, default_index=2),
        "running": True,
        "paused": False,
        "dormant": False,
        "display_paused": False,
        "pause_mode": args.pause_mode,
        "pause_event": event_factory(),
        "stop_event": event_factory(),
        "status_message": None,
        "force_render": False,
        "show_asn": bool(arg_values.get("show_asn", True)),
        "color_supported": stdout_isatty,
        "use_color": args.color and stdout_isatty,
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
        "render_buffers": initial_render_buffers,
        "render_stats": initial_render_stats,
        "render_snapshot_timestamp": None,
        "render_paused": False,
        "done_host_ids": set(),
        "worker_threads": {},
        "next_host_id": (max((info["id"] for info in setup["host_infos"]), default=-1) + 1),
        "updated": True,
        "interval_seconds": args.interval,
        "last_render": 0.0,
        "refresh_interval": 0.10,
        "last_observed_term_size": initial_term_size,
        "next_resize_check_time": now_monotonic + 1.0,
        "resize_check_interval": 1.0,
        "expect_completion": args.count > 0,
        "rdns_request_queue": queue_factory(),
        "rdns_result_queue": queue_factory(),
        "asn_request_queue": queue_factory(),
        "asn_result_queue": queue_factory(),
        "worker_stop": event_factory(),
    }
