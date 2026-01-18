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
"""Tests for paraping package initialization."""

import unittest

import paraping


class TestPackageInit(unittest.TestCase):
    """Tests for paraping package init."""

    def test_version_is_string(self):
        """Ensure the package exposes a non-empty version string."""
        self.assertTrue(hasattr(paraping, "__version__"))
        self.assertIsInstance(paraping.__version__, str)
        self.assertTrue(paraping.__version__)


if __name__ == "__main__":
    unittest.main()
