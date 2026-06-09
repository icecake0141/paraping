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

"""Runtime state helpers for the ParaPing CLI."""

import logging
import os
from typing import Any, Callable, Dict, Optional

from paraping.runtime.rate_limit import validate_global_rate_limit


def build_runtime_config_overrides(state: Dict[str, Any]) -> Dict[str, Any]:
    """Collect the current state that should persist across launches."""
    return {
        "display_name": state["modes"][state["mode_index"]],
        "view": state["display_modes"][state["display_mode_index"]],
        "sort": state["sort_modes"][state["sort_mode_index"]],
        "filter": state["filter_modes"][state["filter_mode_index"]],
        "show_asn": bool(state["show_asn"]),
        "summary_mode": state["summary_modes"][state["summary_mode_index"]],
        "summary_scope": state["summary_scope_modes"][state["summary_scope_mode_index"]],
        "group_by": state["group_by_modes"][state["group_by_mode_index"]],
        "panel_position": state["panel_position"],
        "color": bool(state["use_color"]),
        "bell_on_fail": bool(state["bell_on_fail"]),
        "kitt": bool(state["kitt_mode_enabled"]),
        "kitt_style": state["kitt_style_modes"][state["kitt_style_index"]],
        "summary_fullscreen": bool(state["summary_fullscreen"]),
    }


def check_terminal_resize_and_request_redraw(
    state: Dict[str, Any],
    now_monotonic: float,
    get_terminal_size_func: Callable[..., Any],
    normalize_term_size: Callable[[Any], Any],
    reset_render_cache_func: Callable[[], None],
) -> None:
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

    current_size = normalize_term_size(get_terminal_size_func(fallback=(80, 24)))
    previous_size = normalize_term_size(state.get("last_observed_term_size"))
    state["last_observed_term_size"] = current_size

    if current_size is None or previous_size is None:
        return
    if current_size.columns == previous_size.columns and current_size.lines == previous_size.lines:
        return

    # Match hotkey `u` behavior for resize recovery.
    reset_render_cache_func()
    state["cached_page_step"] = None
    state["last_term_size"] = None
    state["force_render"] = True
    state["updated"] = True


def compute_scheduler_stagger(interval_seconds: float, host_count: int) -> float:
    """Compute per-host stagger for the current host count."""
    return interval_seconds / host_count if host_count > 0 else 0.0


def round_interval_seconds(interval_seconds: float) -> float:
    """Round interval updates to one decimal place for stable hotkey stepping."""
    return round(interval_seconds + 1e-9, 1)


def update_runtime_interval(
    state: Dict[str, Any],
    scheduler: Any,
    ping_lock: Any,
    next_interval_seconds: float,
    active_host_count_func: Callable[[Dict[str, Any]], int],
    now_func: Callable[[], float],
    min_interval_seconds: float,
    max_interval_seconds: float,
) -> str:
    """Apply a runtime interval update when it passes bounds and rate-limit validation."""
    rounded_interval = round_interval_seconds(next_interval_seconds)
    current_interval = float(state.get("interval_seconds", rounded_interval))
    if rounded_interval < min_interval_seconds or rounded_interval > max_interval_seconds:
        return f"Interval unchanged: {current_interval:.1f}s"

    active_host_count = active_host_count_func(state)
    is_valid, _rate, error_message = validate_global_rate_limit(active_host_count, rounded_interval)
    if not is_valid:
        return f"Interval change rejected: {error_message}"

    with ping_lock:
        scheduler.set_interval(rounded_interval)
        scheduler.set_stagger(compute_scheduler_stagger(rounded_interval, scheduler.get_host_count()))
        scheduler.reset_timing(now_func())

    state["interval_seconds"] = rounded_interval
    return f"Interval: {rounded_interval:.1f}s"


def configure_logging(
    log_level: str,
    log_file: Optional[str],
    interactive_ui: bool = False,
    verbose_ui_errors: bool = False,
    logging_module: Any = logging,
) -> None:
    """Configure logging handlers for CLI execution."""
    handlers: list[logging.Handler] = []
    # Avoid polluting the live TUI with asynchronous log lines.
    if (not interactive_ui) or verbose_ui_errors:
        handlers.append(logging_module.StreamHandler())
    if log_file:
        handlers.append(logging_module.FileHandler(os.path.expanduser(log_file), encoding="utf-8"))
    if not handlers:
        handlers.append(logging_module.NullHandler())
    logging_module.basicConfig(
        level=getattr(logging_module, log_level, logging_module.INFO),
        format="%(message)s",
        handlers=handlers,
        force=True,
    )
