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

"""Display-entry and group-header helpers for ParaPing UI rendering."""

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from paraping.stats import (
    compute_fail_streak,
    is_hierarchical_group_by,
    latest_rtt_value,
    natural_sort_key,
    resolve_group_components,
    resolve_group_labels,
    resolve_primary_group_label,
    resolve_site_tag1_labels,
)


def resolve_display_name(host_info: Dict[str, Any], mode: str) -> str:
    """Resolve the display name for a host based on mode."""
    if mode == "ip":
        return str(host_info["ip"])
    if mode == "rdns":
        if host_info.get("rdns_pending"):
            return "resolving..."
        rdns_value = host_info.get("rdns")
        return str(rdns_value) if rdns_value is not None else str(host_info["ip"])
    if mode == "alias":
        alias_value = host_info.get("alias") or host_info.get("host")
        return str(alias_value) if alias_value is not None else str(host_info["ip"])
    return str(host_info["ip"])


def format_asn_label(host_info: Dict[str, Any], asn_width: int) -> str:
    """Format the ASN label for display."""
    if host_info.get("asn_pending"):
        label = "resolving..."
    else:
        asn_value = host_info.get("asn")
        label = str(asn_value) if asn_value is not None else ""
    return f"{label[:asn_width]:<{asn_width}}"


def format_display_name(
    host_info: Dict[str, Any],
    mode: str,
    include_asn: bool,
    asn_width: int,
    base_label_width: int = 0,
) -> str:
    """Format the complete display name including optional ASN."""
    base_label = resolve_display_name(host_info, mode)
    if not include_asn:
        formatted = base_label
    else:
        padded_label = f"{base_label:<{base_label_width}}" if base_label_width else base_label
        asn_label = format_asn_label(host_info, asn_width)
        formatted = f"{padded_label} {asn_label}"
    if host_info.get("removed"):
        return f"{formatted} [REMOVED]"
    return formatted


def build_display_names(host_infos: Sequence[Dict[str, Any]], mode: str, include_asn: bool, asn_width: int) -> Dict[int, str]:
    """Build display names for all hosts."""
    base_label_width = 0
    if include_asn:
        base_label_width = max((len(resolve_display_name(info, mode)) for info in host_infos), default=0)
    return {info["id"]: format_display_name(info, mode, include_asn, asn_width, base_label_width) for info in host_infos}


