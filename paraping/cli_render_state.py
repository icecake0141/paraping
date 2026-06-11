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

"""Runtime render-state update helpers for the ParaPing CLI."""

import queue
from typing import Any, Callable, Dict


def drain_rdns_results(state: Dict[str, Any]) -> None:
    """Apply pending reverse-DNS results to host info records."""
    while True:
        try:
            host, rdns_value = state["rdns_result_queue"].get_nowait()
        except queue.Empty:
            break
        for info in state["host_info_map"].get(host, []):
            info["rdns"] = rdns_value
            info["rdns_pending"] = False
        if not state["paused"]:
            state["updated"] = True


def drain_asn_results(state: Dict[str, Any], now_func: Callable[[], float]) -> None:
    """Apply pending ASN results to host info records and cache."""
    while True:
        try:
            host, asn_value = state["asn_result_queue"].get_nowait()
        except queue.Empty:
            break
        for info in state["host_info_map"].get(host, []):
            info["asn"] = asn_value
            info["asn_pending"] = False
        ip_address = state["host_info_map"][host][0]["ip"] if state["host_info_map"].get(host) else host
        state["asn_cache"][ip_address] = {"value": asn_value, "fetched_at": now_func()}
        if not state["paused"]:
            state["updated"] = True


def enqueue_pending_asn_requests(
    state: Dict[str, Any],
    now: float,
    should_retry_asn_func: Callable[[str, Dict[str, Any], float, float], bool],
) -> None:
    """Queue ASN lookups for active hosts that still need one."""
    for host, infos in state["host_info_map"].items():
        if not any(info.get("active", True) for info in infos):
            continue
        if any(info["asn_pending"] for info in infos) or any(info["asn"] is not None for info in infos):
            continue
        ip_address = infos[0]["ip"]
        if should_retry_asn_func(ip_address, state["asn_cache"], now, state["asn_failure_ttl"]):
            for info in infos:
                info["asn_pending"] = True
            state["asn_request_queue"].put((host, ip_address))


def drain_ping_results(
    state: Dict[str, Any],
    mirror_ping_event_func: Callable[[Any, Dict[str, Any], Any, int], None],
    should_flash_on_fail_func: Callable[[str, bool, bool], bool],
    flash_screen_func: Callable[[], None],
    ring_bell_func: Callable[[], None],
) -> None:
    """Apply pending ping results to monitor state and side effects."""
    while True:
        try:
            result = state["result_queue"].get_nowait()
        except queue.Empty:
            break
        host_id = result["host_id"]
        if result.get("status") == "done":
            state["done_host_ids"].add(host_id)
            continue

        status = result["status"]
        mirror_ping_event_func(state["monitor_state"], result, status, host_id)
        if should_flash_on_fail_func(status, state["flash_on_fail"], state["show_help"]):
            flash_screen_func()
        if status == "fail" and state["bell_on_fail"] and not state["show_help"]:
            ring_bell_func()
        if not state["paused"]:
            state["updated"] = True


def update_history_projection(
    state: Dict[str, Any],
    now: float,
    update_history_buffer_func: Callable[..., Any],
    resolve_render_state_func: Callable[..., Any],
    project_render_state_func: Callable[..., Any],
) -> None:
    """Maintain history snapshots and resolve the monitor state used for rendering."""
    state["last_snapshot_time"], state["history_offset"] = update_history_buffer_func(
        state["history_buffer"],
        state["monitor_state"],
        now,
        state["last_snapshot_time"],
        state["history_offset"],
    )
    render_monitor_state, state["render_paused"], state["render_snapshot_timestamp"] = resolve_render_state_func(
        state["history_offset"],
        state["history_buffer"],
        state["monitor_state"],
        state["paused"],
    )
    state["render_buffers"], state["render_stats"] = project_render_state_func(render_monitor_state, state["symbols"])
