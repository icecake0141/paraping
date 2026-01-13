<!--
Copyright 2025 icecake0141
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
-->

# MultiPing

MultiPing is an interactive, terminal-based ICMP monitor that pings many hosts in parallel and visualizes results as a live timeline or sparkline. It adds useful operator controls like sorting, filtering, pause modes, snapshots, and optional ASN/rDNS display for fast network triage.

> 日本語版 README: [README.ja.md](README.ja.md)

## Features
- Concurrent ICMP ping to multiple hosts (capability-based helper binary).
- Live timeline or sparkline visualization with success/slow/fail markers.
- Animated activity indicator (Knight Rider-style) while pings are running.
- Summary panel with host statistics, aggregate counts, and TTL display.
- Summary host ordering matches the current ping result sort order.
- Sort and filter results by failures, streaks, latency, or host name.
- Toggle display name mode: IP, reverse DNS, or alias.
- Optional ASN display (fetched from Team Cymru) with auto-retry.
- Optional colored output for success/slow/fail states.
- Pause modes: freeze display only or pause ping + display.
- Snapshot export to a timestamped text file.
- Configurable timezone for timestamps and snapshot naming.
- Input file support for host lists (one per line in `IP,alias` format; comments allowed).

## Requirements
- Python 3.9 or newer.
- The `ping_helper` binary built with `cap_net_raw` (Linux) to run without `sudo`.
- Root/administrator privileges if you cannot use the helper (non-Linux platforms).
- Network access for optional ASN lookups.
- IPv4-only support (hosts must resolve to IPv4 addresses).

### Linux-Specific: Privileged ICMP Helper (Recommended)

On Linux, use the included `ping_helper` binary with capability-based privileges instead of running Python as root. This is more secure as it limits raw socket access to a single small binary.
The helper also connects its raw socket and applies ICMP filters to reduce per-process packet fan-out, which improves reliability when monitoring many hosts concurrently.

**Dependencies:**
- `gcc` (for building the helper)
- `libcap2-bin` (for setting capabilities with `setcap`)

Install dependencies on Debian/Ubuntu:
```bash
sudo apt-get install gcc libcap2-bin
```

**Build and configure the helper:**
```bash
# Build the helper binary
make build

# Set capabilities (requires sudo)
sudo make setcap

# Test the helper
python3 ping_wrapper.py google.com
```

If `ping_wrapper.py` fails, its JSON output includes an `error` field with details from `ping_helper` (including stderr when available) to aid troubleshooting.

**Note for macOS/BSD users:** The `setcap` command is Linux-specific and not available on macOS or BSD systems. On these platforms, you would need to use the setuid bit instead (e.g., `sudo chown root:wheel ping_helper && sudo chmod u+s ping_helper`), but this is not recommended for security reasons. It's better to run the main Python script with `sudo` on these platforms.

**Security Note:** Never grant `cap_net_raw` or any capabilities to `/usr/bin/python3` or other general-purpose interpreters. Only grant the minimal required privilege to the specific `ping_helper` binary.

## Installation
```bash
git clone https://github.com/icecake0141/multiping.git
cd multiping
python -m pip install -r requirements.txt

# Build the privileged ICMP helper (Linux only)
make build
sudo make setcap
```

## Usage

![MultiPing Demo](docs/images/usage-demo.gif)

```bash
python main.py [options] <host1> <host2> ...
```

Example (with a host list file and 2-second timeout):
```bash
python main.py -t 2 -f hosts.txt
```
Example (explicit IPv4 addresses only):
```bash
python main.py 1.1.1.1 8.8.8.8
```

### Command-line Options
- `-t`, `--timeout`: Timeout in seconds for each ping (default: 1).
- `-c`, `--count`: Number of ping attempts per host (default: 0 for infinite).
- `-i`, `--interval`: Interval in seconds between pings per host (default: 1.0, range: 0.1-60.0).
- `--slow-threshold`: RTT threshold (seconds) to mark a ping as slow (default: 0.5).
- `-v`, `--verbose`: Print raw per-packet output (non-UI).
- `-f`, `--input`: Read hosts from a file (one per line; format: `IP,alias`; `#` comments supported).
- `--panel-position`: Summary panel position (`right|left|top|bottom|none`).
- `--pause-mode`: Pause behavior (`display|ping`).
- `--timezone`: IANA timezone name for on-screen timestamps.
- `--snapshot-timezone`: Timezone for snapshot filenames (`utc|display`).
- `--flash-on-fail`: Flash screen (invert colors) when a ping fails to draw attention.
- `--bell-on-fail`: Ring terminal bell when a ping fails to draw attention.
- `--color`: Enable colored output (blue=success, yellow=slow, red=fail).
- `--ping-helper`: Path to the `ping_helper` binary (default: `./ping_helper`).

### Interactive Controls
- `n`: Cycle display name mode (ip/rdns/alias).
- `v`: Toggle view (timeline/sparkline).
- `o`: Cycle sort (failures/streak/latency/host).
- `f`: Cycle filter (failures/latency/all).
- `a`: Toggle ASN display (auto hides when space is tight).
- `m`: Cycle summary info (rates/avg RTT/TTL/streak).
- `w`: Toggle the summary panel on/off.
- `W`: Cycle summary panel position (left/right/top/bottom).
- `p`: Pause/resume (display only or ping + display).
- `s`: Save a snapshot to `multiping_snapshot_YYYYMMDD_HHMMSS.txt`.
- `←` / `→`: Navigate backward/forward in time by one page. History keeps recording while browsing; the view is frozen until you return to live.
- `↑` / `↓`: Scroll the host list when it exceeds the terminal height.
- `H`: Show help (press any key to close).
- `q`: Quit.

### Timeline/Sparkline Legend
- `.` success
- `!` slow (RTT >= `--slow-threshold`)
- `x` failure/timeout
- When `--color` is enabled: blue=success, yellow=slow, red=failure.

## Notes
- ICMP requires elevated privileges (run with `sudo` or Administrator on Windows).
- ASN lookups use `whois.cymru.com`; blocked networks will show blank ASN values.
- IPv6 is not supported; use IPv4 addresses or hostnames that resolve to IPv4.
- When the summary panel is positioned at the top/bottom, it expands to use available empty rows.
- When the summary panel is positioned at the top/bottom, it shows all summary fields if the width allows.

## License
Apache License 2.0. See [LICENSE](LICENSE).
