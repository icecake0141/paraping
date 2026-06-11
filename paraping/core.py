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
# Review for correctness and security.

"""CLI-facing wrappers around ParaPing runtime helpers."""

import logging
import socket  # noqa: F401 - tests patch this module-level symbol.
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

from paraping.runtime.constants import HISTORY_DURATION_MINUTES, MAX_HOST_THREADS, SNAPSHOT_INTERVAL_SECONDS
from paraping.runtime.hosts import HostInputReport
from paraping.runtime.hosts import build_host_infos as runtime_build_host_infos
from paraping.runtime.hosts import parse_host_file_line as runtime_parse_host_file_line
from paraping.runtime.hosts import read_input_file as runtime_read_input_file
from paraping.runtime.hosts import read_input_file_with_report as runtime_read_input_file_with_report
from paraping.runtime.paging import compute_history_page_step as runtime_compute_history_page_step
from paraping.runtime.paging import get_cached_page_step as runtime_get_cached_page_step
from paraping.runtime.rate_limit import MAX_GLOBAL_PINGS_PER_SECOND
from paraping.runtime.rate_limit import validate_global_rate_limit as runtime_validate_global_rate_limit
from paraping.runtime.term_size import extract_timeline_width_from_layout as runtime_extract_timeline_width_from_layout
from paraping.runtime.term_size import normalize_term_size as runtime_normalize_term_size
from paraping.types import HostInfo

logger = logging.getLogger(__name__)


class TerminalSizeLike(Protocol):
    """Protocol for terminal size objects with columns/lines attributes."""

    @property
    def columns(self) -> int: ...

    @property
    def lines(self) -> int: ...


def _normalize_term_size(term_size: Any) -> Optional[Any]:
    """
    Normalize terminal size to an object with .columns and .lines attributes.

    Handles tuple-like sequences, dicts, and objects with columns/lines attributes.

    Args:
        term_size: Terminal size as tuple-like sequence, dict, or object with attributes

    Returns:
        Object with .columns and .lines attributes, or None if invalid
    """
    return runtime_normalize_term_size(term_size)


def _extract_timeline_width_from_layout(layout: Any, main_width: int) -> int:
    """
    Defensively extract timeline width from compute_main_layout result.

    Supports tuple/list indexing and attribute-style extraction with fallbacks.

    Args:
        layout: Result from compute_main_layout (tuple, list, or object)
        main_width: Main panel width for fallback calculation

    Returns:
        int: Timeline width (always >= 1)
    """
    return runtime_extract_timeline_width_from_layout(layout, main_width)


def parse_host_file_line(line: str, line_number: int, input_file: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single line from the host input file.

    Args:
        line: Line of text from the file
        line_number: Line number in the file
        input_file: Path to the input file (for error messages)

    Returns:
        Dict with keys 'host', 'alias', 'ip' or None if invalid/comment
    """
    return runtime_parse_host_file_line(line=line, line_number=line_number, input_file=input_file, logger=logger)


def read_input_file(input_file: str) -> List[Dict[str, Any]]:
    """
    Read and parse hosts from an input file.

    Args:
        input_file: Path to the file containing host entries

    Returns:
        List of host info dictionaries
    """
    return runtime_read_input_file(input_file=input_file, logger=logger)


def read_input_file_with_report(input_file: str) -> Tuple[List[Dict[str, Any]], HostInputReport]:
    """
    Read and parse hosts from an input file, returning structured diagnostics.

    Args:
        input_file: Path to the file containing host entries

    Returns:
        Tuple of (parsed host entries, parse report)
    """
    return runtime_read_input_file_with_report(input_file=input_file, logger=logger)


def compute_history_page_step(
    host_infos: List[HostInfo],
    buffers: Dict[int, Any],
    stats: Dict[int, Any],
    symbols: Dict[str, str],
    panel_position: str,
    mode_label: str,
    sort_mode: str,
    filter_mode: str,
    slow_threshold: float,
    show_asn: bool,
    asn_width: int = 8,
    header_lines: int = 2,
    pulse_position: str = "none",
) -> int:
    """Wrapper for page-step computation."""
    return runtime_compute_history_page_step(
        host_infos=host_infos,
        buffers=buffers,
        stats=stats,
        symbols=symbols,
        panel_position=panel_position,
        pulse_position=pulse_position,
        mode_label=mode_label,
        sort_mode=sort_mode,
        filter_mode=filter_mode,
        slow_threshold=slow_threshold,
        show_asn=show_asn,
        asn_width=asn_width,
        header_lines=header_lines,
    )


def get_cached_page_step(
    cached_page_step: Optional[int],
    last_term_size: Optional[TerminalSizeLike],
    host_infos: List[HostInfo],
    buffers: Dict[int, Any],
    stats: Dict[int, Any],
    symbols: Dict[str, str],
    panel_position: str,
    mode_label: str,
    sort_mode: str,
    filter_mode: str,
    slow_threshold: float,
    show_asn: bool,
    pulse_position: str = "none",
) -> Tuple[int, int, Optional[TerminalSizeLike]]:
    """
    Get the page step for history navigation, using cached value if available.

    The page step is only recalculated if the terminal size has changed.
    This prevents expensive recalculation on every arrow key press.

    Returns:
        tuple: (page_step, new_cached_page_step, new_last_term_size)
    """

    return runtime_get_cached_page_step(
        cached_page_step=cached_page_step,
        last_term_size=last_term_size,
        host_infos=host_infos,
        buffers=buffers,
        stats=stats,
        symbols=symbols,
        panel_position=panel_position,
        pulse_position=pulse_position,
        mode_label=mode_label,
        sort_mode=sort_mode,
        filter_mode=filter_mode,
        slow_threshold=slow_threshold,
        show_asn=show_asn,
    )


def build_host_infos(hosts: List[Union[str, Dict[str, Any]]]) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """Build host information structures from a list of hosts."""
    return runtime_build_host_infos(hosts=hosts, logger=logger)


def validate_global_rate_limit(host_count: int, interval: float) -> Tuple[bool, float, str]:
    """
    Validate that the requested ping rate does not exceed the global limit.

    Args:
        host_count: Number of hosts to ping
        interval: Interval in seconds between pings per host

    Returns:
        Tuple of (is_valid, computed_rate, error_message)
        - is_valid: True if rate is within limit, False otherwise
        - computed_rate: The computed pings per second rate
        - error_message: Error message if invalid, empty string if valid
    """
    return runtime_validate_global_rate_limit(host_count=host_count, interval=interval)


__all__ = [
    "HISTORY_DURATION_MINUTES",
    "SNAPSHOT_INTERVAL_SECONDS",
    "MAX_HOST_THREADS",
    "MAX_GLOBAL_PINGS_PER_SECOND",
    "TerminalSizeLike",
    "_normalize_term_size",
    "_extract_timeline_width_from_layout",
    "parse_host_file_line",
    "read_input_file",
    "read_input_file_with_report",
    "compute_history_page_step",
    "get_cached_page_step",
    "build_host_infos",
    "validate_global_rate_limit",
]
