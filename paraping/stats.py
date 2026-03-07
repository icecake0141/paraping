#!/usr/bin/env python3
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
# Review required for correctness, security, and licensing.

"""
Statistics computation for ParaPing.

This module provides functions for computing statistics like jitter,
standard deviation, streaks, and aggregated ping data.
"""

import math
import re
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple

TAG_INDEX_GROUP_RE = re.compile(r"^tag(\d+)$")
HIER_GROUP_SITE_TAG1 = "site>tag1"
HIER_GROUP_TAG1_SITE = "tag1>site"


def compute_fail_streak(timeline: Sequence[str], fail_symbol: str) -> int:
    """
    Compute the current consecutive failure streak.

    Args:
        timeline: Deque of status symbols
        fail_symbol: The symbol representing a failure

    Returns:
        Number of consecutive failures from the end of the timeline
    """
    streak = 0
    for symbol in reversed(timeline):
        if symbol == fail_symbol:
            streak += 1
        else:
            break
    return streak


def build_streak_label(entry: Dict[str, Any]) -> str:
    """
    Build a display label for a streak.

    Args:
        entry: Dictionary with streak_type and streak_length

    Returns:
        String label like "F5" for fail streak or "S10" for success streak
    """
    streak_label = "-"
    if entry["streak_type"] == "fail":
        streak_label = f"F{entry['streak_length']}"
    elif entry["streak_type"] == "success":
        streak_label = f"S{entry['streak_length']}"
    return streak_label


def build_packet_stats_label(entry: Dict[str, Any]) -> str:
    """
    Build packet statistics label in Snt/Rcv/Los format with loss percentage.

    Args:
        entry: Dictionary with sent, received, lost, and loss_rate

    Returns:
        Formatted string like "10/9/1 loss 10.0%"
    """
    sent = entry.get("sent", 0)
    received = entry.get("received", 0)
    lost = entry.get("lost", 0)
    return f"{sent}/{received}/{lost} loss {entry['loss_rate']:.1f}%"


def build_summary_suffix(entry: Dict[str, Any], summary_mode: str) -> str:
    """
    Build the suffix for a summary line based on the summary mode.

    Args:
        entry: Dictionary with statistics data
        summary_mode: Display mode ('rtt', 'ttl', 'streak', or 'rates')

    Returns:
        Formatted suffix string
    """
    if summary_mode == "rtt":
        avg_rtt = f"{entry['avg_rtt_ms']:.1f} ms" if entry.get("avg_rtt_ms") is not None else "n/a"
        jitter = f"{entry['jitter_ms']:.1f} ms" if entry.get("jitter_ms") is not None else "n/a"
        stddev = f"{entry['stddev_ms']:.1f} ms" if entry.get("stddev_ms") is not None else "n/a"
        return f": avg rtt {avg_rtt} jitter {jitter} stddev {stddev}"
    if summary_mode == "ttl":
        latest_ttl = entry.get("latest_ttl")
        return f": ttl {latest_ttl}" if latest_ttl is not None else ": ttl n/a"
    if summary_mode == "streak":
        return f": streak {build_streak_label(entry)}"
    # Default mode is 'rates' - show Snt/Rcv/Los and loss percentage
    return f": {build_packet_stats_label(entry)}"


def build_summary_all_suffix(entry: Dict[str, Any]) -> str:
    """
    Build a comprehensive summary suffix with all statistics.

    Args:
        entry: Dictionary with statistics data

    Returns:
        Formatted suffix string with all statistics
    """
    avg_rtt = f"{entry['avg_rtt_ms']:.1f} ms" if entry.get("avg_rtt_ms") is not None else "n/a"
    jitter = f"{entry['jitter_ms']:.1f} ms" if entry.get("jitter_ms") is not None else "n/a"
    stddev = f"{entry['stddev_ms']:.1f} ms" if entry.get("stddev_ms") is not None else "n/a"
    latest_ttl = entry.get("latest_ttl")
    ttl_value = f"{latest_ttl}" if latest_ttl is not None else "n/a"
    streak_label = build_streak_label(entry)
    parts = [
        build_packet_stats_label(entry),
        f"avg rtt {avg_rtt}",
        f"jitter {jitter}",
        f"stddev {stddev}",
        f"ttl {ttl_value}",
        f"streak {streak_label}",
    ]
    return f": {' | '.join(parts)}"


