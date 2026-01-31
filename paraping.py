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
ParaPing - User entrypoint script.

This is the main executable entrypoint for running ParaPing from the repository root.
Users can run this file directly with: python paraping.py [args]
or execute it directly: ./paraping.py [args]

This wrapper imports and runs the main CLI entry point from the paraping package.
"""

if __name__ == "__main__":
    from paraping.cli import main

    main()
