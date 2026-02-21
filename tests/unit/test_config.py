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
Unit tests for paraping.config module.

Covers:
- INI config loading (various field types, hosts section, edge cases)
- YAML config loading (flat defaults, hosts list, edge cases)
- Format auto-detection (_is_yaml_file)
- load_config entry point (missing file, YAML, INI dispatch)
- _apply_config_to_args merging logic
- handle_options integration with config (--no-config flag, override precedence)
"""

import os
import sys
import tempfile
import unittest
from argparse import Namespace
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from paraping.cli import _apply_config_to_args, handle_options
from paraping.config import (
    _is_yaml_file,
    load_config,
    load_ini_config,
    load_yaml_config,
)


class TestParseBool(unittest.TestCase):
    """Tests for the internal _parse_bool helper via INI config loading."""

    def _load(self, content: str, key: str) -> object:
        with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = f.name
        try:
            return load_ini_config(path)[key]
        finally:
            os.unlink(path)

    def test_true_values(self):
        for val in ("true", "True", "TRUE", "yes", "Yes", "1", "on", "On"):
            result = self._load(f"[default]\ncolor = {val}\n", "color")
            self.assertTrue(result, msg=f"Expected True for '{val}'")

    def test_false_values(self):
        for val in ("false", "False", "FALSE", "no", "No", "0", "off", "Off"):
            result = self._load(f"[default]\ncolor = {val}\n", "color")
            self.assertFalse(result, msg=f"Expected False for '{val}'")

    def test_invalid_bool_raises(self):
        with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False, encoding="utf-8") as f:
            f.write("[default]\ncolor = maybe\n")
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_ini_config(path)
        finally:
            os.unlink(path)


class TestLoadIniConfig(unittest.TestCase):
    """Tests for load_ini_config."""

    def _write(self, content: str) -> str:
        f = tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return f.name

    def test_basic_default_section(self):
        path = self._write("[default]\ninterval = 2.0\ntimeout = 3\ncolor = true\n")
        try:
            cfg = load_ini_config(path)
            self.assertAlmostEqual(cfg["interval"], 2.0)
            self.assertEqual(cfg["timeout"], 3)
            self.assertTrue(cfg["color"])
        finally:
            os.unlink(path)

    def test_hosts_section_bare_values(self):
        """Hosts without '=' delimiters (allow_no_value=True)."""
        path = self._write("[hosts]\n8.8.8.8\n1.1.1.1\n")
        try:
            cfg = load_ini_config(path)
            self.assertIn("hosts", cfg)
            self.assertIn("8.8.8.8", cfg["hosts"])
            self.assertIn("1.1.1.1", cfg["hosts"])
        finally:
            os.unlink(path)

    def test_hosts_section_key_value(self):
        """Hosts with 'key = value' style."""
        path = self._write("[hosts]\nhost1 = 8.8.8.8\nhost2 = 1.1.1.1\n")
        try:
            cfg = load_ini_config(path)
            self.assertIn("hosts", cfg)
            self.assertIn("8.8.8.8", cfg["hosts"])
        finally:
            os.unlink(path)

    def test_colon_delimiter(self):
        """Keys separated by ':' instead of '='."""
        path = self._write("[default]\ninterval: 2.5\ntimeout: 5\n")
        try:
            cfg = load_ini_config(path)
            self.assertAlmostEqual(cfg["interval"], 2.5)
            self.assertEqual(cfg["timeout"], 5)
        finally:
            os.unlink(path)

    def test_unknown_key_ignored(self):
        path = self._write("[default]\nunknown_key = something\ninterval = 1.5\n")
        try:
            cfg = load_ini_config(path)
            self.assertNotIn("unknown_key", cfg)
            self.assertAlmostEqual(cfg["interval"], 1.5)
        finally:
            os.unlink(path)

    def test_empty_file_returns_empty_dict(self):
        path = self._write("")
        try:
            cfg = load_ini_config(path)
            self.assertEqual(cfg, {})
        finally:
            os.unlink(path)

    def test_missing_file_raises(self):
        with self.assertRaises(ValueError):
            load_ini_config("/tmp/nonexistent_paraping_test_file_12345.conf")

    def test_invalid_type_raises(self):
        path = self._write("[default]\ntimeout = notanumber\n")
        try:
            with self.assertRaises(ValueError):
                load_ini_config(path)
        finally:
            os.unlink(path)

    def test_all_supported_fields(self):
        content = (
            "[default]\n"
            "interval = 2.0\n"
            "timeout = 3\n"
            "slow_threshold = 0.6\n"
            "timezone = Europe/Berlin\n"
            "color = true\n"
            "flash_on_fail = false\n"
            "bell_on_fail = yes\n"
            "panel_position = left\n"
            "pause_mode = ping\n"
            "ping_helper = /usr/bin/ping\n"
            "log_level = DEBUG\n"
            "log_file = /tmp/paraping.log\n"
            "snapshot_timezone = display\n"
        )
        path = self._write(content)
        try:
            cfg = load_ini_config(path)
            self.assertAlmostEqual(cfg["interval"], 2.0)
            self.assertEqual(cfg["timeout"], 3)
            self.assertAlmostEqual(cfg["slow_threshold"], 0.6)
            self.assertEqual(cfg["timezone"], "Europe/Berlin")
            self.assertTrue(cfg["color"])
            self.assertFalse(cfg["flash_on_fail"])
            self.assertTrue(cfg["bell_on_fail"])
            self.assertEqual(cfg["panel_position"], "left")
            self.assertEqual(cfg["pause_mode"], "ping")
            self.assertEqual(cfg["ping_helper"], "/usr/bin/ping")
            self.assertEqual(cfg["log_level"], "DEBUG")
            self.assertEqual(cfg["log_file"], "/tmp/paraping.log")
            self.assertEqual(cfg["snapshot_timezone"], "display")
        finally:
            os.unlink(path)


class TestLoadYamlConfig(unittest.TestCase):
    """Tests for load_yaml_config (requires PyYAML)."""

    def _write(self, content: str) -> str:
        f = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return f.name

    def test_basic_yaml(self):
        path = self._write("default:\n  interval: 2.0\n  timeout: 3\n  color: true\n")
        try:
            cfg = load_yaml_config(path)
            self.assertAlmostEqual(cfg["interval"], 2.0)
            self.assertEqual(cfg["timeout"], 3)
            self.assertTrue(cfg["color"])
        finally:
            os.unlink(path)

    def test_hosts_list(self):
        path = self._write("hosts:\n  - 8.8.8.8\n  - 1.1.1.1\n")
        try:
            cfg = load_yaml_config(path)
            self.assertIn("hosts", cfg)
            self.assertIn("8.8.8.8", cfg["hosts"])
            self.assertIn("1.1.1.1", cfg["hosts"])
        finally:
            os.unlink(path)

    def test_empty_yaml_returns_empty_dict(self):
        path = self._write("")
        try:
            cfg = load_yaml_config(path)
            self.assertEqual(cfg, {})
        finally:
            os.unlink(path)

    def test_invalid_yaml_raises(self):
        path = self._write("key: [unclosed\n")
        try:
            with self.assertRaises(ValueError):
                load_yaml_config(path)
        finally:
            os.unlink(path)

    def test_top_level_not_a_mapping_raises(self):
        path = self._write("- item1\n- item2\n")
        try:
            with self.assertRaises(ValueError):
                load_yaml_config(path)
        finally:
            os.unlink(path)

    def test_hosts_not_a_list_raises(self):
        path = self._write("hosts: not_a_list\n")
        try:
            with self.assertRaises(ValueError):
                load_yaml_config(path)
        finally:
            os.unlink(path)

    def test_unknown_key_ignored(self):
        path = self._write("default:\n  unknown_key: something\n  interval: 1.5\n")
        try:
            cfg = load_yaml_config(path)
            self.assertNotIn("unknown_key", cfg)
            self.assertAlmostEqual(cfg["interval"], 1.5)
        finally:
            os.unlink(path)

    def test_all_supported_fields(self):
        content = (
            "default:\n"
            "  interval: 2.0\n"
            "  timeout: 3\n"
            "  slow_threshold: 0.6\n"
            "  timezone: Europe/Berlin\n"
            "  color: true\n"
            "  flash_on_fail: false\n"
            "  bell_on_fail: true\n"
            "  panel_position: left\n"
            "  pause_mode: ping\n"
            "  ping_helper: /usr/bin/ping\n"
            "  log_level: DEBUG\n"
            "  log_file: /tmp/paraping.log\n"
            "  snapshot_timezone: display\n"
            "hosts:\n"
            "  - 8.8.8.8\n"
            "  - 1.1.1.1\n"
        )
        path = self._write(content)
        try:
            cfg = load_yaml_config(path)
            self.assertEqual(cfg["timeout"], 3)
            self.assertEqual(cfg["timezone"], "Europe/Berlin")
            self.assertTrue(cfg["color"])
            self.assertEqual(cfg["hosts"], ["8.8.8.8", "1.1.1.1"])
        finally:
            os.unlink(path)


class TestIsYamlFile(unittest.TestCase):
    """Tests for the _is_yaml_file format-detection helper."""

    def _write(self, content: str) -> str:
        f = tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return f.name

    def test_ini_detected_as_not_yaml(self):
        path = self._write("[default]\ninterval = 2.0\n")
        try:
            self.assertFalse(_is_yaml_file(path))
        finally:
            os.unlink(path)

    def test_yaml_detected_as_yaml(self):
        path = self._write("default:\n  interval: 2.0\n")
        try:
            self.assertTrue(_is_yaml_file(path))
        finally:
            os.unlink(path)

    def test_yaml_with_comment_preamble(self):
        path = self._write("# comment\ndefault:\n  interval: 2.0\n")
        try:
            self.assertTrue(_is_yaml_file(path))
        finally:
            os.unlink(path)

    def test_empty_file_returns_false(self):
        path = self._write("")
        try:
            self.assertFalse(_is_yaml_file(path))
        finally:
            os.unlink(path)

    def test_missing_file_returns_false(self):
        self.assertFalse(_is_yaml_file("/tmp/nonexistent_paraping_test_9999.conf"))


class TestLoadConfig(unittest.TestCase):
    """Tests for the load_config entry point."""

    def test_missing_file_returns_empty_dict(self):
        cfg = load_config("/tmp/nonexistent_paraping_test_12345.conf")
        self.assertEqual(cfg, {})

    def test_loads_ini_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False, encoding="utf-8") as f:
            f.write("[default]\ninterval = 3.0\n")
            path = f.name
        try:
            cfg = load_config(path)
            self.assertAlmostEqual(cfg["interval"], 3.0)
        finally:
            os.unlink(path)

    def test_loads_yaml_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("default:\n  interval: 4.0\n")
            path = f.name
        try:
            cfg = load_config(path)
            self.assertAlmostEqual(cfg["interval"], 4.0)
        finally:
            os.unlink(path)

    def test_default_path_missing_returns_empty(self):
        """When no path provided and default config doesn't exist."""
        with patch("paraping.config.DEFAULT_CONFIG_PATH", "/tmp/definitely_missing_paraping.conf"):
            cfg = load_config()
            self.assertEqual(cfg, {})


