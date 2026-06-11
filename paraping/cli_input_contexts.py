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

"""Context-specific keyboard handlers for the ParaPing CLI."""

from argparse import Namespace
from typing import Any, Dict, List, Tuple

from paraping.keymap import KeyContext
from paraping.ui_render import build_display_entries, build_display_names, get_terminal_size, should_show_asn


def resolve_input_context(state: Dict[str, Any]) -> KeyContext:
    """Resolve the active keyboard context from CLI state."""
    if state.get("show_help"):
        return "help"
    if state.get("host_select_active"):
        return "host_select"
    if state.get("graph_host_id") is not None:
        return "graph"
    return "main"


def handle_help_context(action: str, state: Dict[str, Any]) -> bool:
    """Handle keyboard actions while the help view is open."""
    if action in ("help_toggle", "back"):
        state["show_help"] = False
        mark_updated(state, force_render=True)
        return True
    return False


def handle_host_select_context(action: str, args: Namespace, state: Dict[str, Any]) -> bool:
    """Handle keyboard actions while the host selection view is open."""
    display_entries = build_host_select_entries(args, state)
    if not display_entries:
        state["host_select_index"] = 0
    else:
        state["host_select_index"] = min(max(state["host_select_index"], 0), len(display_entries) - 1)

    if action == "select_prev" and display_entries:
        state["host_select_index"] = max(0, state["host_select_index"] - 1)
        mark_updated(state, force_render=True)
    elif action == "select_next" and display_entries:
        state["host_select_index"] = min(len(display_entries) - 1, state["host_select_index"] + 1)
        mark_updated(state, force_render=True)
    elif action == "select_confirm":
        if display_entries:
            state["graph_host_id"] = display_entries[state["host_select_index"]][0]
            state["host_select_active"] = False
            mark_updated(state, force_render=True)
    elif action == "back":
        state["host_select_active"] = False
        mark_updated(state, force_render=True)

    return bool(action)


def build_host_select_entries(args: Namespace, state: Dict[str, Any]) -> List[Tuple[int, str]]:
    """Build display entries for host selection from the current render projection."""
    term_size = get_terminal_size(fallback=(80, 24))
    mode_label = state["modes"][state["mode_index"]]
    include_asn = should_show_asn(
        state["host_infos"],
        mode_label,
        state["show_asn"],
        term_size.columns,
    )
    display_names = build_display_names(
        state["host_infos"],
        mode_label,
        include_asn,
        asn_width=8,
    )
    return build_display_entries(
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


def handle_graph_context(action: str, state: Dict[str, Any]) -> bool:
    """Handle keyboard actions while the fullscreen graph view is open."""
    if action == "back":
        state["graph_host_id"] = None
        mark_updated(state, force_render=True)
        return True
    if action == "host_select_open":
        state["host_select_active"] = True
        state["graph_host_id"] = None
        mark_updated(state, force_render=True)
        return True
    if action == "graph_toggle":
        state["display_mode_index"] = (state["display_mode_index"] + 1) % len(state["display_modes"])
        mark_updated(state)
    return False


def mark_updated(state: Dict[str, Any], *, force_render: bool = False) -> None:
    """Mark state as changed, optionally requiring a full render pass."""
    if force_render:
        state["force_render"] = True
    state["updated"] = True
