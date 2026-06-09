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

"""CLI display mode definitions and index helpers."""

from typing import Sequence

DISPLAY_NAME_MODES = ["ip", "rdns", "alias"]
DISPLAY_VIEW_MODES = ["timeline", "sparkline", "square"]
SUMMARY_MODES = ["rates", "rtt", "ttl", "streak"]
SUMMARY_SCOPE_MODES = ["host", "group"]
SORT_MODES = ["config", "failures", "streak", "latency", "host"]
FILTER_MODES = ["failures", "latency", "all"]
KITT_STYLE_MODES = ["scanner", "gradient"]


def resolve_mode_index(modes: Sequence[str], selected: str, default_index: int = 0) -> int:
    """Return selected mode index, falling back to a valid default index."""
    if selected in modes:
        return modes.index(selected)
    if not modes:
        return 0
    return max(0, min(default_index, len(modes) - 1))
