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

"""Summary source preparation for ParaPing UI rendering."""

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from paraping.stats import compute_group_summary_data, compute_summary_data, resolve_group_labels, resolve_primary_group_label
from paraping.types import HostInfo


@dataclass(frozen=True)
class SummarySources:
    """Prepared host and summary data for display rendering."""

    active_host_infos: List[HostInfo]
    host_group_labels: Dict[int, str]
    host_tree_labels: Dict[int, str]
    ordered_host_ids: List[int]
    summary_data: List[Dict[str, Any]]
    group_summary_data: List[Dict[str, Any]]
    summary_source: List[Dict[str, Any]]
    kitt_total_hosts: int
    kitt_error_hosts: int


def prepare_summary_sources(
    host_infos: Sequence[HostInfo],
    display_entries: Sequence[Tuple[int, str]],
    display_names: Dict[int, str],
    buffers: Dict[int, Dict[str, Any]],
    stats: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    summary_scope: str,
    group_by: str,
) -> SummarySources:
    """Prepare host, group, and Pulse severity data for display composition."""
    active_host_infos = [info for info in host_infos if info.get("active", True)]
    active_host_ids = {info["id"] for info in active_host_infos}
    host_group_labels = {info["id"]: resolve_primary_group_label(info, group_by) for info in active_host_infos}
    host_tree_labels = (
        {info["id"]: resolve_group_labels(info, group_by)[0] for info in active_host_infos}
        if group_by == "site>tag1"
        else host_group_labels
    )
    ordered_host_ids = [host_id for host_id, _label in display_entries if host_id in active_host_ids]
    summary_data = compute_summary_data(
        active_host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        ordered_host_ids=ordered_host_ids,
    )
    group_summary_data = build_group_summary_data(
        active_host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        group_by,
        ordered_host_ids,
        host_group_labels,
        host_tree_labels,
    )
    summary_source = group_summary_data if summary_scope == "group" and group_by != "none" else summary_data
    return SummarySources(
        active_host_infos=active_host_infos,
        host_group_labels=host_group_labels,
        host_tree_labels=host_tree_labels,
        ordered_host_ids=ordered_host_ids,
        summary_data=summary_data,
        group_summary_data=group_summary_data,
        summary_source=summary_source,
        kitt_total_hosts=len(active_host_infos),
        kitt_error_hosts=count_kitt_error_hosts(active_host_infos, buffers, symbols),
    )


def build_group_summary_data(
    active_host_infos: List[HostInfo],
    display_names: Dict[int, str],
    buffers: Dict[int, Dict[str, Any]],
    stats: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    group_by: str,
    ordered_host_ids: List[int],
    host_group_labels: Dict[int, str],
    host_tree_labels: Dict[int, str],
) -> List[Dict[str, Any]]:
    """Build group summary data in display order."""
    if group_by == "none":
        return []
    group_order: List[str] = []
    group_label_source = host_tree_labels if group_by == "site>tag1" else host_group_labels
    for host_id in ordered_host_ids:
        label = group_label_source.get(host_id)
        if label and label not in group_order:
            group_order.append(label)
    return compute_group_summary_data(
        active_host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        group_by=group_by,
        ordered_group_labels=group_order,
    )


def count_kitt_error_hosts(
    active_host_infos: Sequence[HostInfo],
    buffers: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
) -> int:
    """Count active hosts whose latest timeline symbol is a failure."""
    fail_symbol = symbols.get("fail")
    if not fail_symbol:
        return 0
    error_hosts = 0
    for info in active_host_infos:
        timeline = buffers.get(info["id"], {}).get("timeline")
        if timeline and timeline[-1] == fail_symbol:
            error_hosts += 1
    return error_hosts
