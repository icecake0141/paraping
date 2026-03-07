#!/usr/bin/env python3
# Copyright 2026 icecake0141
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for centralized keyboard mapping."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.keymap import build_help_items, find_key_conflicts, resolve_action  # noqa: E402


class TestKeymapResolveAction(unittest.TestCase):
    """Test context-aware action resolution."""

    def test_global_actions_win(self):
        self.assertEqual(resolve_action("q", "main"), "quit")
        self.assertEqual(resolve_action("?", "graph"), "help_toggle")

    def test_main_navigation_aliases(self):
        self.assertEqual(resolve_action("h", "main"), "history_prev")
        self.assertEqual(resolve_action("arrow_left", "main"), "history_prev")
        self.assertEqual(resolve_action("l", "main"), "history_next")
        self.assertEqual(resolve_action("arrow_right", "main"), "history_next")
        self.assertEqual(resolve_action("j", "main"), "host_scroll_down")
        self.assertEqual(resolve_action("arrow_down", "main"), "host_scroll_down")
        self.assertEqual(resolve_action("k", "main"), "host_scroll_up")
        self.assertEqual(resolve_action("arrow_up", "main"), "host_scroll_up")

    def test_context_specific_actions(self):
        self.assertEqual(resolve_action("j", "host_select"), "select_next")
        self.assertEqual(resolve_action("k", "host_select"), "select_prev")
        self.assertEqual(resolve_action("\r", "host_select"), "select_confirm")
        self.assertEqual(resolve_action("\x1b", "host_select"), "back")
        self.assertEqual(resolve_action("v", "graph"), "graph_toggle")
        self.assertEqual(resolve_action("x", "graph"), "host_select_open")


class TestKeymapHelpAndConflicts(unittest.TestCase):
    """Test help content generation and conflict checks."""

    def test_help_items_include_new_core_keys(self):
        lines = "\n".join(build_help_items())
        self.assertIn("?: toggle help", lines)
        self.assertIn("d: cycle display mode", lines)
        self.assertIn("u: force full redraw", lines)
        self.assertIn("y: toggle Knight Rider mode", lines)
        self.assertIn("Y: cycle Knight Rider style", lines)

    def test_key_conflicts_are_empty(self):
        self.assertEqual(find_key_conflicts(), {})


if __name__ == "__main__":
    unittest.main()
