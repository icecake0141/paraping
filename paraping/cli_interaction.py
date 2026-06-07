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

"""State transitions for CLI keyboard interaction handlers."""

from typing import Any, MutableMapping


def sync_pause_state(state: MutableMapping[str, Any]) -> None:
    """Synchronize aggregate pause flags and the worker pause event."""
    state["paused"] = bool(state["display_paused"]) or bool(state["dormant"])
    pause_event = state["pause_event"]
    should_pause_workers = bool(state["dormant"]) or (state["pause_mode"] == "ping" and bool(state["display_paused"]))
    if should_pause_workers:
        pause_event.set()
    else:
        pause_event.clear()


def toggle_display_pause(state: MutableMapping[str, Any]) -> None:
    """Toggle display pause mode and update common render state."""
    state["display_paused"] = not state["display_paused"]
    sync_pause_state(state)
    state["status_message"] = "Display paused" if state["display_paused"] else "Display resumed"
    state["force_render"] = True
    state["updated"] = True


def toggle_dormant_mode(state: MutableMapping[str, Any]) -> None:
    """Toggle dormant mode and update common render state."""
    state["dormant"] = not state["dormant"]
    sync_pause_state(state)
    state["status_message"] = "Dormant mode enabled" if state["dormant"] else "Dormant mode disabled"
    state["force_render"] = True
    state["updated"] = True
