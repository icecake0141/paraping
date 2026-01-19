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


def compute_fail_streak(timeline, fail_symbol):
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


def build_streak_label(entry):
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


def build_summary_suffix(entry, summary_mode):
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
    return f": ok {entry['success_rate']:.1f}% loss {entry['loss_rate']:.1f}%"


def build_summary_all_suffix(entry):
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
        f"ok {entry['success_rate']:.1f}% loss {entry['loss_rate']:.1f}%",
        f"avg rtt {avg_rtt}",
        f"jitter {jitter}",
        f"stddev {stddev}",
        f"ttl {ttl_value}",
        f"streak {streak_label}",
    ]
    return f": {' | '.join(parts)}"


def compute_summary_data(
    host_infos,
    display_names,
    buffers,
    stats,
    symbols,
    ordered_host_ids=None,
):
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


def latest_ttl_value(ttl_history):
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


def latest_rtt_value(rtt_history):
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