def compute_summary_data(
    host_infos: Sequence[Dict[str, Any]],
    display_names: Dict[int, str],
    buffers: Dict[int, Dict[str, Any]],
    stats: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    ordered_host_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Compute summary statistics for all hosts.

    Args:
        host_infos: List of host information dictionaries
        display_names: Dictionary mapping host IDs to display names
        buffers: Dictionary of per-host buffers
        stats: Dictionary of per-host statistics
        symbols: Dictionary mapping status to symbol
        ordered_host_ids: Optional list of host IDs in desired order

    Returns:
        List of summary data dictionaries, one per host
    """
    summary = []
    success_symbols = {symbols["success"], symbols["slow"]}
    info_by_id = {info["id"]: info for info in host_infos}
    host_ids = ordered_host_ids if ordered_host_ids is not None else [info["id"] for info in host_infos]
    for host_id in host_ids:
        info = info_by_id.get(host_id)
        if info is None:
            continue
        display_name = display_names.get(host_id, info["alias"])
        total = stats[host_id]["total"]
        success = stats[host_id]["success"] + stats[host_id]["slow"]
        fail = stats[host_id]["fail"]
        success_rate = (success / total * 100) if total > 0 else 0.0
        loss_rate = (fail / total * 100) if total > 0 else 0.0
        timeline = list(buffers[host_id]["timeline"])
        streak_type = None
        streak_length = 0
        if timeline:
            last = timeline[-1]
            if last in success_symbols:
                streak_type = "success"
                for symbol in reversed(timeline):
                    if symbol in success_symbols:
                        streak_length += 1
                    else:
                        break
            elif last == symbols["fail"]:
                streak_type = "fail"
                for symbol in reversed(timeline):
                    if symbol == symbols["fail"]:
                        streak_length += 1
                    else:
                        break
        avg_rtt_ms = None
        if stats[host_id]["rtt_count"] > 0:
            avg_rtt_ms = stats[host_id]["rtt_sum"] / stats[host_id]["rtt_count"] * 1000
        stddev_ms = None
        if stats[host_id]["rtt_count"] > 1:
            mean_rtt = stats[host_id]["rtt_sum"] / stats[host_id]["rtt_count"]
            mean_square = stats[host_id].get("rtt_sum_sq", 0.0) / stats[host_id]["rtt_count"]
            variance = max(0.0, mean_square - mean_rtt * mean_rtt)
            stddev_ms = math.sqrt(variance) * 1000
        rtt_values = [value for value in buffers[host_id]["rtt_history"] if value is not None]
        jitter_ms = None
        if len(rtt_values) >= 2:
            diffs = [abs(current - previous) for previous, current in zip(rtt_values, rtt_values[1:])]
            jitter_ms = sum(diffs) / len(diffs) * 1000
        latest_ttl = latest_ttl_value(buffers[host_id]["ttl_history"])
        summary.append(
            {
                "host": display_name,
                "sent": total,
                "received": success,
                "lost": fail,
                "success_rate": success_rate,
                "loss_rate": loss_rate,
                "streak_type": streak_type,
                "streak_length": streak_length,
                "avg_rtt_ms": avg_rtt_ms,
                "jitter_ms": jitter_ms,
                "stddev_ms": stddev_ms,
                "latest_ttl": latest_ttl,
            }
        )
    return summary


def latest_ttl_value(ttl_history: Deque[Optional[int]]) -> Optional[int]:
    """
    Get the latest TTL value from history.

    Args:
        ttl_history: Deque of TTL values

    Returns:
        The most recent TTL value, or None if history is empty
    """
    if not ttl_history:
        return None
    return ttl_history[-1]


def latest_rtt_value(rtt_history: Deque[Optional[float]]) -> Optional[float]:
    """
    Get the latest RTT value from history.

    Args:
        rtt_history: Deque of RTT values

    Returns:
        The most recent RTT value, or None if history is empty
    """
    if not rtt_history:
        return None
    return rtt_history[-1]


def natural_sort_key(value: str) -> Tuple[Tuple[int, Any], ...]:
    """Build a natural-sort key that remains comparable across mixed chunk types."""
    parts = re.split(r"(\d+)", value)
    key: List[Tuple[int, Any]] = []
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part.lower()))
    return tuple(key)


def normalize_host_tags(host_info: Dict[str, Any]) -> List[str]:
    """Return de-duplicated host tags in config order, with whitespace removed."""
    tags = host_info.get("tags") or []
    if not isinstance(tags, list):
        tags = [tags]
    normalized: List[str] = []
    seen = set()
    for tag in tags:
        value = str(tag).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def resolve_site_group_label(host_info: Dict[str, Any]) -> str:
    """Resolve a site-based group label for one host."""
    site_value = str(host_info.get("site") or "").strip()
    return f"site:{site_value}" if site_value else "site:unknown"


def resolve_tag_index_group_label(host_info: Dict[str, Any], tag_index: int) -> str:
    """Resolve a positional tag label (1-based) for one host."""
    normalized = normalize_host_tags(host_info)
    if tag_index < 1 or tag_index > len(normalized):
        return "tag:unknown"
    return f"tag:{normalized[tag_index - 1]}"


def is_hierarchical_group_by(group_by: str) -> bool:
    """Return True when group mode is one of the two-level hierarchy modes."""
    return group_by in (HIER_GROUP_SITE_TAG1, HIER_GROUP_TAG1_SITE)


def resolve_group_components(host_info: Dict[str, Any], group_by: str) -> List[str]:
    """Resolve display components for a group mode (1 item for flat, 2 for hierarchy)."""
    if group_by == "asn":
        asn_value = host_info.get("asn")
        return [f"ASN:{asn_value}" if asn_value not in (None, "") else "ASN:unknown"]
    if group_by == "site":
        return [resolve_site_group_label(host_info)]
    if group_by == HIER_GROUP_SITE_TAG1:
        return [resolve_site_group_label(host_info), resolve_tag_index_group_label(host_info, 1)]
    if group_by == HIER_GROUP_TAG1_SITE:
        return [resolve_tag_index_group_label(host_info, 1), resolve_site_group_label(host_info)]
    tag_index_match = TAG_INDEX_GROUP_RE.match(group_by)
    if tag_index_match:
        return [resolve_tag_index_group_label(host_info, int(tag_index_match.group(1)))]
    if group_by == "tag":
        labels = resolve_group_labels(host_info, "tag")
        return [labels[0] if labels else "tag:unknown"]
    return ["all"]


def resolve_group_labels(host_info: Dict[str, Any], group_by: str) -> List[str]:
    """Resolve all group labels for one host based on grouping mode."""
    if group_by == "asn":
        return resolve_group_components(host_info, group_by)
    if group_by == "site":
        return resolve_group_components(host_info, group_by)
    tag_index_match = TAG_INDEX_GROUP_RE.match(group_by)
    if tag_index_match:
        return [resolve_tag_index_group_label(host_info, int(tag_index_match.group(1)))]
    if is_hierarchical_group_by(group_by):
        return [" > ".join(resolve_group_components(host_info, group_by))]
    if group_by == "tag":
        normalized = sorted(normalize_host_tags(host_info), key=natural_sort_key)
        if not normalized:
            return ["tag:unknown"]
        return [f"tag:{tag}" for tag in normalized]
    return ["all"]


def resolve_primary_group_label(host_info: Dict[str, Any], group_by: str) -> str:
    """Resolve the primary group label used for host-row ordering."""
    if group_by == "site>tag1":
        return resolve_site_tag1_labels(host_info)["site_label"]
    labels = resolve_group_labels(host_info, group_by)
    return labels[0] if labels else "unknown"


def resolve_site_tag1_labels(host_info: Dict[str, Any]) -> Dict[str, str]:
    """Resolve hierarchical labels used by `site>tag1` grouping mode."""
    site_value = str(host_info.get("site") or "").strip()
    site_label = f"site:{site_value}" if site_value else "site:unknown"

    raw_tags = host_info.get("tags") or []
    if isinstance(raw_tags, list):
        first_tag = str(raw_tags[0]).strip() if raw_tags else ""
    else:
        first_tag = str(raw_tags).strip()
    tag1_label = f"tag1:{first_tag}" if first_tag else "tag1:unknown"

    return {
        "site_label": site_label,
        "tag1_label": tag1_label,
        "composite_label": f"{site_label}>{tag1_label}",
    }


def compute_group_summary_data(
    host_infos: Sequence[Dict[str, Any]],
    display_names: Dict[int, str],
    buffers: Dict[int, Dict[str, Any]],
    stats: Dict[int, Dict[str, Any]],
    symbols: Dict[str, str],
    group_by: str,
    ordered_group_labels: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Compute aggregated summary rows by group label."""
    if group_by == "none":
        return []

    success_symbols = {symbols["success"], symbols["slow"]}
    groups: Dict[str, Dict[str, Any]] = {}
    hierarchy_labels: Dict[str, Dict[str, str]] = {}

    for info in host_infos:
        host_id = info["id"]
        host_stats = stats[host_id]
        if group_by == "site>tag1":
            labels_map = resolve_site_tag1_labels(info)
            hierarchy_labels[labels_map["composite_label"]] = labels_map
            labels = [labels_map["site_label"], labels_map["composite_label"]]
        else:
            labels = resolve_group_labels(info, group_by)
        timeline = list(buffers[host_id]["timeline"])
        latest_symbol = timeline[-1] if timeline else None
        fail_streak = compute_fail_streak(timeline, symbols["fail"])
        rtt_values = [value for value in buffers[host_id]["rtt_history"] if value is not None]
        jitter_ms = None
        if len(rtt_values) >= 2:
            diffs = [abs(current - previous) for previous, current in zip(rtt_values, rtt_values[1:])]
            jitter_ms = sum(diffs) / len(diffs) * 1000

        for label in labels:
            group = groups.setdefault(
                label,
                {
                    "host": label,
                    "sent": 0,
                    "received": 0,
                    "lost": 0,
                    "success_rate": 0.0,
                    "loss_rate": 0.0,
                    "streak_type": None,
                    "streak_length": 0,
                    "avg_rtt_ms": None,
                    "jitter_ms": None,
                    "stddev_ms": None,
                    "latest_ttl": None,
                    "_member_ids": set(),
                    "_rtt_sum": 0.0,
                    "_rtt_sum_sq": 0.0,
                    "_rtt_count": 0,
                    "_jitter_weighted_sum": 0.0,
                    "_jitter_weight": 0,
                    "_latest_symbol": None,
                },
            )
            group["_member_ids"].add(host_id)
            group["sent"] += host_stats["total"]
            group["received"] += host_stats["success"] + host_stats["slow"]
            group["lost"] += host_stats["fail"]
            group["_rtt_sum"] += host_stats["rtt_sum"]
            group["_rtt_sum_sq"] += host_stats.get("rtt_sum_sq", 0.0)
            group["_rtt_count"] += host_stats["rtt_count"]
            if jitter_ms is not None and len(rtt_values) > 1:
                weight = len(rtt_values) - 1
                group["_jitter_weighted_sum"] += jitter_ms * weight
                group["_jitter_weight"] += weight
            latest_ttl = latest_ttl_value(buffers[host_id]["ttl_history"])
            if latest_ttl is not None:
                group["latest_ttl"] = latest_ttl
            group["streak_length"] = max(group["streak_length"], fail_streak)
            if latest_symbol == symbols["fail"]:
                group["_latest_symbol"] = symbols["fail"]
            elif latest_symbol == symbols["slow"] and group["_latest_symbol"] not in (symbols["fail"], symbols["slow"]):
                group["_latest_symbol"] = symbols["slow"]
            elif latest_symbol in success_symbols and group["_latest_symbol"] is None:
                group["_latest_symbol"] = symbols["success"]

    summary = []
    for label, group in groups.items():
        sent = group["sent"]
        received = group["received"]
        lost = group["lost"]
        group["success_rate"] = (received / sent * 100) if sent > 0 else 0.0
        group["loss_rate"] = (lost / sent * 100) if sent > 0 else 0.0
        rtt_count = group["_rtt_count"]
        if rtt_count > 0:
            mean_rtt = group["_rtt_sum"] / rtt_count
            group["avg_rtt_ms"] = mean_rtt * 1000
        if rtt_count > 1:
            mean_rtt = group["_rtt_sum"] / rtt_count
            mean_square = group["_rtt_sum_sq"] / rtt_count
            variance = max(0.0, mean_square - mean_rtt * mean_rtt)
            group["stddev_ms"] = math.sqrt(variance) * 1000
        if group["_jitter_weight"] > 0:
            group["jitter_ms"] = group["_jitter_weighted_sum"] / group["_jitter_weight"]
        latest_symbol = group["_latest_symbol"]
        if latest_symbol == symbols["fail"] and group["streak_length"] > 0:
            group["streak_type"] = "fail"
        else:
            group["streak_type"] = None
            group["streak_length"] = 0
        group["member_count"] = len(group["_member_ids"])
        summary.append(
            {
                "host": (
                    hierarchy_labels[label]["tag1_label"] if group_by == "site>tag1" and label in hierarchy_labels else label
                ),
                "sent": group["sent"],
                "received": group["received"],
                "lost": group["lost"],
                "success_rate": group["success_rate"],
                "loss_rate": group["loss_rate"],
                "streak_type": group["streak_type"],
                "streak_length": group["streak_length"],
                "avg_rtt_ms": group["avg_rtt_ms"],
                "jitter_ms": group["jitter_ms"],
                "stddev_ms": group["stddev_ms"],
                "latest_ttl": group["latest_ttl"],
                "member_count": group["member_count"],
                "row_kind": (
                    "tag1"
                    if group_by == "site>tag1" and label in hierarchy_labels
                    else ("site" if group_by == "site>tag1" else "group")
                ),
                "indent_level": 1 if group_by == "site>tag1" and label in hierarchy_labels else 0,
                "parent_label": (
                    hierarchy_labels[label]["site_label"] if group_by == "site>tag1" and label in hierarchy_labels else None
                ),
                "group_label": label,
            }
        )

    if ordered_group_labels is not None:
        order_index = {label: index for index, label in enumerate(ordered_group_labels)}
        if group_by == "site>tag1":
            site_order: List[str] = []
            for composite in ordered_group_labels:
                hierarchy = hierarchy_labels.get(composite)
                if not hierarchy:
                    continue
                site_label = hierarchy["site_label"]
                if site_label not in site_order:
                    site_order.append(site_label)
            site_order_index = {label: index for index, label in enumerate(site_order)}

            def _sort_site_tag1(entry: Dict[str, Any]) -> Tuple[int, int, int]:
                row_kind = entry.get("row_kind")
                group_label = entry.get("group_label", entry["host"])
                if row_kind == "site":
                    return (site_order_index.get(group_label, len(site_order_index)), -1, -1)
                parent_label = entry.get("parent_label")
                return (
                    site_order_index.get(parent_label, len(site_order_index)),
                    0,
                    order_index.get(group_label, len(order_index)),
                )

            summary.sort(key=_sort_site_tag1)
        else:
            summary.sort(key=lambda entry: order_index.get(entry["host"], len(order_index)))
    else:
        summary.sort(key=lambda entry: natural_sort_key(entry["host"]))
    return summary
