# Copyright 2026 icecake0141
# SPDX-License-Identifier: Apache-2.0

"""Centralized hotkey definitions and helpers for ParaPing."""

from typing import Dict, Iterable, List, Literal, Mapping, Optional, Sequence, Tuple

KeyContext = Literal["main", "help", "host_select", "graph"]

KEYMAPS: Dict[str, Dict[str, str]] = {
    "global": {
        "q": "quit",
        "?": "help_toggle",
    },
    "main": {
        "d": "display_name_cycle",
        "v": "display_view_cycle",
        "x": "host_select_open",
        "j": "host_scroll_down",
        "k": "host_scroll_up",
        "h": "history_prev",
        "l": "history_next",
        "arrow_down": "host_scroll_down",
        "arrow_up": "host_scroll_up",
        "arrow_left": "history_prev",
        "arrow_right": "history_next",
        "r": "reload_hosts",
        "s": "snapshot_save",
        "S": "settings_save",
        "u": "force_redraw",
        "o": "sort_cycle",
        "f": "filter_cycle",
        "a": "asn_toggle",
        "i": "summary_info_cycle",
        "g": "summary_scope_cycle",
        "t": "group_key_cycle",
        "w": "panel_toggle",
        "e": "panel_position_cycle",
        "n": "pulse_panel_toggle",
        "N": "pulse_panel_position_cycle",
        "z": "summary_fullscreen_toggle",
        "c": "color_toggle",
        "b": "bell_toggle",
        "p": "display_pause_toggle",
        "P": "dormant_toggle",
        # NOTE: conflicts with vim-style navigation; use y/Y for Pulse mode.
        "y": "kitt_toggle",
        "Y": "kitt_style_cycle",
    },
    "help": {
        "?": "help_toggle",
        "\x1b": "back",
    },
    "host_select": {
        "j": "select_next",
        "k": "select_prev",
        "arrow_down": "select_next",
        "arrow_up": "select_prev",
        "\r": "select_confirm",
        "\n": "select_confirm",
        "\x1b": "back",
    },
    "graph": {
        "v": "graph_toggle",
        "x": "host_select_open",
        "\x1b": "back",
    },
}

ACTION_METADATA: Dict[str, Dict[str, str]] = {
    "help_toggle": {"label": "toggle help", "category": "global"},
    "back": {"label": "go back", "category": "global"},
    "quit": {"label": "quit", "category": "global"},
    "display_name_cycle": {"label": "cycle display mode (ip/rdns/alias)", "category": "main"},
    "display_view_cycle": {"label": "cycle view (timeline/sparkline/square)", "category": "main"},
    "host_select_open": {"label": "select host for fullscreen RTT graph", "category": "main"},
    "history_prev": {"label": "history page previous", "category": "main"},
    "history_next": {"label": "history page next", "category": "main"},
    "host_scroll_up": {"label": "host list scroll up", "category": "main"},
    "host_scroll_down": {"label": "host list scroll down", "category": "main"},
    "reload_hosts": {"label": "reload hosts", "category": "main"},
    "snapshot_save": {"label": "save snapshot", "category": "main"},
    "settings_save": {"label": "save current settings", "category": "main"},
    "force_redraw": {"label": "force full redraw", "category": "main"},
    "sort_cycle": {"label": "cycle sort", "category": "data"},
    "filter_cycle": {"label": "cycle filter", "category": "data"},
    "asn_toggle": {"label": "toggle ASN display", "category": "data"},
    "summary_info_cycle": {"label": "cycle summary info (rates/rtt/ttl/streak)", "category": "data"},
    "summary_scope_cycle": {"label": "cycle summary scope (host/group)", "category": "data"},
    "group_key_cycle": {"label": "cycle group key", "category": "data"},
    "panel_toggle": {"label": "toggle summary panel", "category": "layout"},
    "panel_position_cycle": {"label": "cycle summary panel position", "category": "layout"},
    "pulse_panel_toggle": {"label": "toggle Pulse panel", "category": "layout"},
    "pulse_panel_position_cycle": {"label": "cycle Pulse panel position", "category": "layout"},
    "summary_fullscreen_toggle": {"label": "toggle summary fullscreen view", "category": "layout"},
    "color_toggle": {"label": "toggle color output", "category": "layout"},
    "bell_toggle": {"label": "toggle bell on ping failure", "category": "layout"},
    "display_pause_toggle": {"label": "toggle display pause", "category": "runtime"},
    "dormant_toggle": {"label": "toggle Dormant Mode", "category": "runtime"},
    "kitt_toggle": {"label": "toggle Pulse mode", "category": "effects"},
    "kitt_style_cycle": {"label": "cycle Pulse style (scanner/gradient)", "category": "effects"},
    "select_prev": {"label": "move selection up", "category": "selection"},
    "select_next": {"label": "move selection down", "category": "selection"},
    "select_confirm": {"label": "confirm selected host", "category": "selection"},
    "graph_toggle": {"label": "toggle graph style (line/bar)", "category": "graph"},
}