class TestApplyConfigToArgs(unittest.TestCase):
    """Tests for _apply_config_to_args merging logic."""

    def test_config_fills_none_fields(self):
        args = Namespace(interval=None, timeout=None, color=None, hosts=[], input=None)
        config = {"interval": 2.0, "timeout": 3, "color": True}
        _apply_config_to_args(args, config)
        self.assertAlmostEqual(args.interval, 2.0)
        self.assertEqual(args.timeout, 3)
        self.assertTrue(args.color)

    def test_cli_values_not_overwritten(self):
        """Values already set on the CLI (non-None) must not be overwritten."""
        args = Namespace(interval=0.5, timeout=5, color=None, hosts=[], input=None)
        config = {"interval": 2.0, "timeout": 3, "color": True}
        _apply_config_to_args(args, config)
        # CLI values preserved
        self.assertAlmostEqual(args.interval, 0.5)
        self.assertEqual(args.timeout, 5)
        # Config value applied for None field
        self.assertTrue(args.color)

    def test_config_hosts_applied_when_no_cli_hosts(self):
        args = Namespace(hosts=[], input=None)
        config = {"hosts": ["8.8.8.8", "1.1.1.1"]}
        _apply_config_to_args(args, config)
        self.assertEqual(args.hosts, ["8.8.8.8", "1.1.1.1"])

    def test_config_hosts_not_applied_when_cli_hosts_present(self):
        args = Namespace(hosts=["9.9.9.9"], input=None)
        config = {"hosts": ["8.8.8.8", "1.1.1.1"]}
        _apply_config_to_args(args, config)
        self.assertEqual(args.hosts, ["9.9.9.9"])

    def test_config_hosts_not_applied_when_input_file_present(self):
        args = Namespace(hosts=[], input="hosts.txt")
        config = {"hosts": ["8.8.8.8", "1.1.1.1"]}
        _apply_config_to_args(args, config)
        # input file takes precedence; config hosts should not be applied
        self.assertEqual(args.hosts, [])

    def test_unknown_config_key_ignored(self):
        args = Namespace(interval=None)
        config = {"interval": 2.0, "no_such_field": "value"}
        _apply_config_to_args(args, config)
        self.assertAlmostEqual(args.interval, 2.0)
        self.assertFalse(hasattr(args, "no_such_field"))

    def test_empty_config_leaves_args_unchanged(self):
        args = Namespace(interval=None, timeout=5, hosts=[])
        _apply_config_to_args(args, {})
        self.assertIsNone(args.interval)
        self.assertEqual(args.timeout, 5)


