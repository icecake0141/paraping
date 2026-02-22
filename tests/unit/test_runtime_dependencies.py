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


def test_default_venv_installs_runtime_requirements() -> None:
    """Ensure default venv setup installs runtime dependencies."""
    makefile_path = Path(__file__).resolve().parents[2] / "Makefile"
    contents = makefile_path.read_text(encoding="utf-8")
    lines = contents.splitlines()
    target_line = "$(VENV):"
    start_index = next((index for index, line in enumerate(lines) if line.startswith(target_line)), None)
    assert start_index is not None, "Expected $(VENV) target not found in Makefile."
    recipe_lines = []
    for line in lines[start_index + 1 :]:
        if line.startswith("\t"):
            recipe_lines.append(line)
            continue
        if line.strip() == "":
            continue
        break
    recipe_block = "\n".join(recipe_lines)
    assert "pip install -r requirements.txt" in recipe_block