HELP_ACTION_GROUPS: Sequence[Tuple[str, Sequence[Tuple[str, Sequence[str]]]]] = (
    (
        "Global",
        (
            ("help_toggle", ("global",)),
            ("quit", ("global",)),
            ("back", ("help", "host_select", "graph")),
        ),
    ),
    (
        "Main",
        (
            ("display_name_cycle", ("main",)),
            ("display_view_cycle", ("main",)),
            ("host_select_open", ("main", "graph")),
            ("history_prev", ("main",)),
            ("history_next", ("main",)),
            ("host_scroll_up", ("main",)),
            ("host_scroll_down", ("main",)),
            ("reload_hosts", ("main",)),
            ("snapshot_save", ("main",)),
            ("settings_save", ("main",)),
            ("force_redraw", ("main",)),
        ),
    ),
    (
        "Data",
        (
            ("sort_cycle", ("main",)),
            ("filter_cycle", ("main",)),
            ("asn_toggle", ("main",)),
            ("summary_info_cycle", ("main",)),
            ("summary_scope_cycle", ("main",)),
            ("group_key_cycle", ("main",)),
        ),
    ),
    (
        "Layout",
        (
            ("panel_toggle", ("main",)),
            ("panel_position_cycle", ("main",)),
            ("pulse_panel_toggle", ("main",)),
            ("pulse_panel_position_cycle", ("main",)),
            ("summary_fullscreen_toggle", ("main",)),
            ("color_toggle", ("main",)),
            ("bell_toggle", ("main",)),
        ),
    ),
    (
        "Runtime/FX",
        (
            ("display_pause_toggle", ("main",)),
            ("dormant_toggle", ("main",)),
            ("kitt_toggle", ("main",)),
            ("kitt_style_cycle", ("main",)),
        ),
    ),
    (
        "Host Select",
        (
            ("select_prev", ("host_select",)),
            ("select_next", ("host_select",)),
            ("select_confirm", ("host_select",)),
            ("back", ("host_select",)),
        ),
    ),
    (
        "Graph",
        (
            ("graph_toggle", ("graph",)),
            ("host_select_open", ("graph",)),
            ("back", ("graph",)),
        ),
    ),
)

_KEY_LABELS: Mapping[str, str] = {
    "arrow_up": "↑",
    "arrow_down": "↓",
    "arrow_left": "←",
    "arrow_right": "→",
    "\x1b": "Esc",
    "\r": "Enter",
    "\n": "Enter",
}


def resolve_action(key: str, context: KeyContext) -> Optional[str]:
    """Resolve a key press to one action in the given context."""
    global_map = KEYMAPS.get("global", {})
    if key in global_map:
        return global_map[key]
    return KEYMAPS.get(context, {}).get(key)


def keys_for_action(action: str, contexts: Iterable[str]) -> List[str]:
    """Return unique keys that trigger an action in the specified contexts."""
    ordered: List[str] = []
    for context in contexts:
        mapping = KEYMAPS.get(context, {})
        for key, mapped_action in mapping.items():
            if mapped_action != action:
                continue
            if key == "\n" and "\r" in ordered:
                continue
            if key not in ordered:
                ordered.append(key)
    return ordered


def format_key_label(key: str) -> str:
    """Convert internal key names to user-facing labels."""
    return _KEY_LABELS.get(key, key)


def format_key_combo(keys: Sequence[str]) -> str:
    """Format key labels for help display."""
    return "/".join(format_key_label(key) for key in keys)


def build_help_items() -> List[str]:
    """Build user-facing help items from centralized key metadata."""
    lines: List[str] = []
    for section_name, items in HELP_ACTION_GROUPS:
        lines.append(f"[{section_name}]")
        for action, contexts in items:
            action_keys = keys_for_action(action, contexts)
            label = ACTION_METADATA.get(action, {}).get("label", action)
            if action_keys:
                lines.append(f"  {format_key_combo(action_keys)}: {label}")
            else:
                lines.append(f"  -: {label}")
    return lines


def find_key_conflicts() -> Dict[str, List[str]]:
    """Find conflicting key assignments per context (for diagnostics/future use)."""
    conflicts: Dict[str, List[str]] = {}
    for context, mapping in KEYMAPS.items():
        seen: Dict[str, str] = {}
        for key, action in mapping.items():
            if key not in seen:
                seen[key] = action
                continue
            conflicts.setdefault(context, []).append(key)
    return conflicts
