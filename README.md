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
- Concurrent ICMP ping to multiple hosts (Scapy-based).
- Live timeline or sparkline visualization with success/slow/fail markers.
- Summary panel with host statistics, aggregate counts, and TTL display.
- Sort and filter results by failures, streaks, latency, or host name.
- Toggle display name mode: IP, reverse DNS, or alias.
- Optional ASN display (fetched from Team Cymru) with auto-retry.
- Pause modes: freeze display only or pause ping + display.
- Snapshot export to a timestamped text file.
- Configurable timezone for timestamps and snapshot naming.
- Input file support for host lists (one per line, comments allowed).

## Requirements
- Python 3.9 or newer.
- `scapy` (see `requirements.txt`).
- Root/administrator privileges to send ICMP packets.
- Network access for optional ASN lookups.

## Installation
```bash
git clone https://github.com/icecake0141/multiping.git
cd multiping
python -m pip install -r requirements.txt
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

### Command-line Options
- `-t`, `--timeout`: Timeout in seconds for each ping (default: 1).
- `-c`, `--count`: Number of ping attempts per host (default: 0 for infinite).
- `-i`, `--interval`: Interval in seconds between pings per host (default: 1.0, range: 0.1-60.0).
- `--slow-threshold`: RTT threshold (seconds) to mark a ping as slow (default: 0.5).
- `-v`, `--verbose`: Print raw per-packet output (non-UI).
- `-f`, `--input`: Read hosts from a file (one per line; `#` comments supported).
- `--panel-position`: Summary panel position (`right|left|top|bottom|none`).
- `--pause-mode`: Pause behavior (`display|ping`).
- `--timezone`: IANA timezone name for on-screen timestamps.
- `--snapshot-timezone`: Timezone for snapshot filenames (`utc|display`).
- `--flash-on-fail`: Flash screen (invert colors) when a ping fails to draw attention.
- `--bell-on-fail`: Ring terminal bell when a ping fails to draw attention.

### Interactive Controls
- `n`: Cycle display name mode (ip/rdns/alias).
- `v`: Toggle view (timeline/sparkline).
- `o`: Cycle sort (failures/streak/latency/host).
- `f`: Cycle filter (failures/latency/all).
- `a`: Toggle ASN display (auto hides when space is tight).
- `p`: Pause/resume (display only or ping + display).
- `s`: Save a snapshot to `multiping_snapshot_YYYYMMDD_HHMMSS.txt`.
- `←` / `→`: Navigate backward/forward in time (view monitoring history up to 30 minutes).
- `H`: Show help (press any key to close).
- `q`: Quit.

### Timeline/Sparkline Legend
- `.` success
- `!` slow (RTT >= `--slow-threshold`)
- `x` failure/timeout

## Notes
- ICMP requires elevated privileges (run with `sudo` or Administrator on Windows).
- ASN lookups use `whois.cymru.com`; blocked networks will show blank ASN values.

## License
Apache License 2.0. See [LICENSE](LICENSE).
