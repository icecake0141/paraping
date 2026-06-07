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
"""Generate deterministic terminal-style screenshots for the UX tour."""

from __future__ import annotations

import os
import re
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from paraping.ui_render import build_display_lines, strip_ansi  # noqa: E402

ASSET_DIR = REPO_ROOT / "docs" / "tour" / "assets"
SYMBOLS = {"success": ".", "fail": "x", "slow": "!", "pending": "-"}


def make_hosts() -> List[Dict[str, Any]]:
    return [
        {
            "id": 0,
            "ip": "8.8.8.8",
            "host": "8.8.8.8",
            "alias": "google-dns",
            "site": "edge-tokyo",
            "tags": ["dns", "public"],
            "rdns": "dns.google",
            "rdns_pending": False,
            "asn": "AS15169",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 1,
            "ip": "1.1.1.1",
            "host": "1.1.1.1",
            "alias": "cloudflare-dns",
            "site": "edge-tokyo",
            "tags": ["dns", "public"],
            "rdns": "one.one.one.one",
            "rdns_pending": False,
            "asn": "AS13335",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 2,
            "ip": "9.9.9.9",
            "host": "9.9.9.9",
            "alias": "quad9-dns",
            "site": "edge-osaka",
            "tags": ["dns", "security"],
            "rdns": "dns.quad9.net",
            "rdns_pending": False,
            "asn": "AS19281",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 3,
            "ip": "203.0.113.10",
            "host": "203.0.113.10",
            "alias": "tokyo-fw-a",
            "site": "tokyo-hq",
            "tags": ["wan", "firewall"],
            "rdns": "tokyo-fw-a.example",
            "rdns_pending": False,
            "asn": "AS64500",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 4,
            "ip": "203.0.113.11",
            "host": "203.0.113.11",
            "alias": "tokyo-fw-b",
            "site": "tokyo-hq",
            "tags": ["wan", "firewall"],
            "rdns": "tokyo-fw-b.example",
            "rdns_pending": False,
            "asn": "AS64500",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 5,
            "ip": "198.51.100.20",
            "host": "198.51.100.20",
            "alias": "osaka-edge-a",
            "site": "osaka-branch",
            "tags": ["wan", "branch"],
            "rdns": "osaka-edge-a.example",
            "rdns_pending": False,
            "asn": "AS64501",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 6,
            "ip": "198.51.100.21",
            "host": "198.51.100.21",
            "alias": "osaka-edge-b",
            "site": "osaka-branch",
            "tags": ["wan", "branch"],
            "rdns": "osaka-edge-b.example",
            "rdns_pending": False,
            "asn": "AS64501",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 7,
            "ip": "203.0.113.40",
            "host": "203.0.113.40",
            "alias": "sapporo-vpn-a",
            "site": "sapporo-branch",
            "tags": ["vpn", "branch"],
            "rdns": "sapporo-vpn-a.example",
            "rdns_pending": False,
            "asn": "AS64502",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 8,
            "ip": "203.0.113.41",
            "host": "203.0.113.41",
            "alias": "sapporo-vpn-b",
            "site": "sapporo-branch",
            "tags": ["vpn", "branch"],
            "rdns": "sapporo-vpn-b.example",
            "rdns_pending": False,
            "asn": "AS64502",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 9,
            "ip": "192.0.2.30",
            "host": "192.0.2.30",
            "alias": "aws-nat-apne1",
            "site": "cloud-apne1",
            "tags": ["cloud", "nat"],
            "rdns": "nat-apne1.example",
            "rdns_pending": False,
            "asn": "AS16509",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 10,
            "ip": "192.0.2.31",
            "host": "192.0.2.31",
            "alias": "aws-alb-apne1",
            "site": "cloud-apne1",
            "tags": ["cloud", "web"],
            "rdns": "alb-apne1.example",
            "rdns_pending": False,
            "asn": "AS16509",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 11,
            "ip": "198.51.100.60",
            "host": "198.51.100.60",
            "alias": "backup-vpn",
            "site": "remote-access",
            "tags": ["vpn", "backup"],
            "rdns": "backup-vpn.example",
            "rdns_pending": False,
            "asn": "AS64503",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 12,
            "ip": "198.51.100.61",
            "host": "198.51.100.61",
            "alias": "partner-vpn",
            "site": "remote-access",
            "tags": ["wan", "demo"],
            "rdns": "partner-vpn.example",
            "rdns_pending": False,
            "asn": "AS64504",
            "asn_pending": False,
            "active": True,
        },
        {
            "id": 13,
            "ip": "203.0.113.80",
            "host": "203.0.113.80",
            "alias": "noc-jumpbox",
            "site": "operations",
            "tags": ["admin", "ssh"],
            "rdns": "noc-jumpbox.example",
            "rdns_pending": False,
            "asn": "AS64505",
            "asn_pending": False,
            "active": True,
        },
    ]


def make_buffers(patterns: Sequence[str]) -> Dict[int, Dict[str, Any]]:
    buffers: Dict[int, Dict[str, Any]] = {}
    for host_id, pattern in enumerate(patterns):
        timeline = list(pattern)
        rtts = []
        ttl = []
        categories = {name: deque(maxlen=len(timeline)) for name in SYMBOLS}
        for idx, symbol in enumerate(timeline):
            if symbol == "x":
                rtts.append(None)
                ttl.append(None)
            elif symbol == "!":
                rtts.append(0.18 + (idx % 5) * 0.018)
                ttl.append(55)
            elif symbol == "-":
                rtts.append(None)
                ttl.append(None)
            else:
                rtts.append(0.009 + host_id * 0.004 + (idx % 7) * 0.0017)
                ttl.append(64 - host_id)
            for name, marker in SYMBOLS.items():
                categories[name].append(1 if symbol == marker else 0)
        buffers[host_id] = {
            "timeline": deque(timeline, maxlen=len(timeline)),
            "rtt_history": deque(rtts, maxlen=len(timeline)),
            "time_history": deque([float(i) for i in range(len(timeline))], maxlen=len(timeline)),
            "ttl_history": deque(ttl, maxlen=len(timeline)),
            "categories": categories,
        }
    return buffers