def build_display_entries(  # noqa: C901
    host_infos: Sequence[Dict[str, Any]],
    display_names: Dict[int, str],
    buffers: Dict[int, Dict[str, Any]],
    stats: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    sort_mode: str,
    filter_mode: str,
    slow_threshold: float,
    group_by: str = "none",
    group_sort_enabled: bool = False,
) -> List[Tuple[int, str]]:
    """Build and sort display entries based on current filter and sort modes."""
    info_by_id = {info["id"]: info for info in host_infos}
    entries = []
    for info in host_infos:
        host_id = info["id"]
        timeline = buffers[host_id]["timeline"]
        latest_rtt = latest_rtt_value(buffers[host_id]["rtt_history"])
        fail_streak = compute_fail_streak(timeline, symbols["fail"])
        fail_count = stats[host_id]["fail"]
        stat_entry = stats[host_id]
        total_count = stat_entry.get("total")
        if total_count is None:
            total_count = stat_entry.get("success", 0) + stat_entry.get("slow", 0) + stat_entry.get("fail", 0)

        include = True
        is_removed = bool(info.get("removed", False))
        if is_removed:
            include = True
        elif filter_mode == "failures":
            include = fail_count > 0
        elif filter_mode == "latency":
            include = latest_rtt is not None and latest_rtt >= slow_threshold

        if include:
            entries.append(
                {
                    "host_id": host_id,
                    "label": display_names.get(host_id, info["alias"]),
                    "fail_count": fail_count,
                    "fail_streak": fail_streak,
                    "latest_rtt": latest_rtt,
                    "total": total_count,
                }
            )

    if group_sort_enabled and group_by == "site>tag1":
        site_tag_groups: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for item in entries:
            host_info = info_by_id[item["host_id"]]
            site_label = resolve_primary_group_label(host_info, group_by)
            tag_group_labels = resolve_group_labels(host_info, group_by)
            tag_group_label = tag_group_labels[0] if tag_group_labels else "site:unknown>tag1:unknown"
            site_tag_groups.setdefault(site_label, {}).setdefault(tag_group_label, []).append(item)

        def _ratio(group_entries: Sequence[Dict[str, Any]]) -> float:
            total = int(sum(entry["total"] for entry in group_entries))
            failures = int(sum(entry["fail_count"] for entry in group_entries))
            return failures / max(1, total)

        def _max_latency(group_entries: Sequence[Dict[str, Any]]) -> float:
            return float(max((entry["latest_rtt"] or -1.0) for entry in group_entries))

        def _max_streak(group_entries: Sequence[Dict[str, Any]]) -> int:
            return int(max(entry["fail_streak"] for entry in group_entries))

        site_order = list(site_tag_groups.keys())
        if sort_mode in ("config", "host"):
            site_order.sort(key=natural_sort_key)
        elif sort_mode == "failures":
            site_order.sort(
                key=lambda site_label: (
                    _ratio([entry for by_tag in site_tag_groups[site_label].values() for entry in by_tag]),
                    site_label,
                ),
                reverse=True,
            )
        elif sort_mode == "latency":
            site_order.sort(
                key=lambda site_label: (
                    _max_latency([entry for by_tag in site_tag_groups[site_label].values() for entry in by_tag]),
                    site_label,
                ),
                reverse=True,
            )
        elif sort_mode == "streak":
            site_order.sort(
                key=lambda site_label: (
                    _max_streak([entry for by_tag in site_tag_groups[site_label].values() for entry in by_tag]),
                    site_label,
                ),
                reverse=True,
            )

        site_ordered_entries: List[Dict[str, Any]] = []
        for site_label in site_order:
            tags_for_site = site_tag_groups[site_label]
            tag_order = list(tags_for_site.keys())
            if sort_mode in ("config", "host"):
                tag_order.sort(key=natural_sort_key)
            elif sort_mode == "failures":
                tag_order.sort(key=lambda label: (_ratio(tags_for_site[label]), label), reverse=True)
            elif sort_mode == "latency":
                tag_order.sort(key=lambda label: (_max_latency(tags_for_site[label]), label), reverse=True)
            elif sort_mode == "streak":
                tag_order.sort(key=lambda label: (_max_streak(tags_for_site[label]), label), reverse=True)

            for tag_label in tag_order:
                group_entries = tags_for_site[tag_label]
                if sort_mode == "config":
                    group_entries.sort(key=lambda item: item["host_id"])
                elif sort_mode == "failures":
                    group_entries.sort(key=lambda item: (item["fail_count"], item["label"]), reverse=True)
                elif sort_mode == "streak":
                    group_entries.sort(key=lambda item: (item["fail_streak"], item["label"]), reverse=True)
                elif sort_mode == "latency":
                    group_entries.sort(key=lambda item: ((item["latest_rtt"] or -1.0), item["label"]), reverse=True)
                elif sort_mode == "host":
                    group_entries.sort(key=lambda item: item["label"])
                site_ordered_entries.extend(group_entries)
        entries = site_ordered_entries
    elif group_sort_enabled and group_by != "none":
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in entries:
            group_label = resolve_primary_group_label(info_by_id[item["host_id"]], group_by)
            groups.setdefault(group_label, []).append(item)

        group_order = list(groups.keys())
        if sort_mode == "config":
            group_order.sort(key=natural_sort_key)
        elif sort_mode == "failures":
            group_order.sort(
                key=lambda label: (
                    (
                        sum(entry["fail_count"] for entry in groups[label])
                        / max(1, sum(entry["total"] for entry in groups[label]))
                    ),
                    label,
                ),
                reverse=True,
            )
        elif sort_mode == "latency":
            group_order.sort(
                key=lambda label: (
                    max((entry["latest_rtt"] or -1.0) for entry in groups[label]),
                    label,
                ),
                reverse=True,
            )
        elif sort_mode == "streak":
            group_order.sort(
                key=lambda label: (
                    max(entry["fail_streak"] for entry in groups[label]),
                    label,
                ),
                reverse=True,
            )
        elif sort_mode == "host":
            group_order.sort(key=natural_sort_key)

        ordered_entries: List[Dict[str, Any]] = []
        for label in group_order:
            group_entries = groups[label]
            if sort_mode == "config":
                group_entries.sort(key=lambda item: item["host_id"])
            elif sort_mode == "failures":
                group_entries.sort(key=lambda item: (item["fail_count"], item["label"]), reverse=True)
            elif sort_mode == "streak":
                group_entries.sort(key=lambda item: (item["fail_streak"], item["label"]), reverse=True)
            elif sort_mode == "latency":
                group_entries.sort(key=lambda item: ((item["latest_rtt"] or -1.0), item["label"]), reverse=True)
            elif sort_mode == "host":
                group_entries.sort(key=lambda item: item["label"])
            ordered_entries.extend(group_entries)
        entries = ordered_entries
    else:
        if sort_mode == "config":
            entries.sort(key=lambda item: item["host_id"])
        elif sort_mode == "failures":
            entries.sort(key=lambda item: (item["fail_count"], item["label"]), reverse=True)
        elif sort_mode == "streak":
            entries.sort(key=lambda item: (item["fail_streak"], item["label"]), reverse=True)
        elif sort_mode == "latency":
            entries.sort(
                key=lambda item: ((item["latest_rtt"] or -1.0), item["label"]),
                reverse=True,
            )
        elif sort_mode == "host":
            entries.sort(key=lambda item: item["label"])

    return [(entry["host_id"], entry["label"]) for entry in entries]


