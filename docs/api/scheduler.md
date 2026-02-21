<!--
Copyright 2026 icecake0141
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
-->

# Scheduler API Reference

## English

## Overview

The `Scheduler` class in `paraping/scheduler.py` provides time-driven ping scheduling that eliminates timeline drift. Instead of sleeping between pings, the scheduler computes precise next-ping timestamps anchored to a single `start_time`, so that clock drift does not accumulate across long monitoring sessions.

Key concepts:

- **Interval** – seconds between consecutive pings to the *same* host (e.g. `1.0`).
- **Stagger** – seconds of offset added between consecutive *hosts* so they do not all fire at once.
- **Start time** – anchors all first-ping offsets; set once on the first call to `get_next_ping_times()`.

> **Important**: ParaPing's CLI enforces `0.1 ≤ interval ≤ 60.0` seconds.  Passing a value outside this range will be rejected before the scheduler is constructed.  The global rate limit of 50 pings/sec (`host_count / interval ≤ 50`) is also validated before the scheduler is started.

---

## Basic Usage

```python
from paraping.scheduler import Scheduler

# Create a scheduler: ping every 1 second, stagger hosts by 0.05 s
scheduler = Scheduler(interval=1.0, stagger=0.05)

scheduler.add_host("8.8.8.8")
scheduler.add_host("1.1.1.1")

# Compute when each host should next be pinged
next_times = scheduler.get_next_ping_times()
# Returns something like:
# {"8.8.8.8": 1740134400.000, "1.1.1.1": 1740134400.050}
```

After sending a ping you **must** call `mark_ping_sent()` so the scheduler can compute the correct next time:

```python
import time

for host, t in next_times.items():
    # Wait until the scheduled time
    delay = t - time.time()
    if delay > 0:
        time.sleep(delay)
    # ... send ping ...
    scheduler.mark_ping_sent(host, sent_time=t)
```

---

## Class Reference

### `Scheduler(interval=1.0, stagger=0.0)`

Create a new scheduler.

| Parameter  | Type    | Default | Description |
|------------|---------|---------|-------------|
| `interval` | `float` | `1.0`   | Seconds between consecutive pings to the same host. |
| `stagger`  | `float` | `0.0`   | Seconds of offset added per host index for the first ping. |

---

### `add_host(host, host_id=None)`

Register a host for scheduling.

| Parameter  | Type             | Default | Description |
|------------|------------------|---------|-------------|
| `host`     | `str`            | —       | Hostname or IP address. |
| `host_id`  | `int` or `None`  | `None`  | Optional numeric identifier. Auto-assigned if omitted. |

Adding the same host twice has no effect (deduplication is applied).

---

### `get_next_ping_times(current_time=None)`

Compute the next scheduled ping time for every registered host.

| Parameter      | Type            | Default        | Description |
|----------------|-----------------|----------------|-------------|
| `current_time` | `float` or `None` | `time.time()` | Current Unix timestamp. Useful for deterministic testing. |

**Returns** `dict[str, float]` – mapping from host name to Unix timestamp.

On the first call, `start_time` is set to `current_time`.  All subsequent first-ping offsets are anchored to this value regardless of when `get_next_ping_times()` is called again, preventing drift.

---

### `mark_ping_sent(host, sent_time=None)`

Record that a ping was dispatched to `host`.  The next call to `get_next_ping_times()` will advance that host's schedule by `interval`.

| Parameter   | Type            | Default        | Description |
|-------------|-----------------|----------------|-------------|
| `host`      | `str`           | —              | Host name previously added via `add_host()`. |
| `sent_time` | `float` or `None` | `time.time()` | Timestamp of dispatch. |

---

### `set_interval(interval)` / `set_stagger(stagger)`

Update the interval or stagger after construction.  Changes take effect for the *next* computed ping time.

---

### `emit_mock_send_events(count=1)`

Generate a list of mock send-event dictionaries for testing purposes without performing real network operations.