def make_stats(patterns: Sequence[str]) -> Dict[int, Dict[str, Any]]:
    stats: Dict[int, Dict[str, Any]] = {}
    for host_id, pattern in enumerate(patterns):
        success = pattern.count(".")
        slow = pattern.count("!")
        fail = pattern.count("x")
        pending = pattern.count("-")
        total = success + slow + fail + pending
        rtt_values = [0.012 + host_id * 0.005 + i * 0.0008 for i in range(success + slow)]
        stats[host_id] = {
            "success": success,
            "slow": slow,
            "fail": fail,
            "pending": pending,
            "total": total,
            "rtt_count": len(rtt_values),
            "rtt_sum": sum(rtt_values),
            "rtt_sum_sq": sum(value * value for value in rtt_values),
        }
    return stats


def render_lines(**kwargs: Any) -> List[str]:
    patterns = [
        "................................................",
        ".....................................!..........",
        "..........................!.....................",
        "................................................",
        "................................................",
        ".................!!...........!!!...............",
        "........xxx......!!......xxxx!!!!...............",
        "................................................",
        "......................----....x....----.........",
        "................................................",
        "...........................!....................",
        "..............xxxx..............xxxx............",
        "..................!!...............!!...........",
        "................................................",
    ]
    defaults: Dict[str, Any] = {
        "symbols": SYMBOLS,
        "panel_position": "right",
        "pulse_position": "none",
        "mode_label": "alias",
        "display_mode": "timeline",
        "summary_mode": "rates",
        "summary_scope": "host",
        "group_by": "none",
        "sort_mode": "config",
        "filter_mode": "all",
        "slow_threshold": 0.15,
        "show_help": False,
        "show_asn": True,
        "paused": False,
        "status_message": "demo data - no live network targets",
        "timestamp": "2026-06-07 12:00:00 (UTC)",
        "now_utc": datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc),
        "use_color": True,
    }
    defaults.update(kwargs)
    with patch("paraping.ui_render.get_terminal_size", return_value=os.terminal_size((132, 34))):
        return build_display_lines(make_hosts(), make_buffers(patterns), make_stats(patterns), **defaults)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")


def draw_ansi_line(draw: ImageDraw.ImageDraw, xy: tuple[int, int], line: str, font: ImageFont.ImageFont) -> None:
    x, y = xy
    color = "#c9d1d9"
    pos = 0
    for match in ANSI_RE.finditer(line):
        chunk = line[pos : match.start()]
        if chunk:
            draw.text((x, y), chunk, font=font, fill=color)
            x += int(draw.textlength(chunk, font=font))
        code = match.group(1)
        if code in ("0", ""):
            color = "#c9d1d9"
        elif "31" in code:
            color = "#ff6b6b"
        elif "32" in code:
            color = "#7ee787"
        elif "33" in code:
            color = "#ffd166"
        elif "34" in code:
            color = "#79c0ff"
        pos = match.end()
    tail = line[pos:]
    if tail:
        draw.text((x, y), tail, font=font, fill=color)


def save_terminal_image(lines: Iterable[str], filename: str) -> None:
    clean_lines = [line.rstrip() for line in lines]
    font = load_font(15)
    title_font = load_font(14)
    line_height = 20
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    text_width = max((int(measure.textlength(strip_ansi(line), font=font)) for line in clean_lines), default=800)
    width = max(text_width + 68, 1120)
    height = max(len(clean_lines) * line_height + 72, 520)

    image = Image.new("RGB", (width, height), "#101418")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((16, 16, width - 16, height - 16), radius=14, fill="#0d1117", outline="#30363d", width=1)
    draw.ellipse((34, 34, 46, 46), fill="#ff5f57")
    draw.ellipse((54, 34, 66, 46), fill="#febc2e")
    draw.ellipse((74, 34, 86, 46), fill="#28c840")
    draw.text((106, 29), "paraping demo", font=title_font, fill="#8b949e")

    y = 62
    for line in clean_lines:
        draw_ansi_line(draw, (34, y), line, font)
        y += line_height

    image.save(ASSET_DIR / filename)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    scenarios = {
        "timeline-overview.png": {"panel_position": "right", "mode_label": "alias", "display_mode": "timeline"},
        "group-summary.png": {
            "panel_position": "bottom",
            "mode_label": "alias",
            "display_mode": "timeline",
            "summary_scope": "group",
            "group_by": "site>tag1",
            "group_sort_enabled": True,
        },
        "asn-rdns.png": {"panel_position": "right", "mode_label": "rdns", "display_mode": "sparkline"},
        "latency-failures.png": {
            "panel_position": "right",
            "mode_label": "alias",
            "display_mode": "square",
            "sort_mode": "failures",
            "summary_mode": "rtt",
        },
        "summary-fullscreen.png": {
            "panel_position": "none",
            "mode_label": "alias",
            "display_mode": "timeline",
            "summary_fullscreen": True,
            "summary_scope": "group",
            "group_by": "site",
        },
    }
    for filename, options in scenarios.items():
        save_terminal_image(render_lines(**options), filename)
        print(f"generated {ASSET_DIR / filename}")


if __name__ == "__main__":
    main()
