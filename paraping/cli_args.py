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

"""Command-line argument parsing for ParaPing."""

import argparse
import re
import warnings
from typing import Any, Callable, Dict

from paraping.cli_options import CLI_OPTION_SPECS, OptionSpec
from paraping.config import load_config


def add_option_from_spec(parser: argparse.ArgumentParser, spec: OptionSpec) -> None:
    """Register one option spec on the argparse parser."""
    kwargs: Dict[str, Any] = {
        "dest": spec.dest,
        "default": None,
        "help": spec.help_text,
    }
    if spec.boolean:
        kwargs["action"] = argparse.BooleanOptionalAction
    else:
        if spec.value_type is not None:
            kwargs["type"] = str.upper if spec.dest == "log_level" else spec.value_type
        if spec.choices:
            kwargs["choices"] = list(spec.choices)
    parser.add_argument(*spec.flags, **kwargs)


def apply_option_defaults(args: argparse.Namespace) -> None:
    """Apply defaults for unset values after config overlay."""
    for spec in CLI_OPTION_SPECS:
        if getattr(args, spec.dest, None) is None:
            setattr(args, spec.dest, spec.default)


def apply_config_to_args(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    """
    Overlay config file values onto a parsed argument namespace.

    Only fields that are still ``None`` (i.e. not explicitly set on the CLI)
    are updated.  Config-supplied ``hosts`` are applied only when the user has
    not provided any hosts on the CLI and has not used ``--input``/``-f``.

    Args:
        args: Namespace returned by ``argparse.ArgumentParser.parse_args()``.
        config: Dictionary of values loaded from the config file.
    """
    for key, value in config.items():
        if key == "verbose_ui_errors":
            key = "ui_log_errors"
        if key == "hosts":
            if not getattr(args, "hosts", None) and not getattr(args, "input", None):
                args.hosts = value
        elif hasattr(args, key) and getattr(args, key) is None:
            setattr(args, key, value)


def apply_deprecated_option_aliases(args: argparse.Namespace) -> None:
    """Apply deprecated option aliases after emitting warnings."""
    if args.verbose:
        warnings.warn("--verbose is deprecated; use --log-level DEBUG instead.", DeprecationWarning, stacklevel=2)
        if getattr(args, "log_level", None) is None:
            args.log_level = "DEBUG"
    if args.deprecated_verbose_ui_errors:
        warnings.warn(
            "--verbose-ui-errors is deprecated; use --ui-log-errors instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        args.ui_log_errors = True


def validate_options(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Validate parsed CLI options."""
    args.log_level = str(args.log_level).upper()
    if args.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        parser.error("--log-level must be one of DEBUG|INFO|WARNING|ERROR")
    args.verbose_ui_errors = args.ui_log_errors

    if args.timeout <= 0:
        parser.error("--timeout must be a positive integer.")
    if not 0.1 <= args.interval <= 60.0:
        parser.error("--interval must be between 0.1 and 60.0 seconds.")
    if args.group_by not in ("none", "asn", "site", "tag", "site>tag1", "tag1>site") and not re.match(
        r"^tag\d+$", args.group_by
    ):
        parser.error("--group-by must be one of none|asn|site|tag|tagN|site>tag1|tag1>site")


def handle_options(config_loader: Callable[[], Dict[str, Any]] = load_config) -> argparse.Namespace:
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(
        description="ParaPing - Perform ICMP ping operations to multiple hosts concurrently",
        epilog="Note: ParaPing enforces a global rate limit of 50 pings/sec for flood protection. "
        "The tool will exit with an error if (host_count / interval) > 50.",
    )
    for spec in CLI_OPTION_SPECS:
        add_option_from_spec(parser, spec)

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--verbose-ui-errors",
        action="store_true",
        dest="deprecated_verbose_ui_errors",
        default=False,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        default=False,
        help="Skip loading ~/.paraping.conf config file",
    )
    parser.add_argument("hosts", nargs="*", help="Hosts to ping (IP addresses or hostnames)")

    args = parser.parse_args()

    # Load and apply config file unless --no-config was given
    if not args.no_config:
        try:
            config = config_loader()
            apply_config_to_args(args, config)
        except (ValueError, ImportError) as exc:
            parser.error(str(exc))

    apply_deprecated_option_aliases(args)
    apply_option_defaults(args)
    validate_options(parser, args)
    return args