```python
scheduler = Scheduler(interval=1.0, stagger=0.1)
scheduler.add_host("10.0.0.1")
scheduler.add_host("10.0.0.2")

events = scheduler.emit_mock_send_events(count=2)
# events is a flat list of dicts:
# [
#   {"host": "10.0.0.1", "scheduled_time": ..., "sequence": 1, "event_type": "send"},
#   {"host": "10.0.0.2", "scheduled_time": ..., "sequence": 1, "event_type": "send"},
#   {"host": "10.0.0.1", "scheduled_time": ..., "sequence": 2, "event_type": "send"},
#   {"host": "10.0.0.2", "scheduled_time": ..., "sequence": 2, "event_type": "send"},
# ]
```

---

### `get_host_count()` / `get_hosts()`

Utility accessors:

```python
scheduler.get_host_count()  # -> int
scheduler.get_hosts()       # -> list[str] (copy)
```

---

### `reset()`

Clear all hosts and timing state.  After calling `reset()` the scheduler can be reused as if freshly constructed.

---

## Stagger Calculation

Stagger spreads the *first* ping of each host across time so that large host lists do not cause a burst of simultaneous ICMP packets.

```
Host index 0: T,       T+I,       T+2I, ...
Host index 1: T+S,     T+S+I,     T+S+2I, ...
Host index 2: T+2S,    T+2S+I,    T+2S+2I, ...
Host index N: T+N*S,   T+N*S+I,   T+N*S+2I, ...

Where T = start_time, I = interval, S = stagger
```

ParaPing computes the stagger automatically from the CLI as:

```
stagger = interval / host_count
```

This spreads all first pings evenly across exactly one interval period.

### Example: 10 hosts, 1.0 s interval

```python
scheduler = Scheduler(interval=1.0, stagger=0.1)   # 1.0 / 10 = 0.1 s per host

for i, host in enumerate(hosts):
    scheduler.add_host(host)

# First-ping schedule (relative to T=0):
# host[0] -> 0.0 s
# host[1] -> 0.1 s
# host[2] -> 0.2 s
# ...
# host[9] -> 0.9 s
```

### Example: 50 hosts, 1.0 s interval

```python
stagger = 1.0 / 50   # = 0.02 s
scheduler = Scheduler(interval=1.0, stagger=stagger)
# Pings spread over the full 1-second interval; no burst.
```

Without stagger (`stagger=0.0`) all 50 hosts would fire at `T`, `T+1`, `T+2`, … causing 50 simultaneous ICMP packets each second.

---

## Real-World Scenarios

### Monitoring 10 hosts at 1 s interval

```python
from paraping.scheduler import Scheduler
import time

hosts = [f"10.0.0.{i}" for i in range(1, 11)]
scheduler = Scheduler(interval=1.0, stagger=0.1)
for host in hosts:
    scheduler.add_host(host)

for _round in range(5):                      # 5 ping rounds
    next_times = scheduler.get_next_ping_times()
    for host, t in sorted(next_times.items(), key=lambda x: x[1]):
        delay = t - time.time()
        if delay > 0:
            time.sleep(delay)
        # send_ping(host)  # your ping implementation here
        scheduler.mark_ping_sent(host, sent_time=t)
```

### Monitoring 50 hosts at 1 s interval

```python
hosts = [f"192.168.1.{i}" for i in range(1, 51)]
# 50 hosts / 1.0 s = 50 pings/sec  (exactly at the global rate limit)
stagger = 1.0 / len(hosts)          # = 0.02 s
scheduler = Scheduler(interval=1.0, stagger=stagger)
for host in hosts:
    scheduler.add_host(host)
```

### Slow network with longer interval

```python
# Monitor 20 remote hosts that may have 200+ ms RTT
scheduler = Scheduler(interval=5.0, stagger=0.25)   # 5 s / 20 hosts = 0.25 s stagger
```

