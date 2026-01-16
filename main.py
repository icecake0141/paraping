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
ParaPing - Interactive terminal-based ICMP ping monitor.

This module provides an interactive, terminal-based ICMP monitor that pings multiple
hosts concurrently and visualizes results as a live timeline or sparkline. It includes
useful operator controls like sorting, filtering, pause modes, snapshots, and optional
ASN/rDNS display for fast network triage.

Features:
- Concurrent ICMP ping to multiple hosts using a capability-based helper binary
- Live timeline or sparkline visualization with success/slow/fail markers
- Real-time statistics and aggregate counts with TTL display
- Sort and filter results by failures, streaks, latency, or host name
- Toggle display name mode: IP, reverse DNS, or alias
- Optional ASN display (fetched from Team Cymru)
- Configurable timezone for timestamps and snapshot naming
- History navigation to review past ping results
- Pause modes and snapshot export functionality
"""

import argparse
import copy
import ipaddress
import math
import os
import queue
import re
import select
import socket
import sys
import termios
import threading
import time
import tty
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ping_wrapper import ping_with_helper


# Constants for time navigation feature
HISTORY_DURATION_MINUTES = 30  # Store up to 30 minutes of history
SNAPSHOT_INTERVAL_SECONDS = 1.0  # Take snapshot every second
ARROW_KEY_READ_TIMEOUT = 0.05  # Timeout for reading arrow key escape sequences
ACTIVITY_INDICATOR_WIDTH = 10
ACTIVITY_INDICATOR_EXPANDED_WIDTH = 20
ACTIVITY_INDICATOR_HEIGHT = 4
ACTIVITY_INDICATOR_SPEED_HZ = 8
LAST_RENDER_LINES = None
ANSI_RESET = "\x1b[0m"
MAX_HOST_THREADS = 128  # Hard cap to avoid unbounded thread growth.
STATUS_COLORS = {
    "success": "\x1b[37m",  # White
    "slow": "\x1b[33m",  # Yellow
    "fail": "\x1b[31m",  # Red
}
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


# Get terminal size by querying the actual terminal, not env vars
def get_terminal_size(fallback=(80, 24)):
    """
    Get the terminal size by directly querying the terminal.

    This function uses os.get_terminal_size() which queries the actual
    terminal instead of checking COLUMNS/LINES environment variables
    first (like shutil does). This ensures the size updates when the
    terminal is resized.

    Args:
        fallback: Tuple of (columns, lines) to use if terminal size
                  cannot be determined

    Returns:
        os.terminal_size with columns and lines attributes
    """
    try:
        # Try stdout first
        if sys.stdout.isatty():
            return os.get_terminal_size(sys.stdout.fileno())
    except (AttributeError, ValueError, OSError):
        pass

    try:
        # Try stderr if stdout fails
        if sys.stderr.isatty():
            return os.get_terminal_size(sys.stderr.fileno())
    except (AttributeError, ValueError, OSError):
        pass

    try:
        # Try stdin as last resort
        if sys.stdin.isatty():
            return os.get_terminal_size(sys.stdin.fileno())
    except (AttributeError, ValueError, OSError):
        pass

    # Fall back to default size
    return os.terminal_size(fallback)


def strip_ansi(text):
    return ANSI_ESCAPE_RE.sub("", text)


def visible_len(text):
    return len(strip_ansi(text))


def truncate_visible(text, width):
    result = []
    visible_count = 0
    index = 0
    while index < len(text) and visible_count < width:
        if text[index] == "\x1b":
            match = ANSI_ESCAPE_RE.match(text, index)
            if match:
                result.append(match.group(0))
                index = match.end()
                continue
        result.append(text[index])
        index += 1
        visible_count += 1
    truncated = "".join(result)
    if "\x1b[" in truncated and not truncated.endswith(ANSI_RESET):
        truncated += ANSI_RESET
    return truncated, visible_count


def pad_visible(text, width):
    truncated, visible_count = truncate_visible(text, width)
    if visible_count < width:
        truncated += " " * (width - visible_count)
    return truncated


def rjust_visible(text, width):
    padding = width - visible_len(text)
    if padding <= 0:
        return text
    return f"{' ' * padding}{text}"


def colorize_text(text, status, use_color):
    if not use_color or not status:
        return text
    color = STATUS_COLORS.get(status)
    if not color:
        return text
    return f"{color}{text}{ANSI_RESET}"


def status_from_symbol(symbol, symbols):
    for status, status_symbol in symbols.items():
        if symbol == status_symbol:
            return status
    return None


def latest_status_from_timeline(timeline, symbols):
    if not timeline:
        return None
    return status_from_symbol(timeline[-1], symbols)


def build_colored_timeline(timeline, symbols, use_color):
    return "".join(
        colorize_text(symbol, status_from_symbol(symbol, symbols), use_color)
        for symbol in timeline
    )


def build_colored_sparkline(sparkline, status_symbols, symbols, use_color):
    if not use_color:
        return sparkline
    colored = []
    for char, symbol in zip(sparkline, status_symbols):
        status = status_from_symbol(symbol, symbols)
        colored.append(colorize_text(char, status, use_color))
    return "".join(colored)


def build_activity_indicator(
    now_utc,
    width=ACTIVITY_INDICATOR_WIDTH,
    max_height=ACTIVITY_INDICATOR_HEIGHT,
    speed_hz=ACTIVITY_INDICATOR_SPEED_HZ,
):
    if width <= 0:
        return ""
    tick = int(now_utc.timestamp() * speed_hz)
    span = max(1, width - 1)
    cycle = span * 2
    position = tick % cycle
    if position > span:
        position = cycle - position
    spark_chars = "▁▂▃▄▅▆▇█"
    peak = min(max_height, len(spark_chars) - 1)
    levels = []
    for index in range(width):
        height = max(0, peak - abs(index - position))
        levels.append(spark_chars[height] if height > 0 else spark_chars[0])
    return "".join(levels)


def compute_activity_indicator_width(
    panel_width,
    header_text,
    default_width=ACTIVITY_INDICATOR_WIDTH,
    expanded_width=ACTIVITY_INDICATOR_EXPANDED_WIDTH,
):
    if panel_width <= 0:
        return 0
    remaining = panel_width - visible_len(header_text) - 1
    if remaining <= 0:
        return 0
    if remaining >= expanded_width:
        return expanded_width
    if remaining >= default_width:
        return default_width
    return remaining


# A handler for command line options


def handle_options():

    parser = argparse.ArgumentParser(
        description="ParaPing - Perform ICMP ping operations to multiple hosts concurrently"
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=1,
        help="Timeout in seconds for each ping (default: 1)",
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=0,
        help="Number of ping attempts per host (default: 0 for infinite)",
    )
    parser.add_argument(
        "-s",
        "--slow-threshold",
        type=float,
        default=0.5,
        help="Threshold in seconds for slow ping (default: 0.5)",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=1.0,
        help="Interval in seconds between pings per host (default: 1.0, range: 0.1-60.0)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output, showing detailed ping results",
    )
    parser.add_argument(
        "-f",
        "--input",
        type=str,
        help="Input file containing list of hosts (one per line, format: IP,alias)",
        required=False,
    )
    parser.add_argument(
        "-P",
        "--panel-position",
        type=str,
        default="right",
        choices=["right", "left", "top", "bottom", "none"],
        help="Summary panel position (right|left|top|bottom|none)",
    )
    parser.add_argument(
        "-m",
        "--pause-mode",
        type=str,
        default="display",
        choices=["display", "ping"],
        help="Pause behavior: display (stop updates only) or ping (pause ping + updates)",
    )
    parser.add_argument(
        "-z",
        "--timezone",
        type=str,
        default=None,
        help="Display timezone (IANA name, e.g. Asia/Tokyo). Defaults to UTC.",
    )
    parser.add_argument(
        "-Z",
        "--snapshot-timezone",
        type=str,
        default="utc",
        choices=["utc", "display"],
        help="Timezone used in snapshot filename (utc|display). Defaults to utc.",
    )
    parser.add_argument(
        "-F",
        "--flash-on-fail",
        action="store_true",
        help="Flash screen (white background) when ping fails",
    )
    parser.add_argument(
        "-B",
        "--bell-on-fail",
        action="store_true",
        help="Ring terminal bell when ping fails",
    )
    parser.add_argument(
        "-C",
        "--color",
        action="store_true",
        help="Enable colored output (blue=success, yellow=slow, red=fail)",
    )
    parser.add_argument(
        "-H",
        "--ping-helper",
        type=str,
        default="./ping_helper",
        help="Path to ping_helper binary (default: ./ping_helper)",
    )
    parser.add_argument(
        "hosts", nargs="*", help="Hosts to ping (IP addresses or hostnames)"
    )

    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be a positive integer.")
    if not 0.1 <= args.interval <= 60.0:
        parser.error("--interval must be between 0.1 and 60.0 seconds.")
    return args


# Read input file. The file contains a list of hosts (IP addresses and aliases)


def parse_host_file_line(line, line_number, input_file):
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = [part.strip() for part in stripped.split(",")]
    if len(parts) != 2:
        print(
            f"Warning: Invalid host entry at {input_file}:{line_number}. "
            "Expected format 'IP,alias'.",
            file=sys.stderr,
        )
        return None
    ip_text, alias = parts
    if not ip_text or not alias:
        print(
            f"Warning: Invalid host entry at {input_file}:{line_number}. "
            "IP address and alias are required.",
            file=sys.stderr,
        )
        return None
    try:
        ip_obj = ipaddress.ip_address(ip_text)
    except ValueError:
        print(
            f"Warning: Invalid IP address at {input_file}:{line_number}: '{ip_text}'.",
            file=sys.stderr,
        )
        return None
    if ip_obj.version != 4:
        print(
            f"Warning: Unsupported IP version at {input_file}:{line_number}: '{ip_text}'.",
            file=sys.stderr,
        )
        return None
    return {"host": ip_text, "alias": alias, "ip": ip_text}


def read_input_file(input_file):
    host_list = []
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                entry = parse_host_file_line(line, line_number, input_file)
                if entry is not None:
                    host_list.append(entry)
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        return []
    except PermissionError:
        print(f"Error: Permission denied reading file '{input_file}'.")
        return []
    except Exception as e:
        print(f"Error reading input file '{input_file}': {e}")
        return []

    return host_list


# Ping a single host


def ping_host(
    host,
    timeout,
    count,
    slow_threshold,
    verbose,
    pause_event=None,
    stop_event=None,
    interval=1.0,
    helper_path="./ping_helper",
):
    """
    Ping a single host with the specified parameters.

    Args:
        host: The hostname or IP address to ping
        timeout: Timeout in seconds for each ping
        count: Number of ping attempts (0 for infinite)
        verbose: Whether to show detailed output
        pause_event: Event to pause pinging
        stop_event: Event to stop pinging and exit
        interval: Interval in seconds between pings
        helper_path: Path to ping_helper binary

    Yields:
        A dict with host, sequence, status, and rtt
    """
    if verbose:
        print(f"\n--- Pinging {host} ---")

    if not os.path.exists(helper_path):
        message = (
            f"ping_helper binary not found at {helper_path}. "
            "Please run 'make build' and 'sudo make setcap'."
        )
        if verbose:
            print(message)
        yield {
            "host": host,
            "sequence": 1,
            "status": "fail",
            "rtt": None,
            "ttl": None,
        }
        return

    i = 0
    while True:
        if stop_event is not None and stop_event.is_set():
            break
        # Check if we should stop (only when count is not 0)
        if count > 0 and i >= count:
            break

        if pause_event is not None:
            while pause_event.is_set():
                if stop_event is not None and stop_event.is_set():
                    return
                time.sleep(0.05)
        try:
            rtt_ms, ttl = ping_with_helper(
                host, timeout_ms=int(timeout * 1000), helper_path=helper_path
            )
            if rtt_ms is not None:
                rtt = rtt_ms / 1000.0
                status = "slow" if rtt >= slow_threshold else "success"
                if verbose:
                    print(f"Reply from {host}: seq={i+1} rtt={rtt:.3f}s ttl={ttl}")
                yield {
                    "host": host,
                    "sequence": i + 1,
                    "status": status,
                    "rtt": rtt,
                    "ttl": ttl,
                }
            else:
                if verbose:
                    print(f"No reply from {host}: seq={i+1}")
                yield {
                    "host": host,
                    "sequence": i + 1,
                    "status": "fail",
                    "rtt": None,
                    "ttl": None,
                }
        except Exception as e:
            if verbose:
                print(f"Error pinging {host}: {e}")
            yield {
                "host": host,
                "sequence": i + 1,
                "status": "fail",
                "rtt": None,
                "ttl": None,
            }

        i += 1

        # Sleep for interval between pings (but not after the last ping when count > 0)
        if count == 0 or i < count:
            if stop_event is None or not stop_event.is_set():
                time.sleep(interval)


def compute_main_layout(host_labels, width, height, header_lines=2):
    max_host_len = max((len(host) for host in host_labels), default=4)
    label_width = min(max_host_len, max(10, width // 3))
    timeline_width = max(1, width - label_width - 3)
    visible_hosts = max(1, height - header_lines)

    return width, label_width, timeline_width, visible_hosts


def compute_panel_sizes(
    term_width,
    term_height,
    panel_position,
    min_panel_width=30,
    min_panel_height=5,
    min_main_width=20,
    min_main_height=5,
    gap=1,
):
    if panel_position == "none":
        return term_width, term_height, 0, 0, "none"

    if term_width < min_main_width or term_height < min_main_height:
        return term_width, term_height, 0, 0, "none"

    if panel_position in ("left", "right"):
        summary_width = max(min_panel_width, term_width // 4)
        main_width = term_width - summary_width - gap
        if main_width < min_main_width or summary_width < min_panel_width:
            return term_width, term_height, 0, 0, "none"
        return main_width, term_height, summary_width, term_height, panel_position

    if panel_position in ("top", "bottom"):
        summary_height = max(min_panel_height, term_height // 4)
        main_height = term_height - summary_height - gap
        if main_height < min_main_height or summary_height < min_panel_height:
            return term_width, term_height, 0, 0, "none"
        return term_width, main_height, term_width, summary_height, panel_position

    return term_width, term_height, 0, 0, "none"


def format_status_line(host, timeline, label_width):
    return f"{pad_visible(host, label_width)} | {timeline}"


def resize_buffers(buffers, timeline_width, symbols):
    for host, host_buffers in buffers.items():
        if host_buffers["timeline"].maxlen != timeline_width:
            host_buffers["timeline"] = deque(
                host_buffers["timeline"], maxlen=timeline_width
            )
        if host_buffers["rtt_history"].maxlen != timeline_width:
            host_buffers["rtt_history"] = deque(
                host_buffers["rtt_history"], maxlen=timeline_width
            )
        if host_buffers["time_history"].maxlen != timeline_width:
            host_buffers["time_history"] = deque(
                host_buffers["time_history"], maxlen=timeline_width
            )
        if host_buffers["ttl_history"].maxlen != timeline_width:
            host_buffers["ttl_history"] = deque(
                host_buffers["ttl_history"], maxlen=timeline_width
            )
        for status in symbols:
            if host_buffers["categories"][status].maxlen != timeline_width:
                host_buffers["categories"][status] = deque(
                    host_buffers["categories"][status], maxlen=timeline_width
                )


def pad_lines(lines, width, height):
    padded = [pad_visible(line, width) for line in lines[:height]]
    while len(padded) < height:
        padded.append("".ljust(width))
    return padded


def resolve_boxed_dimensions(width, height, boxed):
    if not boxed or width < 2 or height < 3:
        return width, height, False
    return width - 2, height - 2, True


def box_lines(lines, width, height):
    inner_width, inner_height, can_box = resolve_boxed_dimensions(width, height, True)
    if not can_box:
        return pad_lines(lines, width, height)
    inner_lines = pad_lines(lines, inner_width, inner_height)
    border = "-" * inner_width
    boxed = [f"+{border}+"]
    boxed.extend(f"|{line}|" for line in inner_lines)
    boxed.append(f"+{border}+")
    return boxed


def compute_summary_data(
    host_infos,
    display_names,
    buffers,
    stats,
    symbols,
    ordered_host_ids=None,
):
    summary = []
    success_symbols = {symbols["success"], symbols["slow"]}
    info_by_id = {info["id"]: info for info in host_infos}
    host_ids = (
        ordered_host_ids
        if ordered_host_ids is not None
        else [info["id"] for info in host_infos]
    )
    for host_id in host_ids:
        info = info_by_id.get(host_id)
        if info is None:
            continue
        display_name = display_names.get(host_id, info["alias"])
        total = stats[host_id]["total"]
        success = stats[host_id]["success"] + stats[host_id]["slow"]
        fail = stats[host_id]["fail"]
        success_rate = (success / total * 100) if total > 0 else 0.0
        loss_rate = (fail / total * 100) if total > 0 else 0.0
        timeline = list(buffers[host_id]["timeline"])
        streak_type = None
        streak_length = 0
        if timeline:
            last = timeline[-1]
            if last in success_symbols:
                streak_type = "success"
                for symbol in reversed(timeline):
                    if symbol in success_symbols:
                        streak_length += 1
                    else:
                        break
            elif last == symbols["fail"]:
                streak_type = "fail"
                for symbol in reversed(timeline):
                    if symbol == symbols["fail"]:
                        streak_length += 1
                    else:
                        break
        avg_rtt_ms = None
        if stats[host_id]["rtt_count"] > 0:
            avg_rtt_ms = stats[host_id]["rtt_sum"] / stats[host_id]["rtt_count"] * 1000
        stddev_ms = None
        if stats[host_id]["rtt_count"] > 1:
            mean_rtt = stats[host_id]["rtt_sum"] / stats[host_id]["rtt_count"]
            mean_square = (
                stats[host_id].get("rtt_sum_sq", 0.0) / stats[host_id]["rtt_count"]
            )
            variance = max(0.0, mean_square - mean_rtt * mean_rtt)
            stddev_ms = math.sqrt(variance) * 1000
        rtt_values = [
            value for value in buffers[host_id]["rtt_history"] if value is not None
        ]
        jitter_ms = None
        if len(rtt_values) >= 2:
            diffs = [
                abs(current - previous)
                for previous, current in zip(rtt_values, rtt_values[1:])
            ]
            jitter_ms = sum(diffs) / len(diffs) * 1000
        latest_ttl = latest_ttl_value(buffers[host_id]["ttl_history"])
        summary.append(
            {
                "host": display_name,
                "success_rate": success_rate,
                "loss_rate": loss_rate,
                "streak_type": streak_type,
                "streak_length": streak_length,
                "avg_rtt_ms": avg_rtt_ms,
                "jitter_ms": jitter_ms,
                "stddev_ms": stddev_ms,
                "latest_ttl": latest_ttl,
            }
        )
    return summary


def build_streak_label(entry):
    streak_label = "-"
    if entry["streak_type"] == "fail":
        streak_label = f"F{entry['streak_length']}"
    elif entry["streak_type"] == "success":
        streak_label = f"S{entry['streak_length']}"
    return streak_label


def build_summary_suffix(entry, summary_mode):
    if summary_mode == "rtt":
        avg_rtt = (
            f"{entry['avg_rtt_ms']:.1f} ms"
            if entry.get("avg_rtt_ms") is not None
            else "n/a"
        )
        jitter = (
            f"{entry['jitter_ms']:.1f} ms"
            if entry.get("jitter_ms") is not None
            else "n/a"
        )
        stddev = (
            f"{entry['stddev_ms']:.1f} ms"
            if entry.get("stddev_ms") is not None
            else "n/a"
        )
        return f": avg rtt {avg_rtt} jitter {jitter} stddev {stddev}"
    if summary_mode == "ttl":
        latest_ttl = entry.get("latest_ttl")
        return f": ttl {latest_ttl}" if latest_ttl is not None else ": ttl n/a"
    if summary_mode == "streak":
        return f": streak {build_streak_label(entry)}"
    return f": ok {entry['success_rate']:.1f}% loss {entry['loss_rate']:.1f}%"


def build_summary_all_suffix(entry):
    avg_rtt = (
        f"{entry['avg_rtt_ms']:.1f} ms"
        if entry.get("avg_rtt_ms") is not None
        else "n/a"
    )
    jitter = (
        f"{entry['jitter_ms']:.1f} ms"
        if entry.get("jitter_ms") is not None
        else "n/a"
    )
    stddev = (
        f"{entry['stddev_ms']:.1f} ms"
        if entry.get("stddev_ms") is not None
        else "n/a"
    )
    latest_ttl = entry.get("latest_ttl")
    ttl_value = f"{latest_ttl}" if latest_ttl is not None else "n/a"
    streak_label = build_streak_label(entry)
    parts = [
        f"ok {entry['success_rate']:.1f}% loss {entry['loss_rate']:.1f}%",
        f"avg rtt {avg_rtt}",
        f"jitter {jitter}",
        f"stddev {stddev}",
        f"ttl {ttl_value}",
        f"streak {streak_label}",
    ]
    return f": {' | '.join(parts)}"


def can_render_full_summary(summary_data, width):
    if not summary_data:
        return False
    max_suffix_len = max(
        len(build_summary_all_suffix(entry)) for entry in summary_data
    )
    return width >= max_suffix_len + 1


def format_summary_line(entry, width, summary_mode, prefer_all=False):
    status_suffix = None
    if prefer_all:
        all_suffix = build_summary_all_suffix(entry)
        if width >= len(all_suffix) + 1:
            status_suffix = all_suffix
    if status_suffix is None:
        status_suffix = build_summary_suffix(entry, summary_mode)

    available_for_host = width - len(status_suffix)
    if available_for_host > 0:
        host_display = entry["host"][:available_for_host]
    else:
        host_display = entry["host"]

    full_line = f"{host_display}{status_suffix}"
    return full_line[:width]


def render_summary_view(
    summary_data,
    width,
    height,
    summary_mode,
    prefer_all=False,
    boxed=False,
):
    if width <= 0 or height <= 0:
        return []

    render_width, render_height, can_box = resolve_boxed_dimensions(
        width, height, boxed
    )
    mode_labels = {
        "rates": "Rates",
        "rtt": "Avg RTT",
        "ttl": "TTL",
        "streak": "Streak",
    }
    allow_all = prefer_all and can_render_full_summary(summary_data, render_width)
    mode_label = "All" if allow_all else mode_labels.get(summary_mode, "Rates")
    lines = [f"Summary ({mode_label})", "-" * render_width]
    for entry in summary_data:
        lines.append(
            format_summary_line(entry, render_width, summary_mode, prefer_all=allow_all)
        )

    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


def build_sparkline(rtt_values, status_symbols, fail_symbol):
    spark_chars = "▁▂▃▄▅▆▇█"
    if rtt_values:
        numeric_values = [value for value in rtt_values if value is not None]
    else:
        numeric_values = []

    if numeric_values:
        min_val = min(numeric_values)
        max_val = max(numeric_values)
        span = max_val - min_val
        if span == 0:
            span = 1
        indices = []
        for value in rtt_values:
            if value is None:
                indices.append(0)
            else:
                idx = round((value - min_val) / span * (len(spark_chars) - 1))
                indices.append(max(0, min(len(spark_chars) - 1, idx)))
    else:
        indices = []
        for symbol in status_symbols:
            if symbol == fail_symbol:
                indices.append(0)
            else:
                indices.append(len(spark_chars) - 1)

    return "".join(spark_chars[idx] for idx in indices)


def render_timeline_view(
    display_entries,
    buffers,
    symbols,
    width,
    height,
    header,
    use_color=False,
    scroll_offset=0,
    header_lines=2,
    boxed=False,
):
    if width <= 0 or height <= 0:
        return []

    render_width, render_height, can_box = resolve_boxed_dimensions(
        width, height, boxed
    )
    host_labels = [entry[1] for entry in display_entries]
    render_width, label_width, timeline_width, visible_hosts = compute_main_layout(
        host_labels, render_width, render_height, header_lines
    )
    max_offset = max(0, len(display_entries) - visible_hosts)
    scroll_offset = min(max(scroll_offset, 0), max_offset)
    truncated_entries = display_entries[scroll_offset : scroll_offset + visible_hosts]

    resize_buffers(buffers, timeline_width, symbols)

    lines = []
    lines.append(header)
    lines.append("".join("-" for _ in range(render_width)))
    for host, label in truncated_entries:
        timeline_symbols = list(buffers[host]["timeline"])
        timeline = build_colored_timeline(timeline_symbols, symbols, use_color)
        timeline = rjust_visible(timeline, timeline_width)
        status = latest_status_from_timeline(timeline_symbols, symbols)
        colored_label = colorize_text(label, status, use_color)
        lines.append(format_status_line(colored_label, timeline, label_width))

    if len(display_entries) > len(truncated_entries) and len(lines) < height:
        remaining = len(display_entries) - len(truncated_entries)
        lines.append(f"... ({remaining} host(s) not shown)")

    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


def render_sparkline_view(
    display_entries,
    buffers,
    symbols,
    width,
    height,
    header,
    use_color=False,
    scroll_offset=0,
    header_lines=2,
    boxed=False,
):
    if width <= 0 or height <= 0:
        return []

    render_width, render_height, can_box = resolve_boxed_dimensions(
        width, height, boxed
    )
    host_labels = [entry[1] for entry in display_entries]
    render_width, label_width, timeline_width, visible_hosts = compute_main_layout(
        host_labels, render_width, render_height, header_lines
    )
    max_offset = max(0, len(display_entries) - visible_hosts)
    scroll_offset = min(max(scroll_offset, 0), max_offset)
    truncated_entries = display_entries[scroll_offset : scroll_offset + visible_hosts]

    resize_buffers(buffers, timeline_width, symbols)

    lines = []
    lines.append(header)
    lines.append("".join("-" for _ in range(render_width)))
    for host, label in truncated_entries:
        rtt_values = list(buffers[host]["rtt_history"])[-timeline_width:]
        status_symbols = list(buffers[host]["timeline"])[-timeline_width:]
        sparkline = build_sparkline(rtt_values, status_symbols, symbols["fail"])
        sparkline = build_colored_sparkline(
            sparkline, status_symbols, symbols, use_color
        )
        sparkline = rjust_visible(sparkline, timeline_width)
        status = latest_status_from_timeline(status_symbols, symbols)
        colored_label = colorize_text(label, status, use_color)
        lines.append(format_status_line(colored_label, sparkline, label_width))

    if len(display_entries) > len(truncated_entries) and len(lines) < height:
        remaining = len(display_entries) - len(truncated_entries)
        lines.append(f"... ({remaining} host(s) not shown)")

    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


def render_main_view(
    display_entries,
    buffers,
    symbols,
    width,
    height,
    mode_label,
    display_mode,
    paused,
    timestamp,
    now_utc,
    use_color=False,
    scroll_offset=0,
    header_lines=2,
    boxed=False,
):
    pause_label = "PAUSED" if paused else "LIVE"
    header_base = (
        f"ParaPing - {pause_label} results [{mode_label} | {display_mode}] {timestamp}"
    )
    activity_indicator = ""
    if not paused:
        indicator_width = compute_activity_indicator_width(width, header_base)
        if indicator_width > 0:
            activity_indicator = build_activity_indicator(
                now_utc, width=indicator_width
            )
    if activity_indicator:
        header = f"{header_base} {activity_indicator}"
    else:
        header = header_base
    if display_mode == "sparkline":
        return render_sparkline_view(
            display_entries,
            buffers,
            symbols,
            width,
            height,
            header,
            use_color,
            scroll_offset,
            header_lines,
            boxed,
        )
    return render_timeline_view(
        display_entries,
        buffers,
        symbols,
        width,
        height,
        header,
        use_color,
        scroll_offset,
        header_lines,
        boxed,
    )


def compute_fail_streak(timeline, fail_symbol):
    streak = 0
    for symbol in reversed(timeline):
        if symbol == fail_symbol:
            streak += 1
        else:
            break
    return streak


def latest_ttl_value(ttl_history):
    if not ttl_history:
        return None
    return ttl_history[-1]


def latest_rtt_value(rtt_history):
    if not rtt_history:
        return None
    return rtt_history[-1]


def build_display_entries(
    host_infos,
    display_names,
    buffers,
    stats,
    symbols,
    sort_mode,
    filter_mode,
    slow_threshold,
):
    entries = []
    for info in host_infos:
        host_id = info["id"]
        timeline = buffers[host_id]["timeline"]
        latest_rtt = latest_rtt_value(buffers[host_id]["rtt_history"])
        fail_streak = compute_fail_streak(timeline, symbols["fail"])
        fail_count = stats[host_id]["fail"]

        include = True
        if filter_mode == "failures":
            include = fail_count > 0
        elif filter_mode == "latency":
            include = latest_rtt is not None and latest_rtt >= slow_threshold

        if include:
            entries.append(
                {
                    "host_id": host_id,
                    "label": display_names.get(host_id, info["alias"]),
                    "fail_count": fail_count,
                    "fail_streak": fail_streak,
                    "latest_rtt": latest_rtt,
                }
            )

    if sort_mode == "failures":
        entries.sort(key=lambda item: (item["fail_count"], item["label"]), reverse=True)
    elif sort_mode == "streak":
        entries.sort(
            key=lambda item: (item["fail_streak"], item["label"]), reverse=True
        )
    elif sort_mode == "latency":
        entries.sort(
            key=lambda item: ((item["latest_rtt"] or -1.0), item["label"]),
            reverse=True,
        )
    elif sort_mode == "host":
        entries.sort(key=lambda item: item["label"])

    return [(entry["host_id"], entry["label"]) for entry in entries]


def build_status_line(
    sort_mode,
    filter_mode,
    summary_mode,
    paused,
    status_message=None,
    summary_all=False,
    summary_fullscreen=False,
):
    sort_labels = {
        "failures": "Failure Count",
        "streak": "Failure Streak",
        "latency": "Latest Latency",
        "host": "Host Name",
    }
    filter_labels = {
        "failures": "Failures Only",
        "latency": "High Latency Only",
        "all": "All Items",
    }
    summary_labels = {
        "rates": "Rates",
        "rtt": "Avg RTT",
        "ttl": "TTL",
        "streak": "Streak",
    }
    sort_label = sort_labels.get(sort_mode, sort_mode)
    filter_label = filter_labels.get(filter_mode, filter_mode)
    summary_label = "All" if summary_all else summary_labels.get(summary_mode, summary_mode)
    status = f"Sort: {sort_label} | Filter: {filter_label} | Summary: {summary_label}"
    if summary_fullscreen:
        status += " | Summary View: Fullscreen"
    if paused:
        status += " | PAUSED"
    if status_message:
        status += f" | {status_message}"
    return status


def render_status_box(status_line, width):
    if width <= 0:
        return []
    if width < 2:
        return [status_line[:width]]
    inner_width = width - 2
    content = pad_visible(status_line[:inner_width], inner_width)
    border = "-" * inner_width
    return [f"+{border}+", f"|{content}|", f"+{border}+"]


def toggle_panel_visibility(
    current_position, last_visible_position, default_position="right"
):
    if current_position == "none":
        restored_position = last_visible_position or default_position
        return restored_position, restored_position
    return "none", current_position


def cycle_panel_position(current_position, default_position="right"):
    positions = ["left", "right", "top", "bottom"]
    if current_position not in positions:
        return default_position if default_position in positions else positions[0]
    next_index = (positions.index(current_position) + 1) % len(positions)
    return positions[next_index]


def render_help_view(width, height, boxed=False):
    render_width, render_height, can_box = resolve_boxed_dimensions(
        width, height, boxed
    )
    lines = [
        "ParaPing - Help",
        "-" * width,
        "  n: cycle display mode (ip/rdns/alias)",
        "  v: toggle view (timeline/sparkline)",
        "  g: select host for fullscreen RTT graph",
        "  o: cycle sort (failures/streak/latency/host)",
        "  f: cycle filter (failures/latency/all)",
        "  a: toggle ASN display",
        "  m: cycle summary info (rates/rtt/ttl/streak)",
        "  c: toggle color output",
        "  b: toggle bell on ping failure",
        "  F: toggle summary fullscreen view",
        "  w/W: toggle/cycle summary panel (on/off, position)",
        "  p: pause/resume display",
        "  s: save snapshot to file",
        "  <- / -> : navigate backward/forward in time (1 page)",
        "  up / down: scroll host list",
        "  ESC: exit fullscreen graph/selection",
        "  H: show help (Press any key to close)",
        "  q: quit",
    ]
    if can_box:
        return box_lines(lines, width, height)
    return pad_lines(lines, width, height)


def build_ascii_graph(values, width, height, style="line"):
    if width <= 0 or height <= 0:
        return []

    trimmed_values = list(values[-width:]) if values else []
    if len(trimmed_values) < width:
        trimmed_values = [None] * (width - len(trimmed_values)) + trimmed_values

    numeric_values = [value for value in trimmed_values if value is not None]
    if not numeric_values:
        return [" " * width for _ in range(height)]

    min_val = min(numeric_values)
    max_val = max(numeric_values)
    span = max_val - min_val
    if span == 0:
        span = 1.0

    grid = [[" " for _ in range(width)] for _ in range(height)]
    for x, value in enumerate(trimmed_values):
        if value is None:
            grid[height - 1][x] = "x"
            continue
        scaled = int(round((value - min_val) / span * (height - 1)))
        y = height - 1 - scaled
        if style == "bar":
            for y_fill in range(y, height):
                grid[y_fill][x] = "#"
        else:
            grid[y][x] = "*"

    return ["".join(row) for row in grid]


def resample_values(values, target_width):
    if target_width <= 0:
        return []
    if not values:
        return [None] * target_width
    if target_width == 1:
        return [values[-1]]
    if len(values) == 1:
        return [values[0]] * target_width
    if len(values) == target_width:
        return list(values)

    last_index = len(values) - 1
    return [
        values[round(i * last_index / (target_width - 1))]
        for i in range(target_width)
    ]


def render_host_selection_view(
    display_entries,
    selected_index,
    width,
    height,
    mode_label,
):
    if width <= 0 or height <= 0:
        return []

    title = f"Select Host for RTT Graph [{mode_label}]"
    lines = [title[:width], "-" * width]
    status_line = "↑/↓ move | Enter: view graph | ESC: cancel"
    list_height = max(0, height - 3)

    if not display_entries:
        lines.append("No hosts match current filter."[:width])
        lines = pad_lines(lines, width, height)
        lines[-1] = status_line[:width].ljust(width)
        return lines

    max_index = len(display_entries) - 1
    selected_index = min(max(selected_index, 0), max_index)

    start_index = max(
        0,
        min(selected_index - list_height + 1, max_index - list_height + 1),
    )
    end_index = min(len(display_entries), start_index + list_height)

    for idx in range(start_index, end_index):
        _host_id, label = display_entries[idx]
        prefix = "> " if idx == selected_index else "  "
        entry_label = f"{prefix}{label}"
        lines.append(entry_label[:width].ljust(width))

    if len(display_entries) > end_index:
        remaining = len(display_entries) - end_index
        lines.append(f"... ({remaining} more)".ljust(width)[:width])

    lines = pad_lines(lines, width, height)
    lines[-1] = status_line[:width].ljust(width)
    return lines


def render_fullscreen_rtt_graph(
    host_label,
    rtt_values,
    time_history,
    width,
    height,
    display_mode,
    paused,
    timestamp,
):
    if width <= 0 or height <= 0:
        return []

    graph_style = "bar" if display_mode == "sparkline" else "line"
    pause_label = "PAUSED" if paused else "LIVE"
    graph_label = "Bar" if graph_style == "bar" else "Line"
    header = (
        f"ParaPing - {pause_label} RTT Graph "
        f"[{host_label} | {graph_label}] {timestamp}"
    )

    rtt_ms = [value * 1000 if value is not None else None for value in rtt_values]
    numeric_values = [value for value in rtt_ms if value is not None]
    if numeric_values:
        min_val = min(numeric_values)
        max_val = max(numeric_values)
        latest_val = numeric_values[-1]
        range_line = (
            "RTT range (Y-axis, ms): "
            f"{min_val:.1f}-{max_val:.1f} | latest: {latest_val:.1f}"
        )
    else:
        min_val = max_val = 0.0
        range_line = "RTT range (Y-axis, ms): n/a"

    status_line = "ESC: back | v: toggle graph | g: select host"

    y_tick_labels = [
        f"{max_val:.1f}",
        f"{(min_val + max_val) / 2:.1f}",
        f"{min_val:.1f}",
    ]
    y_axis_width = max(len(label) for label in y_tick_labels) if numeric_values else 1
    graph_width = max(1, width - y_axis_width - 3)

    graph_height = max(0, height - 5)
    resampled_values = resample_values(rtt_ms, graph_width)
    resampled_times = resample_values(time_history, graph_width)
    graph_lines = build_ascii_graph(
        resampled_values, graph_width, graph_height, style=graph_style
    )
    if not numeric_values and graph_height > 0:
        message = "No RTT samples yet"
        message_line = message[:graph_width].center(graph_width)
        mid = graph_height // 2
        graph_lines[mid] = message_line

    y_tick_positions = {
        0: y_tick_labels[0],
        max(0, graph_height // 2): y_tick_labels[1],
        max(0, graph_height - 1): y_tick_labels[2],
    }

    lines = [header[:width], range_line[:width], "-" * width]
    for idx, line in enumerate(graph_lines):
        label = y_tick_positions.get(idx, "")
        label_text = label.rjust(y_axis_width)
        lines.append(f"{label_text} | {line}".ljust(width)[:width])

    time_values = [value for value in resampled_times if value is not None]
    if time_values:
        oldest_time = next(value for value in resampled_times if value is not None)
        latest_time = next(
            value for value in reversed(resampled_times) if value is not None
        )
        oldest_age = max(0, int(round(latest_time - oldest_time)))
        x_axis_line = (
            "X-axis (seconds ago, oldest→newest): "
            f"{oldest_age}s → 0s"
        )
    else:
        x_axis_line = "X-axis (seconds ago): n/a"
    lines.append(x_axis_line[:width].ljust(width))
    lines = pad_lines(lines, width, height)
    lines[-1] = status_line[:width].ljust(width)
    return lines


def compute_history_page_step(
    host_infos,
    buffers,
    stats,
    symbols,
    panel_position,
    mode_label,
    sort_mode,
    filter_mode,
    slow_threshold,
    show_asn,
    asn_width=8,
    header_lines=2,
):
    term_size = get_terminal_size(fallback=(80, 24))
    term_width = term_size.columns
    term_height = term_size.lines
    status_box_height = 3 if term_height >= 4 and term_width >= 2 else 1
    panel_height = max(1, term_height - status_box_height)

    include_asn = should_show_asn(
        host_infos, mode_label, show_asn, term_width, asn_width=asn_width
    )
    display_names = build_display_names(host_infos, mode_label, include_asn, asn_width)
    main_width, main_height, _, _, _ = compute_panel_sizes(
        term_width, panel_height, panel_position
    )
    display_entries = build_display_entries(
        host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        sort_mode,
        filter_mode,
        slow_threshold,
    )
    host_labels = [entry[1] for entry in display_entries]
    if not host_labels:
        host_labels = [info["alias"] for info in host_infos]
    _, _, timeline_width, _ = compute_main_layout(
        host_labels, main_width, main_height, header_lines
    )
    return max(1, timeline_width)


def get_cached_page_step(
    cached_page_step,
    last_term_size,
    host_infos,
    buffers,
    stats,
    symbols,
    panel_position,
    mode_label,
    sort_mode,
    filter_mode,
    slow_threshold,
    show_asn,
):
    """
    Get the page step for history navigation, using cached value if available.

    The page step is only recalculated if the terminal size has changed.
    This prevents expensive recalculation on every arrow key press.

    Returns:
        tuple: (page_step, new_cached_page_step, new_last_term_size)
    """
    def should_recalculate_page_step(cached_value, last_size, current_size):
        """Check if page step needs recalculation due to cache miss or terminal resize"""
        if cached_value is None or last_size is None:
            return True  # First time - need to calculate
        if current_size.columns != last_size.columns:
            return True  # Terminal width changed
        if current_size.lines != last_size.lines:
            return True  # Terminal height changed
        return False

    current_term_size = get_terminal_size(fallback=(80, 24))

    # Check if we need to recalculate
    if should_recalculate_page_step(cached_page_step, last_term_size, current_term_size):
        # Terminal size changed or first time - recalculate
        page_step = compute_history_page_step(
            host_infos,
            buffers,
            stats,
            symbols,
            panel_position,
            mode_label,
            sort_mode,
            filter_mode,
            slow_threshold,
            show_asn,
        )
        return page_step, page_step, current_term_size

    # Use cached value
    return cached_page_step, cached_page_step, last_term_size


def compute_host_scroll_bounds(
    host_infos,
    buffers,
    stats,
    symbols,
    panel_position,
    mode_label,
    sort_mode,
    filter_mode,
    slow_threshold,
    show_asn,
    asn_width=8,
    header_lines=2,
):
    term_size = get_terminal_size(fallback=(80, 24))
    term_width = term_size.columns
    term_height = term_size.lines

    include_asn = should_show_asn(
        host_infos, mode_label, show_asn, term_width, asn_width=asn_width
    )
    display_names = build_display_names(host_infos, mode_label, include_asn, asn_width)
    main_width, main_height, _, _, _ = compute_panel_sizes(
        term_width, term_height, panel_position
    )
    display_entries = build_display_entries(
        host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        sort_mode,
        filter_mode,
        slow_threshold,
    )
    host_labels = [entry[1] for entry in display_entries]
    if not host_labels:
        host_labels = [info["alias"] for info in host_infos]
    _, _, _, visible_hosts = compute_main_layout(
        host_labels, main_width, main_height, header_lines
    )
    total_hosts = len(display_entries)
    max_offset = max(0, total_hosts - visible_hosts)
    return max_offset, visible_hosts, total_hosts


def build_display_lines(
    host_infos,
    buffers,
    stats,
    symbols,
    panel_position,
    mode_label,
    display_mode,
    summary_mode,
    sort_mode,
    filter_mode,
    slow_threshold,
    show_help,
    show_asn,
    paused,
    status_message,
    timestamp,
    now_utc,
    use_color=False,
    host_scroll_offset=0,
    summary_fullscreen=False,
    asn_width=8,
    header_lines=2,
):
    term_size = get_terminal_size(fallback=(80, 24))
    term_width = term_size.columns
    term_height = term_size.lines
    min_main_height = 5
    gap_size = 1
    use_panel_boxes = True
    status_box_height = 3 if term_height >= 4 and term_width >= 2 else 1
    panel_height = max(1, term_height - status_box_height)

    include_asn = should_show_asn(
        host_infos, mode_label, show_asn, term_width, asn_width=asn_width
    )
    display_names = build_display_names(host_infos, mode_label, include_asn, asn_width)

    display_entries = build_display_entries(
        host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        sort_mode,
        filter_mode,
        slow_threshold,
    )
    main_width, main_height, summary_width, summary_height, resolved_position = (
        compute_panel_sizes(
            term_width,
            panel_height,
            panel_position,
            min_main_height=min_main_height,
        )
    )
    if resolved_position in ("top", "bottom") and summary_height > 0:
        required_main_height = header_lines + len(display_entries)
        if use_panel_boxes:
            required_main_height += 2
        adjusted_main_height = max(
            min_main_height, min(main_height, required_main_height)
        )
        if adjusted_main_height < main_height:
            main_height = adjusted_main_height
            summary_height = panel_height - main_height - gap_size
    summary_data = compute_summary_data(
        host_infos,
        display_names,
        buffers,
        stats,
        symbols,
        ordered_host_ids=[host_id for host_id, _label in display_entries],
    )
    summary_all = False
    main_lines = []
    summary_lines = []
    if summary_fullscreen:
        summary_all = can_render_full_summary(summary_data, term_width)
        summary_lines = render_summary_view(
            summary_data,
            term_width,
            panel_height,
            summary_mode,
            prefer_all=summary_all,
            boxed=use_panel_boxes,
        )
    else:
        main_lines = render_main_view(
            display_entries,
            buffers,
            symbols,
            main_width,
            main_height,
            mode_label,
            display_mode,
            paused,
            timestamp,
            now_utc,
            use_color,
            host_scroll_offset,
            header_lines,
            boxed=use_panel_boxes,
        )
        summary_all = resolved_position in (
            "top",
            "bottom",
        ) and can_render_full_summary(summary_data, summary_width)
        summary_lines = render_summary_view(
            summary_data,
            summary_width,
            summary_height,
            summary_mode,
            prefer_all=summary_all,
            boxed=use_panel_boxes,
        )

    gap = " "
    combined_lines = []
    if show_help:
        combined_lines = render_help_view(
            term_width, panel_height, boxed=use_panel_boxes
        )
    elif summary_fullscreen:
        combined_lines = summary_lines
    elif resolved_position in ("left", "right"):
        for main_line, summary_line in zip(main_lines, summary_lines):
            if resolved_position == "left":
                combined_lines.append(f"{summary_line}{gap}{main_line}")
            else:
                combined_lines.append(f"{main_line}{gap}{summary_line}")
    elif resolved_position == "top":
        combined_lines = summary_lines + [""] + main_lines
    elif resolved_position == "bottom":
        combined_lines = main_lines + [""] + summary_lines
    else:
        combined_lines = main_lines

    status_line = build_status_line(
        sort_mode,
        filter_mode,
        summary_mode,
        paused,
        status_message,
        summary_all=summary_all,
        summary_fullscreen=summary_fullscreen,
    )
    if panel_height > 0:
        combined_lines = pad_lines(combined_lines, term_width, panel_height)

    if status_box_height == 1:
        status_lines = [status_line[:term_width].ljust(term_width)]
    else:
        status_lines = render_status_box(status_line, term_width)

    if panel_height <= 0:
        return status_lines
    return combined_lines + status_lines


def render_display(
    host_infos,
    buffers,
    stats,
    symbols,
    panel_position,
    mode_label,
    display_mode,
    summary_mode,
    sort_mode,
    filter_mode,
    slow_threshold,
    show_help,
    show_asn,
    paused,
    status_message,
    display_tz,
    use_color=False,
    host_scroll_offset=0,
    summary_fullscreen=False,
    asn_width=8,
    header_lines=2,
    override_lines=None,
):
    global LAST_RENDER_LINES
    now_utc = datetime.now(timezone.utc)
    timestamp = format_timestamp(now_utc, display_tz)
    combined_lines = override_lines
    if combined_lines is None:
        combined_lines = build_display_lines(
            host_infos,
            buffers,
            stats,
            symbols,
            panel_position,
            mode_label,
            display_mode,
            summary_mode,
            sort_mode,
            filter_mode,
            slow_threshold,
            show_help,
            show_asn,
            paused,
            status_message,
            timestamp,
            now_utc,
            use_color,
            host_scroll_offset,
            summary_fullscreen,
            asn_width,
            header_lines,
        )
    if not combined_lines:
        return

    if LAST_RENDER_LINES is None:
        sys.stdout.write("\x1b[2J\x1b[H")
        output_chunks = []
        for index, line in enumerate(combined_lines):
            output_chunks.append(f"\x1b[{index + 1};1H\x1b[2K{line}")
        sys.stdout.write("".join(output_chunks))
        sys.stdout.flush()
        LAST_RENDER_LINES = combined_lines
        return

    max_lines = max(len(LAST_RENDER_LINES), len(combined_lines))
    output_chunks = []
    for index in range(max_lines):
        previous_line = LAST_RENDER_LINES[index] if index < len(LAST_RENDER_LINES) else None
        current_line = combined_lines[index] if index < len(combined_lines) else ""
        if previous_line == current_line and index < len(combined_lines):
            continue
        output_chunks.append(f"\x1b[{index + 1};1H\x1b[2K{current_line}")

    if output_chunks:
        sys.stdout.write("".join(output_chunks))
        sys.stdout.flush()

    LAST_RENDER_LINES = combined_lines


def format_timezone_label(now_utc, display_tz):
    tzinfo = now_utc.astimezone(display_tz).tzinfo
    tz_name = tzinfo.tzname(now_utc) if tzinfo else None
    if tz_name:
        return tz_name
    if hasattr(display_tz, "key"):
        return display_tz.key
    return "UTC"


def format_timestamp(now_utc, display_tz):
    timestamp = now_utc.astimezone(display_tz).strftime("%Y-%m-%d %H:%M:%S")
    tz_label = format_timezone_label(now_utc, display_tz)
    return f"{timestamp} ({tz_label})"


def worker_ping(
    host_info,
    timeout,
    count,
    slow_threshold,
    verbose,
    pause_event,
    stop_event,
    result_queue,
    interval,
    helper_path,
):
    for result in ping_host(
        host_info["host"],
        timeout,
        count,
        slow_threshold,
        verbose,
        pause_event,
        stop_event,
        interval,
        helper_path,
    ):
        result_queue.put({**result, "host_id": host_info["id"]})
    result_queue.put({"host_id": host_info["id"], "status": "done"})


def resolve_display_name(host_info, mode):
    if mode == "ip":
        return host_info["ip"]
    if mode == "rdns":
        if host_info.get("rdns_pending"):
            return "resolving..."
        return host_info["rdns"] or host_info["ip"]
    if mode == "alias":
        return host_info.get("alias") or host_info.get("host") or host_info["ip"]
    return host_info["ip"]


def format_display_name(host_info, mode, include_asn, asn_width, base_label_width=0):
    base_label = resolve_display_name(host_info, mode)
    if not include_asn:
        return base_label
    padded_label = (
        f"{base_label:<{base_label_width}}" if base_label_width else base_label
    )
    asn_label = format_asn_label(host_info, asn_width)
    return f"{padded_label} {asn_label}"


def format_asn_label(host_info, asn_width):
    if host_info.get("asn_pending"):
        label = "resolving..."
    else:
        label = host_info.get("asn") or ""
    return f"{label[:asn_width]:<{asn_width}}"


def build_display_names(host_infos, mode, include_asn, asn_width):
    base_label_width = 0
    if include_asn:
        base_label_width = max(
            (len(resolve_display_name(info, mode)) for info in host_infos), default=0
        )
    return {
        info["id"]: format_display_name(
            info, mode, include_asn, asn_width, base_label_width
        )
        for info in host_infos
    }


def build_host_infos(hosts):
    host_infos = []
    host_map = {}
    for index, entry in enumerate(hosts):
        if isinstance(entry, str):
            host = entry
            alias = entry
            ip_address = None
        else:
            host = entry.get("host") or entry.get("ip")
            alias = entry.get("alias") or host
            ip_address = entry.get("ip")
        if not ip_address:
            try:
                ip_address = socket.gethostbyname(host)
            except (socket.gaierror, OSError):
                ip_address = host
        info = {
            "id": index,
            "host": host,
            "alias": alias,
            "ip": ip_address,
            "rdns": None,
            "rdns_pending": False,
            "asn": None,
            "asn_pending": False,
        }
        host_infos.append(info)
        host_map.setdefault(host, []).append(info)
    return host_infos, host_map


def resolve_rdns(ip_address):
    try:
        return socket.gethostbyaddr(ip_address)[0]
    except (socket.herror, socket.gaierror, OSError):
        return None


def resolve_asn(ip_address, timeout=3.0, max_bytes=65536):
    query = f" -v {ip_address}\n".encode("utf-8")
    try:
        with socket.create_connection(("whois.cymru.com", 43), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(query)
            chunks = []
            total_read = 0
            while True:
                remaining = max_bytes - total_read
                if remaining <= 0:
                    break
                chunk = sock.recv(min(4096, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                total_read += len(chunk)
    except (socket.timeout, OSError):
        return None

    response = b"".join(chunks).decode("utf-8", errors="ignore")
    lines = [line for line in response.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    parts = [part.strip() for part in lines[1].split("|")]
    if not parts:
        return None
    asn = parts[0].replace("AS", "").strip()
    if not asn or asn.upper() == "NA":
        return None
    return f"AS{asn}"


def rdns_worker(request_queue, result_queue, stop_event):
    while not stop_event.is_set():
        try:
            item = request_queue.get(timeout=0.1)
        except queue.Empty:
            continue
        if item is None:
            request_queue.task_done()
            break
        host, ip_address = item
        result_queue.put((host, resolve_rdns(ip_address)))
        request_queue.task_done()


def asn_worker(request_queue, result_queue, stop_event, timeout):
    while not stop_event.is_set():
        try:
            item = request_queue.get(timeout=0.1)
        except queue.Empty:
            continue
        if item is None:
            request_queue.task_done()
            break
        host, ip_address = item
        result_queue.put((host, resolve_asn(ip_address, timeout=timeout)))
        request_queue.task_done()


def should_retry_asn(ip_address, asn_cache, now, failure_ttl):
    cached = asn_cache.get(ip_address)
    if cached is None:
        return True
    if cached["value"] is None and (now - cached["fetched_at"]) >= failure_ttl:
        return True
    return False


def should_show_asn(
    host_infos, mode, show_asn, term_width, min_timeline_width=10, asn_width=8
):
    if not show_asn:
        return False
    base_label_width = max(
        (len(resolve_display_name(info, mode)) for info in host_infos), default=0
    )
    labels = [
        format_display_name(info, mode, True, asn_width, base_label_width)
        for info in host_infos
    ]
    if not labels:
        return False
    label_width = max(len(label) for label in labels)
    timeline_width = term_width - label_width - 3
    return timeline_width >= min_timeline_width


def parse_escape_sequence(seq):
    arrow_map = {
        "A": "arrow_up",
        "B": "arrow_down",
        "C": "arrow_right",
        "D": "arrow_left",
    }
    if not seq:
        return None
    if seq in ("[A", "OA"):
        return "arrow_up"
    if seq in ("[B", "OB"):
        return "arrow_down"
    if seq in ("[C", "OC"):
        return "arrow_right"
    if seq in ("[D", "OD"):
        return "arrow_left"
    if seq[0] in ("[", "O") and seq[-1] in arrow_map:
        return arrow_map[seq[-1]]
    return None


def read_key():
    """
    Read a key from stdin, handling multi-byte sequences like arrow keys.
    Returns special strings for arrow keys: 'arrow_left', 'arrow_right', 'arrow_up', 'arrow_down'
    """
    if not sys.stdin.isatty():
        return None
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return None
    char = sys.stdin.read(1)
    # Check for escape sequence (arrow keys start with ESC)
    if char == "\x1b":
        seq = ""
        deadline = time.monotonic() + ARROW_KEY_READ_TIMEOUT
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            ready, _, _ = select.select([sys.stdin], [], [], remaining)
            if not ready:
                break
            seq += sys.stdin.read(1)
            if seq and seq[-1] in ("A", "B", "C", "D"):
                break
        parsed = parse_escape_sequence(seq)
        return parsed if parsed is not None else char
    return char


def flash_screen():
    """Flash the screen with a white background for ~100ms"""
    if not sys.stdout.isatty():
        return
    # ANSI escape sequences for visual flash effect
    SAVE_CURSOR = "\x1b7"           # Save cursor position
    SET_WHITE_BG = "\x1b[47m"       # White background
    SET_BLACK_FG = "\x1b[30m"       # Black foreground
    CLEAR_SCREEN = "\x1b[2J"        # Clear screen
    MOVE_HOME = "\x1b[H"            # Move cursor to home position
    RESTORE_CURSOR = "\x1b8"        # Restore cursor position
    FLASH_DURATION_SECONDS = 0.1    # Duration of flash effect

    # Apply white flash effect and clear screen
    sys.stdout.write(
        SAVE_CURSOR + SET_WHITE_BG + SET_BLACK_FG + CLEAR_SCREEN + MOVE_HOME
    )
    sys.stdout.flush()
    time.sleep(FLASH_DURATION_SECONDS)
    # Restore normal display
    sys.stdout.write(ANSI_RESET + RESTORE_CURSOR)
    sys.stdout.flush()


def should_flash_on_fail(status, flash_on_fail, show_help):
    """Return True when the failure flash should be displayed."""
    return status == "fail" and flash_on_fail and not show_help


def ring_bell():
    """Ring the terminal bell"""
    if not sys.stdout.isatty():
        return
    sys.stdout.write("\a")
    sys.stdout.flush()


def create_state_snapshot(buffers, stats, timestamp):
    """
    Create a deep copy snapshot of current buffers and stats.

    Args:
        buffers: Current buffer state
        stats: Current statistics
        timestamp: Timestamp for this snapshot

    Returns:
        Dict with snapshot data
    """
    # Deep copy buffers (deques and their contents)
    buffers_copy = {}
    for host_id, host_buffers in buffers.items():
        buffers_copy[host_id] = {
            "timeline": deque(
                host_buffers["timeline"],
                maxlen=host_buffers["timeline"].maxlen
            ),
            "rtt_history": deque(
                host_buffers["rtt_history"],
                maxlen=host_buffers["rtt_history"].maxlen
            ),
            "time_history": deque(
                host_buffers["time_history"],
                maxlen=host_buffers["time_history"].maxlen
            ),
            "ttl_history": deque(
                host_buffers["ttl_history"],
                maxlen=host_buffers["ttl_history"].maxlen
            ),
            "categories": {
                status: deque(cat_deque, maxlen=cat_deque.maxlen)
                for status, cat_deque in host_buffers["categories"].items()
            }
        }

    # Deep copy stats
    stats_copy = copy.deepcopy(stats)

    return {
        "timestamp": timestamp,
        "buffers": buffers_copy,
        "stats": stats_copy,
    }


def update_history_buffer(
    history_buffer,
    buffers,
    stats,
    now,
    last_snapshot_time,
    history_offset,
):
    if (now - last_snapshot_time) < SNAPSHOT_INTERVAL_SECONDS:
        return last_snapshot_time, history_offset

    snapshot = create_state_snapshot(buffers, stats, now)
    history_buffer.append(snapshot)
    last_snapshot_time = now
    if history_offset > 0:
        history_offset = min(history_offset + 1, len(history_buffer) - 1)
    return last_snapshot_time, history_offset


def resolve_render_state(history_offset, history_buffer, buffers, stats, paused):
    if history_offset > 0 and history_offset <= len(history_buffer):
        snapshot = history_buffer[-(history_offset + 1)]
        return snapshot["buffers"], snapshot["stats"], True
    return buffers, stats, paused


def prepare_terminal_for_exit():
    if not sys.stdout.isatty():
        return
    term_size = get_terminal_size(fallback=(80, 24))
    sys.stdout.write("\n" * term_size.lines)
    sys.stdout.flush()


def main(args):

    # Validate count parameter - allow 0 for infinite
    if args.count < 0:
        print("Error: Count must be a non-negative number (0 for infinite).")
        return
    if args.timeout <= 0:
        print("Error: Timeout must be a positive number of seconds.")
        return

    # Validate interval parameter
    if args.interval < 0.1 or args.interval > 60.0:
        print("Error: Interval must be between 0.1 and 60.0 seconds.")
        return

    # Collect all hosts to ping
    all_hosts = []

    # Add hosts from command line arguments
    if args.hosts:
        all_hosts.extend({"host": host, "alias": host} for host in args.hosts)

    # Add hosts from input file if provided
    if args.input:
        file_hosts = read_input_file(args.input)
        all_hosts.extend(file_hosts)

    # Check if we have any hosts to ping
    if not all_hosts:
        print(
            "Error: No hosts specified. Provide hosts as arguments or use -f/--input option."
        )
        return
    if len(all_hosts) > MAX_HOST_THREADS:
        print(
            "Error: Host count exceeds maximum supported threads "
            f"({len(all_hosts)} > {MAX_HOST_THREADS}). Reduce the host list."
        )
        return

    display_tz = timezone.utc
    if args.timezone:
        try:
            display_tz = ZoneInfo(args.timezone)
        except ZoneInfoNotFoundError:
            print(
                f"Error: Unknown timezone '{args.timezone}'. Use an IANA name like 'Asia/Tokyo'."
            )
            return
    snapshot_tz = display_tz if args.snapshot_timezone == "display" else timezone.utc

    symbols = {"success": ".", "fail": "x", "slow": "!"}
    term_size = get_terminal_size(fallback=(80, 24))
    host_infos, host_info_map = build_host_infos(all_hosts)
    host_labels = [info["alias"] for info in host_infos]
    _, _, timeline_width, _ = compute_main_layout(
        host_labels, term_size.columns, term_size.lines
    )
    buffers = {
        info["id"]: {
            "timeline": deque(maxlen=timeline_width),
            "rtt_history": deque(maxlen=timeline_width),
            "time_history": deque(maxlen=timeline_width),
            "ttl_history": deque(maxlen=timeline_width),
            "categories": {status: deque(maxlen=timeline_width) for status in symbols},
        }
        for info in host_infos
    }
    stats = {
        info["id"]: {
            "success": 0,
            "fail": 0,
            "slow": 0,
            "total": 0,
            "rtt_sum": 0.0,
            "rtt_sum_sq": 0.0,
            "rtt_count": 0,
        }
        for info in host_infos
    }
    result_queue = queue.Queue()

    count_display = "infinite" if args.count == 0 else str(args.count)
    print(
        f"ParaPing - Pinging {len(all_hosts)} host(s) with timeout={args.timeout}s, "
        f"count={count_display}, interval={args.interval}s, slow-threshold={args.slow_threshold}s"
    )

    modes = ["ip", "rdns", "alias"]
    mode_index = 0
    show_help = False
    display_modes = ["timeline", "sparkline"]
    display_mode_index = 0
    summary_modes = ["rates", "rtt", "ttl", "streak"]
    summary_mode_index = 0
    summary_fullscreen = False
    sort_modes = ["failures", "streak", "latency", "host"]
    sort_mode_index = 0
    filter_modes = ["failures", "latency", "all"]
    filter_mode_index = 2
    running = True
    paused = False
    pause_mode = args.pause_mode
    pause_event = threading.Event()
    stop_event = threading.Event()
    status_message = None
    force_render = False
    show_asn = True
    color_supported = sys.stdout.isatty()
    use_color = args.color and color_supported
    flash_on_fail = getattr(args, "flash_on_fail", False)
    bell_on_fail = getattr(args, "bell_on_fail", False)
    asn_cache = {}
    asn_timeout = 3.0
    asn_failure_ttl = 300.0
    panel_position = args.panel_position
    panel_toggle_default = args.panel_position if args.panel_position != "none" else "right"
    last_panel_position = panel_position if panel_position != "none" else None
    host_select_active = False
    host_select_index = 0
    graph_host_id = None

    # History navigation state
    # Store snapshots at regular intervals for time navigation
    max_history_snapshots = int(
        HISTORY_DURATION_MINUTES * 60 / SNAPSHOT_INTERVAL_SECONDS
    )
    history_buffer = deque(maxlen=max_history_snapshots)
    history_offset = 0  # 0 = live, >0 = viewing history
    last_snapshot_time = 0.0
    # Cache page step to avoid expensive recalculation on every arrow key press
    cached_page_step = None
    last_term_size = None
    host_scroll_offset = 0

    rdns_request_queue = queue.Queue()
    rdns_result_queue = queue.Queue()
    asn_request_queue = queue.Queue()
    asn_result_queue = queue.Queue()
    worker_stop = threading.Event()
    rdns_thread = threading.Thread(
        target=rdns_worker,
        args=(rdns_request_queue, rdns_result_queue, worker_stop),
        daemon=True,
    )
    asn_thread = threading.Thread(
        target=asn_worker,
        args=(asn_request_queue, asn_result_queue, worker_stop, asn_timeout),
        daemon=True,
    )
    rdns_thread.start()
    asn_thread.start()

    stdin_fd = None
    original_term = None
    if sys.stdin.isatty():
        stdin_fd = sys.stdin.fileno()
        original_term = termios.tcgetattr(stdin_fd)

    with ThreadPoolExecutor(max_workers=len(all_hosts)) as executor:
        for host, infos in host_info_map.items():
            info = infos[0]
            for entry in infos:
                entry["rdns_pending"] = True
            rdns_request_queue.put((host, info["ip"]))
            now = time.time()
            if info["ip"] in asn_cache and asn_cache[info["ip"]]["value"] is not None:
                cached_asn = asn_cache[info["ip"]]["value"]
                for entry in infos:
                    entry["asn"] = cached_asn
                    entry["asn_pending"] = False
            elif should_retry_asn(info["ip"], asn_cache, now, asn_failure_ttl):
                for entry in infos:
                    entry["asn_pending"] = True
                asn_request_queue.put((host, info["ip"]))
        for info in host_infos:
            executor.submit(
                worker_ping,
                info,
                args.timeout,
                args.count,
                args.slow_threshold,
                args.verbose,
                pause_event,
                stop_event,
                result_queue,
                args.interval,
                args.ping_helper,
            )

        completed_hosts = 0
        updated = True
        last_render = 0.0
        refresh_interval = 0.15
        # When count is 0 (infinite), workers never complete, so we wait for user to quit
        expect_completion = args.count > 0
        try:
            if stdin_fd is not None:
                tty.setcbreak(stdin_fd)
            while running and (not expect_completion or completed_hosts < len(host_infos)):
                key = read_key()
                if key:
                    if key in ("q", "Q"):
                        running = False
                        stop_event.set()
                    elif show_help:
                        show_help = False
                        force_render = True
                        updated = True
                        continue
                    elif host_select_active:
                        render_buffers, render_stats, _ = resolve_render_state(
                            history_offset,
                            history_buffer,
                            buffers,
                            stats,
                            paused,
                        )
                        term_size = get_terminal_size(fallback=(80, 24))
                        include_asn = should_show_asn(
                            host_infos,
                            modes[mode_index],
                            show_asn,
                            term_size.columns,
                        )
                        display_names = build_display_names(
                            host_infos, modes[mode_index], include_asn, asn_width=8
                        )
                        display_entries = build_display_entries(
                            host_infos,
                            display_names,
                            render_buffers,
                            render_stats,
                            symbols,
                            sort_modes[sort_mode_index],
                            filter_modes[filter_mode_index],
                            args.slow_threshold,
                        )
                        if not display_entries:
                            host_select_index = 0
                        else:
                            host_select_index = min(
                                max(host_select_index, 0), len(display_entries) - 1
                            )
                        if key == "arrow_up" and display_entries:
                            host_select_index = max(0, host_select_index - 1)
                            force_render = True
                            updated = True
                        elif key == "arrow_down" and display_entries:
                            host_select_index = min(
                                len(display_entries) - 1, host_select_index + 1
                            )
                            force_render = True
                            updated = True
                        elif key in ("\r", "\n"):
                            if display_entries:
                                graph_host_id = display_entries[host_select_index][0]
                                host_select_active = False
                                force_render = True
                                updated = True
                        elif key == "\x1b":
                            host_select_active = False
                            force_render = True
                            updated = True
                        continue
                    elif graph_host_id is not None:
                        if key == "\x1b":
                            graph_host_id = None
                            force_render = True
                            updated = True
                            continue
                        if key in ("g", "G"):
                            host_select_active = True
                            graph_host_id = None
                            force_render = True
                            updated = True
                            continue
                    elif key in ("H", "h"):
                        show_help = True
                        force_render = True
                        updated = True
                    elif key == "n":
                        mode_index = (mode_index + 1) % len(modes)
                        cached_page_step = None  # Invalidate cache - display mode changed
                        updated = True
                    elif key == "v":
                        display_mode_index = (display_mode_index + 1) % len(
                            display_modes
                        )
                        updated = True
                    elif key == "o":
                        sort_mode_index = (sort_mode_index + 1) % len(sort_modes)
                        cached_page_step = None  # Invalidate cache - sort mode changed
                        updated = True
                    elif key == "f":
                        filter_mode_index = (filter_mode_index + 1) % len(filter_modes)
                        cached_page_step = None  # Invalidate cache - filter mode changed
                        updated = True
                    elif key == "a":
                        show_asn = not show_asn
                        cached_page_step = None  # Invalidate cache - ASN display toggled
                        updated = True
                    elif key == "m":
                        summary_mode_index = (summary_mode_index + 1) % len(
                            summary_modes
                        )
                        status_message = (
                            f"Summary: {summary_modes[summary_mode_index].upper()}"
                        )
                        updated = True
                    elif key == "c":
                        if not color_supported:
                            status_message = "Color output unavailable (no TTY)"
                        else:
                            use_color = not use_color
                            status_message = (
                                "Color output enabled"
                                if use_color
                                else "Color output disabled"
                            )
                        force_render = True
                        updated = True
                    elif key == "b":
                        bell_on_fail = not bell_on_fail
                        status_message = (
                            "Bell on fail enabled"
                            if bell_on_fail
                            else "Bell on fail disabled"
                        )
                        force_render = True
                        updated = True
                    elif key == "F":
                        summary_fullscreen = not summary_fullscreen
                        status_message = (
                            "Summary fullscreen view enabled"
                            if summary_fullscreen
                            else "Summary fullscreen view disabled"
                        )
                        force_render = True
                        updated = True
                    elif key == "w":
                        panel_position, last_panel_position = toggle_panel_visibility(
                            panel_position,
                            last_panel_position,
                            default_position=panel_toggle_default,
                        )
                        status_message = (
                            "Summary panel hidden"
                            if panel_position == "none"
                            else "Summary panel shown"
                        )
                        cached_page_step = None  # Invalidate cache - panel visibility changed
                        force_render = True
                        updated = True
                    elif key == "W":
                        reference_position = (
                            panel_position
                            if panel_position != "none"
                            else last_panel_position or panel_toggle_default
                        )
                        panel_position = cycle_panel_position(
                            reference_position, default_position=panel_toggle_default
                        )
                        last_panel_position = panel_position
                        status_message = (
                            f"Summary panel position: {panel_position.upper()}"
                        )
                        cached_page_step = None  # Invalidate cache - panel position changed
                        force_render = True
                        updated = True
                    elif key == "p":
                        paused = not paused
                        status_message = "Paused" if paused else "Resumed"
                        if pause_mode == "ping":
                            if paused:
                                pause_event.set()
                            else:
                                pause_event.clear()
                        force_render = True
                        updated = True
                    elif key == "s":
                        now_utc = datetime.now(timezone.utc)
                        snapshot_dt = now_utc.astimezone(snapshot_tz)
                        snapshot_name = snapshot_dt.strftime(
                            "paraping_snapshot_%Y%m%d_%H%M%S.txt"
                        )
                        snapshot_lines = build_display_lines(
                            host_infos,
                            buffers,
                            stats,
                            symbols,
                            panel_position,
                            modes[mode_index],
                            display_modes[display_mode_index],
                            summary_modes[summary_mode_index],
                            sort_modes[sort_mode_index],
                            filter_modes[filter_mode_index],
                            args.slow_threshold,
                            show_help,
                            show_asn,
                            paused,
                            status_message,
                            format_timestamp(now_utc, display_tz),
                            now_utc,
                            False,
                            host_scroll_offset,
                            summary_fullscreen,
                        )
                        with open(
                            snapshot_name, "w", encoding="utf-8"
                        ) as snapshot_file:
                            snapshot_file.write("\n".join(snapshot_lines) + "\n")
                        status_message = f"Saved: {snapshot_name}"
                        updated = True
                    elif key == "arrow_left":
                        # Go back in time (increase offset)
                        if history_offset < len(history_buffer) - 1:
                            page_step, cached_page_step, last_term_size = get_cached_page_step(
                                cached_page_step,
                                last_term_size,
                                host_infos,
                                buffers,
                                stats,
                                symbols,
                                panel_position,
                                modes[mode_index],
                                sort_modes[sort_mode_index],
                                filter_modes[filter_mode_index],
                                args.slow_threshold,
                                show_asn,
                            )
                            history_offset = min(
                                history_offset + page_step,
                                len(history_buffer) - 1,
                            )
                            force_render = True
                            updated = True
                            snapshot = history_buffer[-(history_offset + 1)]
                            elapsed_seconds = int(time.time() - snapshot["timestamp"])
                            status_message = f"Viewing {elapsed_seconds}s ago"
                    elif key == "arrow_right":
                        # Go forward in time (decrease offset, toward live)
                        if history_offset > 0:
                            page_step, cached_page_step, last_term_size = get_cached_page_step(
                                cached_page_step,
                                last_term_size,
                                host_infos,
                                buffers,
                                stats,
                                symbols,
                                panel_position,
                                modes[mode_index],
                                sort_modes[sort_mode_index],
                                filter_modes[filter_mode_index],
                                args.slow_threshold,
                                show_asn,
                            )
                            history_offset = max(0, history_offset - page_step)
                            force_render = True
                            updated = True
                            if history_offset == 0:
                                status_message = "Returned to LIVE view"
                            else:
                                snapshot = history_buffer[-(history_offset + 1)]
                                elapsed_seconds = int(time.time() - snapshot["timestamp"])
                                status_message = f"Viewing {elapsed_seconds}s ago"
                    elif key == "arrow_up":
                        scroll_buffers = buffers
                        scroll_stats = stats
                        if history_offset > 0 and history_offset <= len(history_buffer):
                            snapshot = history_buffer[-(history_offset + 1)]
                            scroll_buffers = snapshot["buffers"]
                            scroll_stats = snapshot["stats"]
                        max_offset, visible_hosts, total_hosts = compute_host_scroll_bounds(
                            host_infos,
                            scroll_buffers,
                            scroll_stats,
                            symbols,
                            panel_position,
                            modes[mode_index],
                            sort_modes[sort_mode_index],
                            filter_modes[filter_mode_index],
                            args.slow_threshold,
                            show_asn,
                        )
                        if host_scroll_offset > 0 and total_hosts > 0:
                            host_scroll_offset = max(0, host_scroll_offset - 1)
                            end_index = min(
                                host_scroll_offset + visible_hosts, total_hosts
                            )
                            status_message = (
                                f"Hosts {host_scroll_offset + 1}-{end_index} "
                                f"of {total_hosts}"
                            )
                            force_render = True
                            updated = True
                    elif key == "arrow_down":
                        scroll_buffers = buffers
                        scroll_stats = stats
                        if history_offset > 0 and history_offset <= len(history_buffer):
                            snapshot = history_buffer[-(history_offset + 1)]
                            scroll_buffers = snapshot["buffers"]
                            scroll_stats = snapshot["stats"]
                        max_offset, visible_hosts, total_hosts = compute_host_scroll_bounds(
                            host_infos,
                            scroll_buffers,
                            scroll_stats,
                            symbols,
                            panel_position,
                            modes[mode_index],
                            sort_modes[sort_mode_index],
                            filter_modes[filter_mode_index],
                            args.slow_threshold,
                            show_asn,
                        )
                        if host_scroll_offset < max_offset and total_hosts > 0:
                            host_scroll_offset = min(max_offset, host_scroll_offset + 1)
                            end_index = min(
                                host_scroll_offset + visible_hosts, total_hosts
                            )
                            status_message = (
                                f"Hosts {host_scroll_offset + 1}-{end_index} "
                                f"of {total_hosts}"
                            )
                            force_render = True
                            updated = True
                    elif key in ("g", "G"):
                        host_select_active = True
                        host_select_index = 0
                        force_render = True
                        updated = True

                while True:
                    try:
                        host, rdns_value = rdns_result_queue.get_nowait()
                    except queue.Empty:
                        break
                    for info in host_info_map.get(host, []):
                        info["rdns"] = rdns_value
                        info["rdns_pending"] = False
                    if not paused:
                        updated = True

                while True:
                    try:
                        host, asn_value = asn_result_queue.get_nowait()
                    except queue.Empty:
                        break
                    for info in host_info_map.get(host, []):
                        info["asn"] = asn_value
                        info["asn_pending"] = False
                    if host_info_map.get(host):
                        ip_address = host_info_map[host][0]["ip"]
                    else:
                        ip_address = host
                    asn_cache[ip_address] = {
                        "value": asn_value,
                        "fetched_at": time.time(),
                    }
                    if not paused:
                        updated = True

                now = time.time()
                for host, infos in host_info_map.items():
                    if any(info["asn_pending"] for info in infos):
                        continue
                    if any(info["asn"] is not None for info in infos):
                        continue
                    ip_address = infos[0]["ip"]
                    if should_retry_asn(ip_address, asn_cache, now, asn_failure_ttl):
                        for info in infos:
                            info["asn_pending"] = True
                        asn_request_queue.put((host, ip_address))

                while True:
                    try:
                        result = result_queue.get_nowait()
                    except queue.Empty:
                        break
                    host_id = result["host_id"]
                    if result.get("status") == "done":
                        completed_hosts += 1
                        continue

                    status = result["status"]
                    buffers[host_id]["timeline"].append(symbols[status])
                    buffers[host_id]["rtt_history"].append(result.get("rtt"))
                    buffers[host_id]["time_history"].append(time.time())
                    buffers[host_id]["ttl_history"].append(result.get("ttl"))
                    buffers[host_id]["categories"][status].append(result["sequence"])
                    stats[host_id][status] += 1
                    stats[host_id]["total"] += 1
                    if result.get("rtt") is not None:
                        stats[host_id]["rtt_sum"] += result["rtt"]
                        stats[host_id]["rtt_sum_sq"] += result["rtt"] ** 2
                        stats[host_id]["rtt_count"] += 1

                    # Trigger flash or bell on ping failure
                    if should_flash_on_fail(status, flash_on_fail, show_help):
                        flash_screen()
                    if status == "fail" and bell_on_fail and not show_help:
                        ring_bell()

                    if not paused:
                        updated = True

                now = time.time()

                # Periodically save snapshots for history navigation
                last_snapshot_time, history_offset = update_history_buffer(
                    history_buffer,
                    buffers,
                    stats,
                    now,
                    last_snapshot_time,
                    history_offset,
                )

                # Determine which buffers/stats to use for rendering
                render_buffers, render_stats, render_paused = resolve_render_state(
                    history_offset,
                    history_buffer,
                    buffers,
                    stats,
                    paused,
                )

                if force_render or (
                    not paused and (updated or (now - last_render) >= refresh_interval)
                ):
                    display_timestamp = format_timestamp(
                        datetime.now(timezone.utc), display_tz
                    )
                    if history_offset > 0 and history_offset <= len(history_buffer):
                        snapshot = history_buffer[-(history_offset + 1)]
                        snapshot_dt = datetime.fromtimestamp(
                            snapshot["timestamp"], timezone.utc
                        )
                        display_timestamp = format_timestamp(snapshot_dt, display_tz)
                    max_offset, _visible_hosts, _total_hosts = compute_host_scroll_bounds(
                        host_infos,
                        render_buffers,
                        render_stats,
                        symbols,
                        panel_position,
                        modes[mode_index],
                        sort_modes[sort_mode_index],
                        filter_modes[filter_mode_index],
                        args.slow_threshold,
                        show_asn,
                    )
                    if host_scroll_offset > max_offset:
                        host_scroll_offset = max_offset
                    override_lines = None
                    term_size = get_terminal_size(fallback=(80, 24))
                    if show_help:
                        override_lines = render_help_view(
                            term_size.columns, term_size.lines
                        )
                    elif host_select_active:
                        include_asn = should_show_asn(
                            host_infos,
                            modes[mode_index],
                            show_asn,
                            term_size.columns,
                        )
                        display_names = build_display_names(
                            host_infos, modes[mode_index], include_asn, asn_width=8
                        )
                        display_entries = build_display_entries(
                            host_infos,
                            display_names,
                            render_buffers,
                            render_stats,
                            symbols,
                            sort_modes[sort_mode_index],
                            filter_modes[filter_mode_index],
                            args.slow_threshold,
                        )
                        override_lines = render_host_selection_view(
                            display_entries,
                            host_select_index,
                            term_size.columns,
                            term_size.lines,
                            modes[mode_index],
                        )
                    elif graph_host_id is not None:
                        include_asn = should_show_asn(
                            host_infos,
                            modes[mode_index],
                            show_asn,
                            term_size.columns,
                        )
                        display_names = build_display_names(
                            host_infos, modes[mode_index], include_asn, asn_width=8
                        )
                        host_label = display_names.get(
                            graph_host_id, host_infos[graph_host_id]["alias"]
                        )
                        rtt_values = render_buffers[graph_host_id]["rtt_history"]
                        time_history = render_buffers[graph_host_id]["time_history"]
                        override_lines = render_fullscreen_rtt_graph(
                            host_label,
                            rtt_values,
                            time_history,
                            term_size.columns,
                            term_size.lines,
                            display_modes[display_mode_index],
                            render_paused,
                            display_timestamp,
                        )
                    render_display(
                        host_infos,
                        render_buffers,
                        render_stats,
                        symbols,
                        panel_position,
                        modes[mode_index],
                        display_modes[display_mode_index],
                        summary_modes[summary_mode_index],
                        sort_modes[sort_mode_index],
                        filter_modes[filter_mode_index],
                        args.slow_threshold,
                        show_help,
                        show_asn,
                        render_paused,
                        status_message,
                        display_tz,
                        use_color,
                        host_scroll_offset,
                        summary_fullscreen,
                        override_lines=override_lines,
                    )
                    last_render = now
                    updated = False
                    force_render = False

                time.sleep(0.05)
        except KeyboardInterrupt:
            running = False
            stop_event.set()
        finally:
            stop_event.set()
            worker_stop.set()
            rdns_request_queue.put(None)
            asn_request_queue.put(None)
            rdns_thread.join(timeout=1.0)
            asn_thread.join(timeout=1.0)
            if stdin_fd is not None and original_term is not None:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, original_term)

    prepare_terminal_for_exit()
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for info in host_infos:
        host_id = info["id"]
        success = stats[host_id]["success"]
        slow = stats[host_id]["slow"]
        fail = stats[host_id]["fail"]
        total = stats[host_id]["total"]
        percentage = (success / total * 100) if total > 0 else 0
        status = "OK" if success > 0 else "FAILED"
        print(
            f"{info['alias']:30} {success}/{total} replies, {slow} slow, {fail} failed "
            f"({percentage:.1f}%) [{status}]"
        )


if __name__ == "__main__":
    # Handle command line options
    options = handle_options()
    main(options)
