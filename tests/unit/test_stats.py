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

"""Unit tests for paraping.stats helpers."""

import os
import sys
import unittest

# Add parent directory to path to import paraping
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.stats import natural_sort_key, resolve_group_labels


class TestNaturalSortKey(unittest.TestCase):
    """Test cases for natural-sort behavior."""

    def test_mixed_leading_numeric_and_alpha_values_are_sortable(self) -> None:
        """Sorting mixed values should not raise TypeError."""
        values = ["prod2", "1st", "prod10", "alpha", "2nd"]
        result = sorted(values, key=natural_sort_key)
        self.assertEqual(result, ["1st", "2nd", "alpha", "prod2", "prod10"])


class TestResolveGroupLabels(unittest.TestCase):
    """Test cases for grouping label resolution."""

    def test_tag_group_labels_handle_mixed_prefixes(self) -> None:
        """Tag grouping should handle numeric-leading and alpha-leading tags."""
        host_info = {"tags": ["prod2", "1st", "prod10", "alpha", "2nd"]}
        labels = resolve_group_labels(host_info, "tag")
        self.assertEqual(labels, ["tag:1st", "tag:2nd", "tag:alpha", "tag:prod2", "tag:prod10"])


if __name__ == "__main__":
    unittest.main()