### Integration with a custom event loop

```python
import asyncio
from paraping.scheduler import Scheduler

async def ping_loop(scheduler, hosts, rounds=10):
    for host in hosts:
        scheduler.add_host(host)

    for _round in range(rounds):
        next_times = scheduler.get_next_ping_times()
        for host, t in sorted(next_times.items(), key=lambda x: x[1]):
            now = asyncio.get_event_loop().time()
            # asyncio uses its own clock; convert if needed
            delay = t - __import__("time").time()
            if delay > 0:
                await asyncio.sleep(delay)
            # await async_send_ping(host)
            scheduler.mark_ping_sent(host, sent_time=t)

asyncio.run(ping_loop(Scheduler(interval=1.0, stagger=0.05), ["8.8.8.8", "1.1.1.1"]))
```

> **Tip**: The scheduler is not thread-safe by default. When using it from multiple threads, protect all scheduler calls with a `threading.Lock()`.  ParaPing's own CLI wraps the scheduler in a `ping_lock` for this reason.

---

## Troubleshooting

### Q: Why is my interval value rejected?

The CLI enforces `0.1 ≤ interval ≤ 60.0` seconds:

```
Error: --interval must be between 0.1 and 60.0 seconds.
```

**Reason**: Values below 0.1 s would require the scheduler to fire more than 10 times per second per host.  Combined with process-spawn overhead (~1–5 ms per ping helper invocation), sub-0.1 s intervals produce unreliable results and excessive system load.

**Fix**: Use `--interval 0.1` as the minimum, or reduce the number of monitored hosts.

---

### Q: I'm monitoring 60 hosts with a 1 s interval and the tool exits with a rate-limit error

```
Error: Rate limit (50 pings/sec) would be exceeded (calculated: 60.0 pings/sec)
Suggestions:
  1. Reduce host count from 60 to 50 (at 1.0s interval)
  2. Increase interval from 1.0s to 1.2s (with 60 hosts)
  3. Run multiple paraping instances with different host subsets
```

**Reason**: `host_count / interval = 60 / 1.0 = 60 pings/sec`, which exceeds the 50 pings/sec global limit.

**Fix**: Either increase `--interval` or split hosts across multiple `paraping` instances:

```bash
# Instance A: first 30 hosts
paraping --interval 1.0 host1 host2 ... host30

# Instance B: remaining hosts
paraping --interval 1.0 host31 ... host60
```

---

### Q: Why are my timeline columns misaligned?

Timeline columns drift when `mark_ping_sent()` is not called promptly after each ping.  The scheduler advances a host's schedule only when `mark_ping_sent()` records `last_ping_time`.  If that call is delayed, subsequent pings will appear offset in the timeline display.

**Fix**: Call `mark_ping_sent(host, sent_time=scheduled_time)` immediately after dispatching the ping, passing the *scheduled* time (not `time.time()`) to keep the timeline anchored.

---

### Q: All hosts fire at the same time despite stagger being set

This happens when hosts are added *after* the first call to `get_next_ping_times()`.  At that point `start_time` is already set, but the newly added host has `last_ping_time = None`, so it will be scheduled for `start_time + (idx * stagger)` where `idx` reflects the insertion order at the time of the *next* `get_next_ping_times()` call.

**Fix**: Add all hosts *before* the first call to `get_next_ping_times()`.

---

### Q: How do I reset and re-use a scheduler?

```python
scheduler.reset()
# Now re-add hosts and start a new session
for host in new_hosts:
    scheduler.add_host(host)
```

`reset()` clears `hosts`, `host_data`, and `start_time`, returning the object to its initial state.

---

### Q: `emit_mock_send_events` sequence numbers don't match my expectations

`emit_mock_send_events(count=N)` generates `N` complete rounds for **all** registered hosts.  Sequence numbers reflect `ping_count + 1` at the moment the event is generated, and `ping_count` is incremented as events are emitted.  If you call `emit_mock_send_events` multiple times, sequence numbers continue from where they left off:

