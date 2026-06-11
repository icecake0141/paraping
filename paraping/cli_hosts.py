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

"""Host state helpers for the ParaPing CLI."""

from typing import Any, Callable, Dict, List

from paraping.types import HostInfo


def rebuild_host_info_map(host_infos: List[HostInfo]) -> Dict[str, List[HostInfo]]:
    """Rebuild host-to-info mapping for DNS/ASN updates."""
    host_info_map: Dict[str, List[HostInfo]] = {}
    for info in host_infos:
        host_info_map.setdefault(info["host"], []).append(info)
    return host_info_map


def build_host_info_from_entry(entry: Dict[str, Any], host_id: int) -> HostInfo:
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


def active_host_count(state: Dict[str, Any]) -> int:
    """Count active hosts currently monitored by scheduler workers."""
    return sum(1 for info in state["host_infos"] if info.get("active", True))


def all_active_hosts_completed(state: Dict[str, Any]) -> bool:
    """Check whether all active hosts have emitted completion markers."""
    active_ids = {info["id"] for info in state["host_infos"] if info.get("active", True)}
    return active_ids.issubset(state["done_host_ids"])


def purge_expired_removed_hosts(
    state: Dict[str, Any],
    now: float,
    sync_group_by_modes: Callable[[Dict[str, Any]], None],
) -> None:
    """Permanently remove hosts after retirement window expires."""
    remaining_infos: List[HostInfo] = []
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
        state["monitor_state"].remove_host(host_id)
        state["worker_threads"].pop(host_id, None)
        state["done_host_ids"].discard(host_id)
        if state.get("graph_host_id") == host_id:
            state["graph_host_id"] = None
    state["host_info_map"] = rebuild_host_info_map(state["host_infos"])
    sync_group_by_modes(state)
    state["cached_page_step"] = None
    state["updated"] = True
