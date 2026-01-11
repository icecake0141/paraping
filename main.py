#!/usr/bin/env python3

import argparse
import queue
import select
import shutil
import socket
import sys
import termios
import time
import tty
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from scapy.all import ICMP, IP, sr

# A handler for command line options


def handle_options():

    parser = argparse.ArgumentParser(description="MultiPing - Perform ICMP ping operations to multiple hosts concurrently")
    parser.add_argument('-t', '--timeout', type=int, default=1, help='Timeout in seconds for each ping (default: 1)')
    parser.add_argument('-c', '--count', type=int, default=4, help='Number of ping attempts per host (default: 4)')
    parser.add_argument('--slow-threshold', type=float, default=0.5, help='Threshold in seconds for slow ping (default: 0.5)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output, showing detailed ping results')
    parser.add_argument('-f', '--input', type=str, help='Input file containing list of hosts (one per line)', required=False)
    parser.add_argument(
        '--panel-position',
        type=str,
        default='right',
        choices=['right', 'left', 'top', 'bottom', 'none'],
        help='Summary panel position (right|left|top|bottom|none)',
    )
    parser.add_argument('hosts', nargs='*', help='Hosts to ping (IP addresses or hostnames)')

    args = parser.parse_args()
    return args


# Read input file. The file contains a list of hosts (IP addresses or hostnames)


