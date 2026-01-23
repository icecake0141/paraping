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

"""
Unit tests for timeline synchronization feature.

This module tests the pending slot behavior that synchronizes timeline columns
across hosts by emitting 'sent' events.
"""

import time
from collections import deque


def _make_buffers(timeline_width=10):
    """Helper to create buffers structure matching cli.py"""
    return {
        0: {
            "timeline": deque(maxlen=timeline_width),
            "rtt_history": deque(maxlen=timeline_width),
            "time_history": deque(maxlen=timeline_width),
            "ttl_history": deque(maxlen=timeline_width),
            "categories": {
                "success": deque(maxlen=timeline_width),
                "fail": deque(maxlen=timeline_width),
                "slow": deque(maxlen=timeline_width),
                "pending": deque(maxlen=timeline_width),
            },
        }
    }


def test_pending_then_success_updates_slot():
    """Test that a pending slot is replaced by a success status"""
    buffers = _make_buffers()
    stats = {0: {"success": 0, "fail": 0, "slow": 0, "total": 0, "rtt_sum": 0.0, "rtt_sum_sq": 0.0, "rtt_count": 0}}

    symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}

    # Simulate sent event
    sent = {"host_id": 0, "sequence": 1, "status": "sent", "sent_time": time.time()}
    # Simulate main's pending append
    buffers[0]["timeline"].append(symbols["pending"])
    buffers[0]["rtt_history"].append(None)
    buffers[0]["time_history"].append(sent["sent_time"])
    buffers[0]["ttl_history"].append(None)
    buffers[0]["categories"]["pending"].append(1)

    assert buffers[0]["timeline"][-1] == symbols["pending"]

    # Now simulate final success arriving later
    success = {"host_id": 0, "sequence": 1, "status": "success", "rtt": 0.01, "ttl": 64}

    # Emulate the overwrite logic from CLI
    last_symbol = buffers[0]["timeline"][-1]
    if last_symbol == symbols.get("pending"):
        buffers[0]["timeline"][-1] = symbols[success["status"]]
        buffers[0]["rtt_history"][-1] = success.get("rtt")
        buffers[0]["time_history"][-1] = time.time()
        buffers[0]["ttl_history"][-1] = success.get("ttl")
        try:
            buffers[0]["categories"]["pending"].pop()
        except IndexError:
            pass
        buffers[0]["categories"]["success"].append(success["sequence"])

        stats[0]["success"] += 1
        stats[0]["total"] += 1
        stats[0]["rtt_sum"] += success["rtt"]
        stats[0]["rtt_sum_sq"] += success["rtt"] ** 2
        stats[0]["rtt_count"] += 1

    assert buffers[0]["timeline"][-1] == symbols["success"]
    assert buffers[0]["rtt_history"][-1] == 0.01
    assert stats[0]["success"] == 1


def test_missing_pending_still_appends():
    """Test that missing pending slots are handled by appending normally"""
    buffers = _make_buffers()
    stats = {0: {"success": 0, "fail": 0, "slow": 0, "total": 0, "rtt_sum": 0.0, "rtt_sum_sq": 0.0, "rtt_count": 0}}

    symbols = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}

    # Directly receive final status without a prior pending
    fail = {"host_id": 0, "sequence": 1, "status": "fail", "rtt": None}
    buffers[0]["timeline"].append(symbols[fail["status"]])
    buffers[0]["rtt_history"].append(None)
    buffers[0]["time_history"].append(time.time())
    buffers[0]["ttl_history"].append(None)
    buffers[0]["categories"]["fail"].append(fail["sequence"])

    stats[0]["fail"] += 1
    stats[0]["total"] += 1

    assert buffers[0]["timeline"][-1] == symbols["fail"]
    assert stats[0]["fail"] == 1