```python
scheduler.emit_mock_send_events(count=2)   # sequences 1, 2
scheduler.emit_mock_send_events(count=1)   # sequence 3
```

Call `reset()` between test runs if you need sequence numbers to restart from 1.

---

## Public Methods Summary

| Method | Returns | Description |
|--------|---------|-------------|
| `add_host(host, host_id=None)` | `None` | Register a host. |
| `set_interval(interval)` | `None` | Update ping interval. |
| `set_stagger(stagger)` | `None` | Update host stagger offset. |
| `get_next_ping_times(current_time=None)` | `dict[str, float]` | Compute next scheduled time per host. |
| `mark_ping_sent(host, sent_time=None)` | `None` | Record a dispatched ping. |
| `emit_mock_send_events(count=1)` | `list[dict]` | Generate mock events for testing. |
| `get_host_count()` | `int` | Number of registered hosts. |
| `get_hosts()` | `list[str]` | Copy of the host list. |
| `reset()` | `None` | Clear all state. |

---

## See Also

- [API Index](index.md) – Overview of all ParaPing modules
- [ping_helper Documentation](../ping_helper.md) – Underlying ICMP helper binary
- Source: `paraping/scheduler.py`
- Tests: `tests/unit/test_scheduler.py`, `tests/unit/test_scheduler_integration.py`

---

## 日本語

# Scheduler API リファレンス

## 概要

`paraping/scheduler.py` の `Scheduler` クラスは、タイムラインのドリフトを排除する時間駆動のpingスケジューリングを提供します。ping間でスリープする代わりに、スケジューラは単一の `start_time` に固定された正確な次回ping時刻を計算します。

主要な概念：

- **interval（間隔）** – 同一ホストへの連続pingの間隔（秒）（例：`1.0`）
- **stagger（ずらし）** – 連続するホスト間に追加されるオフセット（秒）（バースト防止）
- **start_time（開始時刻）** – 最初の `get_next_ping_times()` 呼び出し時に設定される基準時刻

> **重要**: ParaPingのCLIは `0.1 ≤ interval ≤ 60.0` 秒を強制します。また、グローバルレート制限（`host_count / interval ≤ 50` pings/sec）もスケジューラ起動前に検証されます。

## 基本的な使用方法

```python
from paraping.scheduler import Scheduler

# 1秒ごとにping、ホスト間を0.05秒ずらす
scheduler = Scheduler(interval=1.0, stagger=0.05)

scheduler.add_host("8.8.8.8")
scheduler.add_host("1.1.1.1")

next_times = scheduler.get_next_ping_times()
# 戻り値例: {"8.8.8.8": 1740134400.000, "1.1.1.1": 1740134400.050}
```

## stagger の計算

staggerは最初のpingを時間的に分散させ、大量ホストによるバーストを防ぎます：

```
ホスト0: T,     T+I,     T+2I, ...
ホスト1: T+S,   T+S+I,   T+S+2I, ...
ホストN: T+N*S, T+N*S+I, T+N*S+2I, ...

T=開始時刻、I=interval、S=stagger
```

ParaPingのCLIは `stagger = interval / host_count` として自動計算します。

## トラブルシューティング

**Q: なぜintervalが拒否されるのですか？**
CLIは `0.1 ≤ interval ≤ 60.0` 秒を強制します。0.1秒未満はシステム負荷と信頼性の問題があります。

**Q: タイムラインの列がずれるのはなぜですか？**
スケジュールされた時刻を `mark_ping_sent()` に渡さないと、ドリフトが発生します。`mark_ping_sent(host, sent_time=scheduled_time)` のようにスケジュール時刻を渡してください。

**Q: レート制限エラーが出ます。**
`host_count / interval > 50` の場合にエラーになります。intervalを増やすか、ホストを複数インスタンスに分割してください。