def read_input_file(input_file):

    host_list = []
    try:
        with open(input_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    host_list.append(line)
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


def ping_host(host, timeout, count, slow_threshold, verbose):
    """
    Ping a single host with the specified parameters.

    Args:
        host: The hostname or IP address to ping
        timeout: Timeout in seconds for each ping
        count: Number of ping attempts
        verbose: Whether to show detailed output

    Yields:
        A dict with host, sequence, status, and rtt
    """
    if verbose:
        print(f"\n--- Pinging {host} ---")

    for i in range(count):
        try:
            # Create ICMP packet
            icmp = IP(dst=host)/ICMP()

            # Send ICMP packet
            ans, unans = sr(icmp, timeout=timeout, verbose=0)

            if ans:
                sent, received = ans[0]
                rtt = received.time - sent.time
                status = "slow" if rtt >= slow_threshold else "success"
                if verbose:
                    print(f"Reply from {host}: seq={i+1} rtt={rtt:.3f}s")
                    for r in ans:
                        r[1].show()
                yield {"host": host, "sequence": i + 1, "status": status, "rtt": rtt}
            else:
                if verbose:
                    print(f"No reply from {host}: seq={i+1}")
                yield {"host": host, "sequence": i + 1, "status": "fail", "rtt": None}
        except OSError as e:
            if verbose:
                print(f"Network error pinging {host}: {e}")
            yield {"host": host, "sequence": i + 1, "status": "fail", "rtt": None}
        except Exception as e:
            if verbose:
                print(f"Error pinging {host}: {e}")
            yield {"host": host, "sequence": i + 1, "status": "fail", "rtt": None}


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
    return f"{host:<{label_width}} | {timeline}"


def resize_buffers(buffers, timeline_width, symbols):
    for host, host_buffers in buffers.items():
        if host_buffers["timeline"].maxlen != timeline_width:
            host_buffers["timeline"] = deque(host_buffers["timeline"], maxlen=timeline_width)
        if host_buffers["rtt_history"].maxlen != timeline_width:
            host_buffers["rtt_history"] = deque(host_buffers["rtt_history"], maxlen=timeline_width)
        for status in symbols:
            if host_buffers["categories"][status].maxlen != timeline_width:
                host_buffers["categories"][status] = deque(
                    host_buffers["categories"][status], maxlen=timeline_width
                )


def pad_lines(lines, width, height):
    padded = [line[:width].ljust(width) for line in lines[:height]]
    while len(padded) < height:
        padded.append("".ljust(width))
    return padded


def compute_summary_data(hosts, display_names, buffers, stats, symbols):
    summary = []
    success_symbols = {symbols["success"], symbols["slow"]}
    for host in hosts:
        display_name = display_names.get(host, host)
        total = stats[host]["total"]
        success = stats[host]["success"] + stats[host]["slow"]
        fail = stats[host]["fail"]
        success_rate = (success / total * 100) if total > 0 else 0.0
        loss_rate = (fail / total * 100) if total > 0 else 0.0
        timeline = list(buffers[host]["timeline"])
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
        if stats[host]["rtt_count"] > 0:
            avg_rtt_ms = stats[host]["rtt_sum"] / stats[host]["rtt_count"] * 1000
        summary.append(
            {
                "host": display_name,
                "success_rate": success_rate,
                "loss_rate": loss_rate,
                "streak_type": streak_type,
                "streak_length": streak_length,
                "avg_rtt_ms": avg_rtt_ms,
            }
        )
    return summary


def render_summary_view(summary_data, width, height):
    if width <= 0 or height <= 0:
        return []

    lines = ["Summary", "-" * width]
    for entry in summary_data:
        streak_label = "-"
        if entry["streak_type"] == "fail":
            streak_label = f"F{entry['streak_length']}"
        elif entry["streak_type"] == "success":
            streak_label = f"S{entry['streak_length']}"
        line = (
            f"{entry['host']}: ok {entry['success_rate']:.1f}% "
            f"loss {entry['loss_rate']:.1f}% streak {streak_label}"
        )
        lines.append(line)
        if entry["avg_rtt_ms"] is not None:
            lines.append(f"  avg rtt {entry['avg_rtt_ms']:.1f} ms")
        else:
            lines.append("  avg rtt n/a")

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


def render_timeline_view(display_entries, buffers, symbols, width, height, header, header_lines=2):
    if width <= 0 or height <= 0:
        return []

    host_labels = [entry[1] for entry in display_entries]
    width, label_width, timeline_width, visible_hosts = compute_main_layout(
        host_labels, width, height, header_lines
    )
    truncated_entries = display_entries[:visible_hosts]

    resize_buffers(buffers, timeline_width, symbols)

    lines = []
    lines.append(header)
    lines.append("".join("-" for _ in range(width)))
    for host, label in truncated_entries:
        timeline = "".join(buffers[host]["timeline"]).rjust(timeline_width)
        lines.append(format_status_line(label, timeline, label_width))

    if len(display_entries) > len(truncated_entries) and len(lines) < height:
        remaining = len(display_entries) - len(truncated_entries)
        lines.append(f"... ({remaining} host(s) not shown)")

    return pad_lines(lines, width, height)


def render_sparkline_view(display_entries, buffers, symbols, width, height, header, header_lines=2):
    if width <= 0 or height <= 0:
        return []

    host_labels = [entry[1] for entry in display_entries]
    width, label_width, timeline_width, visible_hosts = compute_main_layout(
        host_labels, width, height, header_lines
    )
    truncated_entries = display_entries[:visible_hosts]

    resize_buffers(buffers, timeline_width, symbols)

    lines = []
    lines.append(header)
    lines.append("".join("-" for _ in range(width)))
    for host, label in truncated_entries:
        rtt_values = list(buffers[host]["rtt_history"])[-timeline_width:]
        status_symbols = list(buffers[host]["timeline"])[-timeline_width:]
        sparkline = build_sparkline(rtt_values, status_symbols, symbols["fail"]).rjust(timeline_width)
        lines.append(format_status_line(label, sparkline, label_width))

    if len(display_entries) > len(truncated_entries) and len(lines) < height:
        remaining = len(display_entries) - len(truncated_entries)
        lines.append(f"... ({remaining} host(s) not shown)")

    return pad_lines(lines, width, height)


def render_main_view(
    display_entries,
    buffers,
    symbols,
    width,
    height,
    mode_label,
    display_mode,
    header_lines=2,
):
    header = f"MultiPing - Live results [{mode_label} | {display_mode}]"
    if display_mode == "sparkline":
        return render_sparkline_view(
            display_entries, buffers, symbols, width, height, header, header_lines
        )
    return render_timeline_view(
        display_entries, buffers, symbols, width, height, header, header_lines
    )


def compute_fail_streak(timeline, fail_symbol):
    streak = 0
    for symbol in reversed(timeline):
        if symbol == fail_symbol:
            streak += 1
        else:
            break
    return streak


def latest_rtt_value(rtt_history):
    if not rtt_history:
        return None
    return rtt_history[-1]


def build_display_entries(
    hosts,
    display_names,
    buffers,
    stats,
    symbols,
    sort_mode,
    filter_mode,
    slow_threshold,
):
    entries = []
    for host in hosts:
        timeline = buffers[host]["timeline"]
        latest_rtt = latest_rtt_value(buffers[host]["rtt_history"])
        fail_streak = compute_fail_streak(timeline, symbols["fail"])
        fail_count = stats[host]["fail"]

        include = True
        if filter_mode == "failures":
            include = fail_count > 0
        elif filter_mode == "latency":
            include = latest_rtt is not None and latest_rtt >= slow_threshold

        if include:
            entries.append(
                {
                    "host": host,
                    "label": display_names.get(host, host),
                    "fail_count": fail_count,
                    "fail_streak": fail_streak,
                    "latest_rtt": latest_rtt,
                }
            )

    if sort_mode == "failures":
        entries.sort(key=lambda item: (item["fail_count"], item["label"]), reverse=True)
    elif sort_mode == "streak":
        entries.sort(key=lambda item: (item["fail_streak"], item["label"]), reverse=True)
    elif sort_mode == "latency":
        entries.sort(
            key=lambda item: ((item["latest_rtt"] or -1.0), item["label"]),
            reverse=True,
        )
    elif sort_mode == "host":
        entries.sort(key=lambda item: item["label"])

    return [(entry["host"], entry["label"]) for entry in entries]


def build_status_line(sort_mode, filter_mode):
    sort_labels = {
        "failures": "失敗回数",
        "streak": "連続失敗",
        "latency": "最新遅延",
        "host": "ホスト名",
    }
    filter_labels = {"failures": "失敗のみ", "latency": "高遅延のみ", "all": "全件"}
    return f"ソート: {sort_labels.get(sort_mode, sort_mode)} | フィルタ: {filter_labels.get(filter_mode, filter_mode)}"


def render_help_view(width, height):
    lines = [
        "MultiPing - Help",
        "-" * width,
        "Keys:",
        "  n : cycle display mode (ip/rdns/alias)",
        "  v : toggle view (timeline/sparkline)",
        "  s : cycle sort (failures/streak/latency/host)",
        "  f : cycle filter (failures/latency/all)",
        "  a : toggle ASN display",
        "  h : toggle this help",
        "  q : quit",
    ]
    return pad_lines(lines, width, height)


def render_display(
    hosts,
    host_infos,
    buffers,
    stats,
    symbols,
    panel_position,
    mode_label,
    display_mode,
    sort_mode,
    filter_mode,
    slow_threshold,
    show_help,
    show_asn,
    asn_width=8,
    header_lines=2,
):
    term_size = shutil.get_terminal_size(fallback=(80, 24))
    term_width = term_size.columns
    term_height = term_size.lines

    include_asn = should_show_asn(host_infos, mode_label, show_asn, term_width, asn_width=asn_width)
    display_names = build_display_names(host_infos, mode_label, include_asn, asn_width)

    main_width, main_height, summary_width, summary_height, resolved_position = compute_panel_sizes(
        term_width, term_height, panel_position
    )
    summary_data = compute_summary_data(hosts, display_names, buffers, stats, symbols)

    display_entries = build_display_entries(
        hosts,
        display_names,
        buffers,
        stats,
        symbols,
        sort_mode,
        filter_mode,
        slow_threshold,
    )
    main_lines = render_main_view(
        display_entries,
        buffers,
        symbols,
        main_width,
        main_height,
        mode_label,
        display_mode,
        header_lines,
    )
    summary_lines = render_summary_view(summary_data, summary_width, summary_height)

    gap = " "
    combined_lines = []
    if show_help:
        combined_lines = render_help_view(term_width, term_height)
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

    status_line = build_status_line(sort_mode, filter_mode)
    if combined_lines:
        combined_lines[-1] = status_line[:term_width].ljust(term_width)

    print("\x1b[2J\x1b[H" + "\n".join(combined_lines), end="", flush=True)


def worker_ping(host, timeout, count, slow_threshold, verbose, result_queue):
    for result in ping_host(host, timeout, count, slow_threshold, verbose):
        result_queue.put(result)
    result_queue.put({"host": host, "status": "done"})


def resolve_display_name(host_info, mode):
    if mode == "ip":
        return host_info["ip"]
    if mode == "rdns":
        return host_info["rdns"] or host_info["ip"]
    if mode == "alias":
        return host_info["alias"]
    return host_info["ip"]


def format_display_name(host_info, mode, include_asn, asn_width):
    base_label = resolve_display_name(host_info, mode)
    if not include_asn:
        return base_label
    asn_label = host_info.get("asn") or ""
    return f"{base_label} {asn_label:<{asn_width}}"


def build_display_names(host_infos, mode, include_asn, asn_width):
    return {
        host: format_display_name(info, mode, include_asn, asn_width)
        for host, info in host_infos.items()
    }


def build_host_infos(hosts):
    host_infos = {}
    for host in hosts:
        try:
            ip_address = socket.gethostbyname(host)
        except (socket.gaierror, OSError):
            ip_address = host
        host_infos[host] = {
            "alias": host,
            "ip": ip_address,
            "rdns": None,
            "rdns_state": "pending",
            "asn": None,
            "asn_state": "pending",
        }
    return host_infos


def resolve_rdns(ip_address):
    try:
        return socket.gethostbyaddr(ip_address)[0]
    except (socket.herror, socket.gaierror, OSError):
        return None


def resolve_asn(ip_address, timeout=3.0):
    query = f" -v {ip_address}\n".encode("utf-8")
    try:
        with socket.create_connection(("whois.cymru.com", 43), timeout=timeout) as sock:
            sock.sendall(query)
            response = sock.recv(4096).decode("utf-8", errors="ignore")
    except (socket.timeout, OSError):
        return None

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


def should_show_asn(host_infos, mode, show_asn, term_width, min_timeline_width=10, asn_width=8):
    if not show_asn:
        return False
    labels = [
        format_display_name(info, mode, True, asn_width)
        for info in host_infos.values()
    ]
    if not labels:
        return False
    label_width = max(len(label) for label in labels)
    timeline_width = term_width - label_width - 3
    return timeline_width >= min_timeline_width


def read_key():
    if not sys.stdin.isatty():
        return None
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if ready:
        return sys.stdin.read(1)
    return None


def main(args):

    # Validate count parameter
    if args.count <= 0:
        print("Error: Count must be a positive number.")
        return

    # Collect all hosts to ping
    all_hosts = []

    # Add hosts from command line arguments
    if args.hosts:
        all_hosts.extend(args.hosts)

    # Add hosts from input file if provided
    if args.input:
        file_hosts = read_input_file(args.input)
        all_hosts.extend(file_hosts)

    # Check if we have any hosts to ping
    if not all_hosts:
        print("Error: No hosts specified. Provide hosts as arguments or use -f/--input option.")
        return

    symbols = {"success": ".", "fail": "x", "slow": "!"}
    term_size = shutil.get_terminal_size(fallback=(80, 24))
    _, _, timeline_width, _ = compute_main_layout(all_hosts, term_size.columns, term_size.lines)
    host_infos = build_host_infos(all_hosts)
    buffers = {
        host: {
            "timeline": deque(maxlen=timeline_width),
            "rtt_history": deque(maxlen=timeline_width),
            "categories": {status: deque(maxlen=timeline_width) for status in symbols},
        }
        for host in all_hosts
    }
    stats = {
        host: {"success": 0, "fail": 0, "slow": 0, "total": 0, "rtt_sum": 0.0, "rtt_count": 0}
        for host in all_hosts
    }
    result_queue = queue.Queue()

    print(
        f"MultiPing - Pinging {len(all_hosts)} host(s) with timeout={args.timeout}s, "
        f"count={args.count}, slow-threshold={args.slow_threshold}s"
    )

    modes = ["ip", "rdns", "alias"]
    mode_index = 0
    show_help = False
    display_modes = ["timeline", "sparkline"]
    display_mode_index = 0
    sort_modes = ["failures", "streak", "latency", "host"]
    sort_mode_index = 0
    filter_modes = ["failures", "latency", "all"]
    filter_mode_index = 2
    running = True
    show_asn = True
    rdns_timeout = 2.0
    rdns_futures = {}
    rdns_started = {}
    asn_timeout = 3.0
    asn_futures = {}
    asn_started = {}
    asn_cache = {}

    stdin_fd = None
    original_term = None
    if sys.stdin.isatty():
        stdin_fd = sys.stdin.fileno()
        original_term = termios.tcgetattr(stdin_fd)

    with ThreadPoolExecutor(max_workers=min(len(all_hosts), 10)) as executor:
        for host, info in host_infos.items():
            rdns_futures[host] = executor.submit(resolve_rdns, info["ip"])
            rdns_started[host] = time.time()
            if info["ip"] in asn_cache:
                cached_asn = asn_cache[info["ip"]]
                host_infos[host]["asn"] = cached_asn
                host_infos[host]["asn_state"] = "resolved" if cached_asn else "failed"
            else:
                asn_futures[host] = executor.submit(resolve_asn, info["ip"])
                asn_started[host] = time.time()
        for host in all_hosts:
            executor.submit(
                worker_ping,
                host,
                args.timeout,
                args.count,
                args.slow_threshold,
                args.verbose,
                result_queue,
            )

        completed_hosts = 0
        updated = True
        last_render = 0.0
        refresh_interval = 0.15
        try:
            if stdin_fd is not None:
                tty.setcbreak(stdin_fd)
            while running and completed_hosts < len(all_hosts):
                key = read_key()
                if key:
                    if key == "q":
                        running = False
                    elif key == "h":
                        show_help = not show_help
                        updated = True
                    elif key == "n":
                        mode_index = (mode_index + 1) % len(modes)
                        updated = True
                    elif key == "v":
                        display_mode_index = (display_mode_index + 1) % len(display_modes)
                        updated = True
                    elif key == "s":
                        sort_mode_index = (sort_mode_index + 1) % len(sort_modes)
                        updated = True
                    elif key == "f":
                        filter_mode_index = (filter_mode_index + 1) % len(filter_modes)
                        updated = True
                    elif key == "a":
                        show_asn = not show_asn
                        updated = True

                for host, future in list(rdns_futures.items()):
                    if host_infos[host]["rdns_state"] != "pending":
                        continue
                    if future.done():
                        host_infos[host]["rdns"] = future.result()
                        host_infos[host]["rdns_state"] = "resolved"
                        updated = True
                    elif time.time() - rdns_started[host] >= rdns_timeout:
                        future.cancel()
                        host_infos[host]["rdns_state"] = "timeout"
                        updated = True

                for host, future in list(asn_futures.items()):
                    if host_infos[host]["asn_state"] != "pending":
                        continue
                    if future.done():
                        asn_value = future.result()
                        host_infos[host]["asn"] = asn_value
                        host_infos[host]["asn_state"] = "resolved" if asn_value else "failed"
                        asn_cache[host_infos[host]["ip"]] = asn_value
                        updated = True
                    elif time.time() - asn_started[host] >= asn_timeout:
                        future.cancel()
                        host_infos[host]["asn_state"] = "timeout"
                        updated = True

                while True:
                    try:
                        result = result_queue.get_nowait()
                    except queue.Empty:
                        break
                    host = result["host"]
                    if result.get("status") == "done":
                        completed_hosts += 1
                        continue

                    status = result["status"]
                    buffers[host]["timeline"].append(symbols[status])
                    buffers[host]["rtt_history"].append(result.get("rtt"))
                    buffers[host]["categories"][status].append(result["sequence"])
                    stats[host][status] += 1
                    stats[host]["total"] += 1
                    if result.get("rtt") is not None:
                        stats[host]["rtt_sum"] += result["rtt"]
                        stats[host]["rtt_count"] += 1
                    updated = True

                now = time.time()
                if updated or (now - last_render) >= refresh_interval:
                    render_display(
                        all_hosts,
                        host_infos,
                        buffers,
                        stats,
                        symbols,
                        args.panel_position,
                        modes[mode_index],
                        display_modes[display_mode_index],
                        sort_modes[sort_mode_index],
                        filter_modes[filter_mode_index],
                        args.slow_threshold,
                        show_help,
                        show_asn,
                    )
                    last_render = now
                    updated = False

                time.sleep(0.05)
        finally:
            if stdin_fd is not None and original_term is not None:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, original_term)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for host in all_hosts:
        success = stats[host]["success"]
        slow = stats[host]["slow"]
        fail = stats[host]["fail"]
        total = stats[host]["total"]
        percentage = (success / total * 100) if total > 0 else 0
        status = "OK" if success > 0 else "FAILED"
        print(
            f"{host:30} {success}/{total} replies, {slow} slow, {fail} failed "
            f"({percentage:.1f}%) [{status}]"
        )


if __name__ == "__main__":
    # Handle command line options
    options = handle_options()
    main(options)