class TestHandleOptionsWithConfig(unittest.TestCase):
    """Integration tests: handle_options respects --no-config and config merging."""

    def test_no_config_flag_skips_config_file(self):
        """--no-config should prevent any config file from being loaded."""
        with patch("sys.argv", ["paraping", "--no-config", "example.com"]):
            with patch("paraping.cli.load_config") as mock_load:
                args = handle_options()
                mock_load.assert_not_called()
                self.assertTrue(args.no_config)  # no_config flag parsed correctly
                # Hardcoded defaults applied
                self.assertEqual(args.interval, 1.0)
                self.assertEqual(args.timeout, 1)

    def test_config_values_used_as_defaults(self):
        """Config values fill in fields not provided on CLI."""
        fake_config = {"interval": 2.0, "timeout": 3, "color": True, "panel_position": "left"}
        with patch("sys.argv", ["paraping", "example.com"]):
            with patch("paraping.cli.load_config", return_value=fake_config):
                args = handle_options()
                self.assertAlmostEqual(args.interval, 2.0)
                self.assertEqual(args.timeout, 3)
                self.assertTrue(args.color)
                self.assertEqual(args.panel_position, "left")

    def test_cli_args_override_config(self):
        """CLI-provided values take priority over config file values."""
        fake_config = {"interval": 2.0, "timeout": 3, "panel_position": "left"}
        with patch("sys.argv", ["paraping", "-i", "0.5", "-t", "10", "-P", "top", "example.com"]):
            with patch("paraping.cli.load_config", return_value=fake_config):
                args = handle_options()
                self.assertAlmostEqual(args.interval, 0.5)
                self.assertEqual(args.timeout, 10)
                self.assertEqual(args.panel_position, "top")

    def test_config_hosts_used_when_none_on_cli(self):
        """Config hosts are used when no hosts provided on CLI."""
        fake_config = {"hosts": ["8.8.8.8", "1.1.1.1"]}
        with patch("sys.argv", ["paraping"]):
            with patch("paraping.cli.load_config", return_value=fake_config):
                args = handle_options()
                self.assertEqual(args.hosts, ["8.8.8.8", "1.1.1.1"])

    def test_cli_hosts_override_config_hosts(self):
        """Hosts provided on CLI take priority over config hosts."""
        fake_config = {"hosts": ["8.8.8.8", "1.1.1.1"]}
        with patch("sys.argv", ["paraping", "9.9.9.9"]):
            with patch("paraping.cli.load_config", return_value=fake_config):
                args = handle_options()
                self.assertEqual(args.hosts, ["9.9.9.9"])

    def test_invalid_config_exits_with_error(self):
        """An invalid config file should cause argparse to call sys.exit."""
        with patch("sys.argv", ["paraping", "example.com"]):
            with patch("paraping.cli.load_config", side_effect=ValueError("bad config")):
                with self.assertRaises(SystemExit) as cm:
                    handle_options()
                self.assertEqual(cm.exception.code, 2)

    def test_hardcoded_defaults_applied_when_no_config(self):
        """Verify all hardcoded defaults are applied when config returns empty dict."""
        with patch("sys.argv", ["paraping", "example.com"]):
            with patch("paraping.cli.load_config", return_value={}):
                args = handle_options()
                self.assertEqual(args.timeout, 1)
                self.assertAlmostEqual(args.interval, 1.0)
                self.assertAlmostEqual(args.slow_threshold, 0.5)
                self.assertEqual(args.panel_position, "right")
                self.assertEqual(args.pause_mode, "display")
                self.assertEqual(args.snapshot_timezone, "utc")
                self.assertEqual(args.ping_helper, "./bin/ping_helper")
                self.assertEqual(args.log_level, "INFO")
                self.assertFalse(args.flash_on_fail)
                self.assertFalse(args.bell_on_fail)
                self.assertFalse(args.color)


if __name__ == "__main__":
    unittest.main()
