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
Config file support for ParaPing.

This module handles loading and merging persistent settings from ~/.paraping.conf.
Supports both YAML and INI formats.

Priority order: CLI args > ~/.paraping.conf > hardcoded defaults
"""

import configparser
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.paraping.conf")

# Mapping of config field names to their expected Python types
_CONFIG_FIELD_TYPES: Dict[str, type] = {
    "interval": float,
    "timeout": int,
    "slow_threshold": float,
    "timezone": str,
    "color": bool,
    "flash_on_fail": bool,
    "bell_on_fail": bool,
    "panel_position": str,
    "pause_mode": str,
    "ping_helper": str,
    "log_level": str,
    "log_file": str,
    "snapshot_timezone": str,
}

_BOOL_TRUE_VALUES = frozenset(("true", "yes", "1", "on"))
_BOOL_FALSE_VALUES = frozenset(("false", "no", "0", "off"))


def _parse_bool(value: str) -> bool:
    """Parse a boolean value from a string representation."""
    lower = value.lower()
    if lower in _BOOL_TRUE_VALUES:
        return True
    if lower in _BOOL_FALSE_VALUES:
        return False
    raise ValueError(f"Cannot parse '{value}' as a boolean. Use true/false, yes/no, 1/0, or on/off.")


def _coerce_field(key: str, raw_value: Any) -> Any:
    """Coerce a raw config value to the expected type for the given field name."""
    if key not in _CONFIG_FIELD_TYPES:
        return raw_value
    field_type = _CONFIG_FIELD_TYPES[key]
    if isinstance(raw_value, field_type):
        return raw_value
    try:
        if field_type is bool:
            if isinstance(raw_value, bool):
                return raw_value
            return _parse_bool(str(raw_value))
        return field_type(raw_value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid value for config field '{key}': expected {field_type.__name__}, got {raw_value!r}") from exc


def load_ini_config(path: str) -> Dict[str, Any]:
    """
    Load and parse an INI-format config file.

    Supports ``=`` and ``:`` as key-value delimiters.
    The ``[hosts]`` section accepts bare hostname/IP lines (no ``=`` required).

    Args:
        path: Path to the INI config file.

    Returns:
        Dictionary of config values.

    Raises:
        ValueError: On parse errors or invalid field values.
    """
    parser = configparser.ConfigParser(allow_no_value=True, delimiters=("=", ":"))
    try:
        read_files = parser.read(path, encoding="utf-8")
    except configparser.Error as exc:
        raise ValueError(f"Invalid config file '{path}': {exc}") from exc

    if not read_files:
        raise ValueError(f"Config file '{path}' could not be read.")

    result: Dict[str, Any] = {}

    if parser.has_section("default"):
        for key, raw_value in parser.items("default"):
            if key not in _CONFIG_FIELD_TYPES:
                logger.warning("Unknown config key '%s' in [default] section of '%s'; ignoring.", key, path)
                continue
            if raw_value is None:
                logger.warning("Config key '%s' has no value in '%s'; ignoring.", key, path)
                continue
            result[key] = _coerce_field(key, raw_value)

    if parser.has_section("hosts"):
        hosts: List[str] = []
        for key, value in parser.items("hosts"):
            # Lines without a value: the "key" itself is the host entry
            host_entry = (value.strip() if value else None) or key.strip()
            if host_entry:
                hosts.append(host_entry)
        if hosts:
            result["hosts"] = hosts

    return result


def load_yaml_config(path: str) -> Dict[str, Any]:
    """
    Load and parse a YAML-format config file.

    Requires PyYAML (``pip install pyyaml``).  Uses ``yaml.safe_load`` to
    prevent arbitrary code execution.

    Args:
        path: Path to the YAML config file.

    Returns:
        Dictionary of config values.

    Raises:
        ImportError: If PyYAML is not installed.
        ValueError: On parse errors or invalid file content.
    """
    try:
        import yaml  # type: ignore[import-untyped]  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required for YAML config files. Install it with: pip install pyyaml"
        ) from exc

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in config file '{path}': {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Cannot read config file '{path}': {exc}") from exc

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file '{path}' must contain a YAML mapping at the top level, got {type(data).__name__}.")

    result: Dict[str, Any] = {}

    default_section = data.get("default") or {}
    if not isinstance(default_section, dict):
        raise ValueError(f"The 'default' section in '{path}' must be a YAML mapping.")
    for key, value in default_section.items():
        if key not in _CONFIG_FIELD_TYPES:
            logger.warning("Unknown config key '%s' in 'default' section of '%s'; ignoring.", key, path)
            continue
        if value is None:
            continue
        result[key] = _coerce_field(key, value)

    hosts_section = data.get("hosts")
    if hosts_section is not None:
        if not isinstance(hosts_section, list):
            raise ValueError(f"The 'hosts' section in '{path}' must be a YAML list.")
        hosts = [str(h).strip() for h in hosts_section if h is not None and str(h).strip()]
        if hosts:
            result["hosts"] = hosts

    return result


def _is_yaml_file(path: str) -> bool:
    """
    Heuristically determine whether a config file uses YAML or INI format.

    INI files begin with a ``[section]`` header on the first non-blank,
    non-comment line.  Anything else is treated as YAML.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    return not stripped.startswith("[")
    except OSError:
        pass
    return False


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load persistent settings from a config file.

    Auto-detects whether the file uses YAML or INI format.
    Returns an empty dict if the config file does not exist.

    Args:
        path: Path to the config file.  Defaults to ``~/.paraping.conf``.

    Returns:
        Dictionary of config values.

    Raises:
        ValueError: If the file exists but cannot be parsed.
        ImportError: If a YAML file is found but PyYAML is not installed.
    """
    if path is None:
        path = DEFAULT_CONFIG_PATH

    if not os.path.exists(path):
        return {}

    if _is_yaml_file(path):
        logger.debug("Loading YAML config from '%s'.", path)
        return load_yaml_config(path)

    logger.debug("Loading INI config from '%s'.", path)
    return load_ini_config(path)
