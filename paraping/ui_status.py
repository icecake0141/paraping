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

"""Status-line and aggregate status metric helpers."""

import os
from typing import Any, Dict, Optional, Sequence

STATUS_METRICS_SEPARATOR = " | "
STATUS_METRICS_TEMPLATE = STATUS_METRICS_SEPARATOR.join(
    ["Hosts: {hosts}", "Success: {success}", "Errors: {errors}", "Rate: {rate}"]
)


def _parse_positive_float(value: Optional[str]) -> Optional[float]:
    """Parse a strictly positive float from a string, returning None if invalid."""
    if not value:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def estimate_ping_rate(host_count: int, interval_seconds: float) -> Optional[float]:
    """Estimate the ping rate using environment variables when provided."""
    rate_env = _parse_positive_float(os.getenv("PARAPING_PING_RATE"))
    if rate_env is not None:
        return rate_env
    interval_env = _parse_positive_float(os.getenv("PARAPING_PING_INTERVAL"))
    interval_value = interval_env if interval_env is not None else interval_seconds
    if interval_value <= 0:
        return None
    return host_count / interval_value


def build_status_metrics(
    host_infos: Optional[Sequence[Dict[str, Any]]],
    stats: Optional[Dict[int, Dict[str, Any]]],
    interval_seconds: float = 1.0,
) -> str:
    """Build a status metrics string for hosts, counts, and estimated rate."""
    host_count = len(host_infos) if host_infos else 0
    successful_pings = 0
    error_count = 0
    stats_map = stats or {}
    for info in host_infos or []:
        stat_entry = stats_map.get(info["id"], {})
        total_successful = stat_entry.get("success", 0) + stat_entry.get("slow", 0)
        successful_pings += total_successful
        error_count += stat_entry.get("fail", 0)
    estimated_rate = estimate_ping_rate(host_count, interval_seconds)
    rate_label = f"{estimated_rate:.1f}/s" if estimated_rate is not None else "n/a"
    return STATUS_METRICS_TEMPLATE.format(
        hosts=host_count,
        success=successful_pings,
        errors=error_count,
        rate=rate_label,
    )


def build_status_line(
    sort_mode: str,
    filter_mode: str,
    summary_mode: str,
    paused: bool,
    status_message: Optional[str] = None,
    summary_all: bool = False,
    summary_fullscreen: bool = False,
    dormant: bool = False,
    summary_scope: str = "host",
    group_by: str = "none",
) -> str:
    """Build the status line showing current modes and settings."""
    sort_labels = {
        "failures": "Failure Count",
        "streak": "Failure Streak",
        "latency": "Latest Latency",
        "host": "Host Name",
    }
    filter_labels = {
        "failures": "Failures Only",
        "latency": "High Latency Only",
        "all": "All Items",
    }
    summary_labels = {
        "rates": "Rates",
        "rtt": "Avg RTT",
        "ttl": "TTL",
        "streak": "Streak",
    }
    sort_label = sort_labels.get(sort_mode, sort_mode)
    filter_label = filter_labels.get(filter_mode, filter_mode)
    summary_label = "All" if summary_all else summary_labels.get(summary_mode, summary_mode)
    status = f"Sort: {sort_label} | Filter: {filter_label} | Summary: {summary_label}"
    if summary_scope == "group":
        status += f" | Group: {group_by}"
    if summary_fullscreen:
        status += " | Summary View: Fullscreen"
    if dormant:
        status += " | DORMANT"
    elif paused:
        status += " | PAUSED"
    if status_message:
        status += f" | {status_message}"
    return status
