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

"""CLI grouping mode helpers."""

from typing import Any, Dict, List, Optional


def count_entry_tags(host_info: Dict[str, Any]) -> int:
    """Count non-empty tag values in one host record."""
    tags = host_info.get("tags") or []
    if not isinstance(tags, list):
        tags = [tags]
    return sum(1 for tag in tags if str(tag).strip())


def build_group_by_modes(host_infos: List[Dict[str, Any]]) -> List[str]:
    """Build group-key cycle modes, including tagN and hierarchical modes."""
    max_tag_count = max((count_entry_tags(info) for info in host_infos), default=0)
    tag_count = max(1, max_tag_count)
    tag_modes = [f"tag{index}" for index in range(1, tag_count + 1)]
    return ["none", "asn", "site", *tag_modes, "site>tag1", "tag1>site"]


def sync_group_by_modes(state: Dict[str, Any], preferred_group_by: Optional[str] = None) -> None:
    """Refresh group-key modes from host data while preserving the current selection."""
    current_group_by = preferred_group_by
    if current_group_by is None:
        modes = state.get("group_by_modes") or []
        mode_index = int(state.get("group_by_mode_index", 0))
        if modes:
            current_group_by = str(modes[mode_index % len(modes)])
    if current_group_by == "tag":
        current_group_by = "tag1"

    modes = build_group_by_modes(state.get("host_infos", []))
    state["group_by_modes"] = modes
    if current_group_by in modes:
        state["group_by_mode_index"] = modes.index(current_group_by)
    else:
        state["group_by_mode_index"] = 0
