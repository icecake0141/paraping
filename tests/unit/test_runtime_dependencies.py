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
"""Tests that runtime dependencies are installed for default setups."""

from pathlib import Path


def test_makefile_installs_runtime_requirements() -> None:
    """Ensure default venv setup installs runtime dependencies."""
    makefile_path = Path(__file__).resolve().parents[2] / "Makefile"
    contents = makefile_path.read_text(encoding="utf-8")
    assert "pip install -r requirements.txt" in contents