def build_group_tree_label_map(
    display_entries: Sequence[Tuple[Any, ...]],
    show_group_headers: bool = False,
    host_group_labels: Optional[Dict[int, str]] = None,
    host_tree_labels: Optional[Dict[int, str]] = None,
    group_by: str = "none",
) -> Dict[int, str]:
    """Build host label overrides with tree branch markers for grouped rendering."""
    tree_labels = host_tree_labels if host_tree_labels is not None else host_group_labels
    if not show_group_headers or not tree_labels:
        return {}

    branch_prefix = "  " if is_hierarchical_group_by(group_by) else ""
    label_map: Dict[int, str] = {}
    for index, entry in enumerate(display_entries):
        host = entry[0]
        group_label = tree_labels.get(host)
        if not group_label:
            continue

        label = str(entry[1]) if len(entry) >= 2 else str(entry[0])
        next_same_group = False
        if index + 1 < len(display_entries):
            next_host = display_entries[index + 1][0]
            next_same_group = tree_labels.get(next_host) == group_label

        branch = f"{branch_prefix}{'├ ' if next_same_group else '└ '}"
        label_map[host] = f"{branch}{label}"
    return label_map


def build_group_header_line_map(  # noqa: C901
    active_host_infos: Sequence[Dict[str, Any]],
    ordered_host_ids: Sequence[int],
    group_by: str,
    group_summary_data: Sequence[Dict[str, Any]],
) -> Dict[str, List[str]]:
    """Build group header text blocks keyed by group label."""
    if group_by == "site>tag1":
        site_entries = [entry for entry in group_summary_data if entry.get("row_kind") == "site"]
        tag_entries = [entry for entry in group_summary_data if entry.get("row_kind") == "tag1"]
        site_summary = {entry.get("group_label", entry["host"]): entry for entry in site_entries}
        tag_summary = {entry.get("group_label", entry["host"]): entry for entry in tag_entries}
        site_tag_header_lines: Dict[str, List[str]] = {}
        info_by_id = {info["id"]: info for info in active_host_infos}
        for host_id in ordered_host_ids:
            info = info_by_id.get(host_id)
            if info is None:
                continue
            labels = resolve_site_tag1_labels(info)
            site_label = labels["site_label"]
            composite_label = labels["composite_label"]
            if site_label not in site_tag_header_lines:
                site_entry = site_summary.get(site_label, {})
                site_member_count = int(site_entry.get("member_count", 0))
                site_loss_rate = float(site_entry.get("loss_rate", 0.0))
                site_tag_header_lines[site_label] = [
                    f"--- {site_label} ({site_member_count} hosts, loss {site_loss_rate:.1f}%) ---"
                ]
            if composite_label not in site_tag_header_lines:
                tag_entry = tag_summary.get(composite_label, {})
                tag_member_count = int(tag_entry.get("member_count", 0))
                tag_loss_rate = float(tag_entry.get("loss_rate", 0.0))
                tag_label = str(tag_entry.get("host", labels["tag1_label"]))
                site_tag_header_lines[composite_label] = [
                    f"  --- {tag_label} ({tag_member_count} hosts, loss {tag_loss_rate:.1f}%) ---"
                ]
        return site_tag_header_lines

    summary_by_label = {entry["host"]: entry for entry in group_summary_data}
    info_by_id = {info["id"]: info for info in active_host_infos}
    header_lines: Dict[str, List[str]] = {}
    for host_id in ordered_host_ids:
        info = info_by_id.get(host_id)
        if info is None:
            continue
        primary_label = resolve_primary_group_label(info, group_by)
        if primary_label in header_lines:
            continue
        summary_entry = summary_by_label.get(primary_label, {})
        member_count = int(summary_entry.get("member_count", 0))
        loss_rate = float(summary_entry.get("loss_rate", 0.0))
        suffix = f" ({member_count} hosts, loss {loss_rate:.1f}%)"
        if is_hierarchical_group_by(group_by):
            components = resolve_group_components(info, group_by)
            if len(components) >= 2:
                header_lines[primary_label] = [f"--- {components[0]} ---", f"  {components[1]}{suffix}"]
                continue
        header_lines[primary_label] = [f"--- {primary_label}{suffix} ---"]
    return header_lines


