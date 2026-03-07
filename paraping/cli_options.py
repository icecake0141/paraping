# Copyright 2026 icecake0141
# SPDX-License-Identifier: Apache-2.0

"""Shared CLI option specifications for parser/config synchronization."""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class OptionSpec:
    """Specification for one CLI option."""

    dest: str
    flags: Tuple[str, ...]
    default: Any
    help_text: str
    value_type: Optional[type] = None
    choices: Optional[Tuple[str, ...]] = None
    boolean: bool = False
    config_key: Optional[str] = None


CLI_OPTION_SPECS: Tuple[OptionSpec, ...] = (
    OptionSpec(
        dest="timeout",
        flags=("-t", "--timeout"),
        value_type=int,
        default=1,
        help_text="Timeout in seconds for each ping (default: 1)",
        config_key="timeout",
    ),
    OptionSpec(
        dest="count",
        flags=("-c", "--count"),
        value_type=int,
        default=0,
        help_text="Number of ping attempts per host (default: 0 for infinite)",
    ),
    OptionSpec(
        dest="slow_threshold",
        flags=("-s", "--slow-threshold"),
        value_type=float,
        default=0.5,
        help_text="Threshold in seconds for slow ping (default: 0.5)",
        config_key="slow_threshold",
    ),
    OptionSpec(
        dest="interval",
        flags=("-i", "--interval"),
        value_type=float,
        default=1.0,
        help_text="Interval in seconds between pings per host (default: 1.0, range: 0.1-60.0). "
        "Note: Global rate limit is 50 pings/sec (host_count / interval <= 50)",
        config_key="interval",
    ),
    OptionSpec(
        dest="log_level",
        flags=("--log-level",),
        value_type=str,
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help_text="Logging level for verbose and error output (default: INFO)",
        config_key="log_level",
    ),
    OptionSpec(
        dest="log_file",
        flags=("--log-file",),
        value_type=str,
        default=None,
        help_text="Optional log file path for persistent logging",
        config_key="log_file",
    ),
    OptionSpec(
        dest="input",
        flags=("-f", "--input"),
        value_type=str,
        default=None,
        help_text="Input file containing list of hosts (one per line, format: IP,alias)",
    ),
    OptionSpec(
        dest="group_by",
        flags=("--group-by",),
        value_type=str,
        default="none",
        help_text="Group key for summary and host grouping (none|asn|site|tag|tagN|site>tag1|tag1>site)",
        config_key="group_by",
    ),
    OptionSpec(
        dest="panel_position",
        flags=("-P", "--panel-position"),
        value_type=str,
        choices=("right", "left", "top", "bottom", "none"),
        default="right",
        help_text="Summary panel position (right|left|top|bottom|none)",
        config_key="panel_position",
    ),
    OptionSpec(
        dest="pause_mode",
        flags=("-m", "--pause-mode"),
        value_type=str,
        choices=("display", "ping"),
        default="display",
        help_text="Pause behavior: display (stop updates only) or ping (pause ping + updates)",
        config_key="pause_mode",
    ),
    OptionSpec(
        dest="timezone",
        flags=("-z", "--timezone"),
        value_type=str,
        default=None,
        help_text="Display timezone (IANA name, e.g. Asia/Tokyo). Defaults to UTC.",
        config_key="timezone",
    ),
    OptionSpec(
        dest="snapshot_timezone",
        flags=("-Z", "--snapshot-timezone"),
        value_type=str,
        choices=("utc", "display"),
        default="utc",
        help_text="Timezone used in snapshot filename (utc|display). Defaults to utc.",
        config_key="snapshot_timezone",
    ),
    OptionSpec(
        dest="flash_on_fail",
        flags=("-F", "--flash-on-fail"),
        boolean=True,
        default=False,
        help_text="Flash screen (white background) when ping fails",
        config_key="flash_on_fail",
    ),
    OptionSpec(
        dest="bell_on_fail",
        flags=("-B", "--bell-on-fail"),
        boolean=True,
        default=False,
        help_text="Ring terminal bell when ping fails",
        config_key="bell_on_fail",
    ),
    OptionSpec(
        dest="color",
        flags=("-C", "--color"),
        boolean=True,
        default=False,
        help_text="Enable colored output (blue=success, yellow=slow, red=fail)",
        config_key="color",
    ),
    OptionSpec(
        dest="ping_helper",
        flags=("-H", "--ping-helper"),
        value_type=str,
        default="./bin/ping_helper",
        help_text="Path to ping_helper binary (default: ./bin/ping_helper)",
        config_key="ping_helper",
    ),
    OptionSpec(
        dest="ui_log_errors",
        flags=("--ui-log-errors",),
        boolean=True,
        default=False,
        help_text="Show warning/error log lines in live TUI output (default: off)",
        config_key="ui_log_errors",
    ),
    OptionSpec(
        dest="show_asn",
        flags=("--show-asn",),
        boolean=True,
        default=True,
        help_text="Initial ASN display state in live views",
        config_key="show_asn",
    ),
    OptionSpec(
        dest="summary_scope",
        flags=("--summary-scope",),
        value_type=str,
        choices=("host", "group"),
        default="host",
        help_text="Initial summary scope (host|group)",
        config_key="summary_scope",
    ),
    OptionSpec(
        dest="summary_mode",
        flags=("--summary-mode",),
        value_type=str,
        choices=("rates", "rtt", "ttl", "streak"),
        default="rates",
        help_text="Initial summary metric mode (rates|rtt|ttl|streak)",
        config_key="summary_mode",
    ),
    OptionSpec(
        dest="view",
        flags=("--view",),
        value_type=str,
        choices=("timeline", "sparkline", "square"),
        default="timeline",
        help_text="Initial main view mode (timeline|sparkline|square)",
        config_key="view",
    ),
    OptionSpec(
        dest="display_name",
        flags=("--display-name",),
        value_type=str,
        choices=("ip", "rdns", "alias"),
        default="alias",
        help_text="Initial host label mode (ip|rdns|alias)",
        config_key="display_name",
    ),
    OptionSpec(
        dest="sort",
        flags=("--sort",),
        value_type=str,
        choices=("config", "failures", "streak", "latency", "host"),
        default="config",
        help_text="Initial host sort mode (config|failures|streak|latency|host)",
        config_key="sort",
    ),
    OptionSpec(
        dest="filter",
        flags=("--filter",),
        value_type=str,
        choices=("failures", "latency", "all"),
        default="all",
        help_text="Initial host filter mode (failures|latency|all)",
        config_key="filter",
    ),
    OptionSpec(
        dest="kitt",
        flags=("--kitt",),
        boolean=True,
        default=False,
        help_text="Initial Knight Rider mode state",
        config_key="kitt",
    ),
    OptionSpec(
        dest="kitt_style",
        flags=("--kitt-style",),
        value_type=str,
        choices=("scanner", "gradient"),
        default="scanner",
        help_text="Initial Knight Rider style (scanner|gradient)",
        config_key="kitt_style",
    ),
    OptionSpec(
        dest="summary_fullscreen",
        flags=("--summary-fullscreen",),
        boolean=True,
        default=False,
        help_text="Initial summary fullscreen view state",
        config_key="summary_fullscreen",
    ),
)


def build_config_field_types() -> Dict[str, type]:
    """Build config field type mapping from CLI option specs."""
    field_types: Dict[str, type] = {}
    for spec in CLI_OPTION_SPECS:
        if spec.config_key is None:
            continue
        if spec.boolean:
            field_types[spec.config_key] = bool
        elif spec.value_type is not None:
            field_types[spec.config_key] = spec.value_type
    return field_types
