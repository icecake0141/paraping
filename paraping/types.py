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

"""Shared structural types for ParaPing."""

from typing import Any, List, Optional, TypedDict


class HostInfo(TypedDict, total=False):
    """Host metadata carried through CLI runtime, statistics, and UI rendering."""

    id: int
    host: str
    alias: str
    ip: str
    site: str
    tags: List[str]
    rdns: Optional[str]
    rdns_pending: bool
    asn: Optional[Any]
    asn_pending: bool
    active: bool
    removed: bool
    retired_until: Optional[float]