def resolve_group_header_lines(
    host_id: Any,
    group_by: str,
    current_primary_group: Optional[str],
    current_tree_group: Optional[str],
    host_group_labels: Optional[Dict[int, str]],
    host_tree_labels: Optional[Dict[int, str]],
    group_header_lines: Optional[Mapping[str, Union[str, List[str]]]],
) -> Tuple[List[str], Optional[str], Optional[str]]:
    """Resolve which group headers should be inserted before a host row."""
    if not host_group_labels:
        return [], current_primary_group, current_tree_group

    primary_group_label = host_group_labels.get(host_id)
    if not primary_group_label:
        return [], current_primary_group, current_tree_group

    tree_group_label = host_tree_labels.get(host_id) if host_tree_labels else primary_group_label
    header_stack: List[str] = []

    def _as_lines(label: str, fallback: str) -> List[str]:
        if not group_header_lines:
            return [fallback]
        header_value = group_header_lines.get(label, [fallback])
        if isinstance(header_value, str):
            return [header_value]
        return list(header_value)

    if group_by == "site>tag1":
        if primary_group_label != current_primary_group:
            header_stack.extend(_as_lines(primary_group_label, f"--- {primary_group_label} ---"))
        if tree_group_label and tree_group_label != current_tree_group:
            header_stack.extend(_as_lines(tree_group_label, f"  --- {tree_group_label} ---"))
        return header_stack, primary_group_label, tree_group_label

    if primary_group_label != current_primary_group:
        header_stack.extend(_as_lines(primary_group_label, f"--- {primary_group_label} ---"))
        return header_stack, primary_group_label, tree_group_label
    return [], current_primary_group, current_tree_group
