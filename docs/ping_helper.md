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

# ping_helper Documentation

## English

## Overview

`ping_helper` is a minimal, capability-based ICMP ping utility written in C. It sends a single ICMP echo request and waits for a reply, printing the round-trip time (RTT) and TTL on success or exiting with a specific error code on failure.

## Design Philosophy

The helper is intentionally minimal and designed to run with `cap_net_raw` capability (on Linux) rather than requiring root privileges for the entire application. Each invocation:
- Sends exactly **one ICMP echo request**
- Waits for a matching reply or times out
- Exits immediately after receiving a valid reply or on timeout/error

This design is optimized for **one helper process per ping**, which is the current usage pattern in ParaPing.

## Command-Line Interface

### Usage

```bash
ping_helper <host> <timeout_ms> [icmp_seq]
```

### Arguments

- `<host>` (required): Hostname or IPv4 address to ping
- `<timeout_ms>` (required): Timeout in milliseconds (1-60000)
- `[icmp_seq]` (optional): ICMP sequence number (0-65535, default: 1)

### Examples

```bash
# Basic ping with 1 second timeout (default icmp_seq=1)
./bin/ping_helper google.com 1000

# Ping with custom sequence number
./bin/ping_helper 8.8.8.8 2000 42

# Ping with minimum timeout
./bin/ping_helper 1.1.1.1 100 1
```

## Output Format

### Success

On successful ping, the helper outputs to stdout:

```
rtt_ms=<value> ttl=<value>
```

Where:
- `rtt_ms`: Round-trip time in milliseconds (floating-point, 3 decimal places)
- `ttl`: Time-to-live from the IP header of the reply (integer)

**Example:**
```
rtt_ms=12.345 ttl=64
```

### Timeout

On timeout (no reply received within timeout_ms), the helper:
- Outputs nothing to stdout
- Exits with code **7**

### Errors

On errors, the helper:
- Outputs an error message to stderr
- Exits with a non-zero, non-7 exit code

## Exit Codes

| Code | Meaning | Notes |
|------|---------|-------|
| 0 | Success | Valid reply received |
| 1 | Invalid arguments | Wrong number of arguments |
| 2 | Argument validation error | Invalid timeout_ms or icmp_seq |
| 3 | Host resolution failed | Cannot resolve hostname |
| 4 | Socket error | Cannot create socket or insufficient privileges |
| 5 | Send error | Failed to send ICMP packet |
| 6 | Select error | Internal select() failure |
| 7 | **Timeout** | No reply within timeout_ms |
| 8 | Receive error | Failed to receive packet |

**Exit code 7 is reserved exclusively for timeouts** and should be treated as "no response" rather than an error.

## Packet Validation

The helper implements robust packet validation to avoid misattribution and handle corrupt packets:

### Reply Matching Criteria

A received packet is considered a valid reply only if **all** of these conditions are met:

1. **Minimum packet size**: At least 20 bytes (minimal IP header)
2. **IP header validation**:
   - IP header length between 20-60 bytes
   - IP version is 4
   - IP protocol is ICMP (1)
3. **ICMP header validation**:
   - Packet is long enough for IP header + 8-byte ICMP header
   - ICMP type is ECHOREPLY (0)
   - ICMP code is 0
4. **Identity matching**:
   - ICMP ID matches `getpid() & 0xFFFF`
   - ICMP sequence number matches the sent sequence
   - Source IP address matches the destination we sent to

Packets that don't match **any** of these criteria are silently discarded, and the helper continues waiting for a valid reply until timeout.

### Defense Against Edge Cases

- **Short packets**: Validated before accessing any fields
- **Corrupt IP headers**: Header length bounds-checked
- **Wrong protocol**: IP protocol field validated
- **Other processes' pings**: ID and sequence number filtering
- **Replies from wrong hosts**: Source address validation

## Assumptions and Limitations

### Current Design Assumptions

1. **One request per process**: Each helper instance sends exactly one ICMP echo request
2. **Process ID as identifier**: Uses `getpid() & 0xFFFF` for ICMP ID
   - Collision possible if multiple helpers run with recycled PIDs
   - Mitigated by sequence number matching and source address validation
3. **IPv4 only**: No IPv6 support
4. **Single host**: Each invocation targets exactly one host
5. **No retries**: Does not retry on packet loss; exits with timeout

### Safe Usage Constraints

- **One helper per ping**: Do not attempt to reuse a single helper process for multiple pings
- **Sequential invocations**: If running multiple helpers with the same host, ensure different sequence numbers or stagger timing to avoid ID collisions
- **Capability-based security (Linux)**: Use `cap_net_raw` on the binary, **never** on interpreters
- **Platform-specific**: Optimized for Linux; macOS/BSD may require different privilege handling

### Multi-Process and Batch Scenarios

When running multiple ping_helper processes concurrently (e.g., monitoring many hosts):

**Recommended practices:**
- Use different `icmp_seq` values when pinging the **same host** concurrently to avoid reply confusion
- Monitor system limits: check file descriptor limits (`ulimit -n`) and ICMP rate limits
- Consider process spawn overhead (~1-5ms per invocation) in high-frequency scenarios

**Example: Monitoring multiple hosts in parallel**
```bash
# Different hosts don't need unique sequence numbers (replies are distinguished by source IP)
./bin/ping_helper 8.8.8.8 1000 &
./bin/ping_helper 1.1.1.1 1000 &
./bin/ping_helper 9.9.9.9 1000 &
wait
```

**Example: Concurrent pings to the same host (use different sequence numbers)**
```bash
# Pinging the same host concurrently requires different icmp_seq to avoid confusion
./bin/ping_helper example.com 1000 1 &
./bin/ping_helper example.com 1000 2 &
./bin/ping_helper example.com 1000 3 &
wait
```

**Example: Sequential pings with controlled sequence numbers**
```bash
# Useful for scripted monitoring loops
for i in {1..10}; do
  ./bin/ping_helper example.com 1000 $i
  sleep 1
done
```

### Known Limitations

1. **Fixed packet size**: Uses 64-byte packets (cannot be configured)
2. **No payload customization**: Sends zero-filled payload
3. **No ICMP filtering on non-Linux**: `ICMP_FILTER` socket option is Linux-specific
4. **Process ID wrap**: Very long-running systems with rapid process creation might see PID recycling
5. **Process spawn overhead**: Each invocation creates a new process; not optimized for sub-millisecond intervals

## Security Considerations

### Privilege Separation

The helper is designed for **capability-based privilege separation**:

```bash
# Build and set capabilities (Linux)
make build
sudo make setcap

# Verify capabilities
getcap bin/ping_helper
# Output: bin/ping_helper = cap_net_raw+ep
```

**Never** grant `cap_net_raw` to Python interpreters or other general-purpose tools.

### Input Validation

All inputs are validated:
- Hostname: Resolved via `getaddrinfo()` with proper error handling
- `timeout_ms`: Range-checked (1-60000), validated as integer
- `icmp_seq`: Range-checked (0-65535), validated as integer

### Attack Surface

The helper:
- Does **not** parse user-controlled data from packets (beyond standard headers)
- Does **not** allocate based on packet contents
- Does **not** perform unbounded operations
- Implements **strict bounds checking** on all packet field access

## Future Extension Points

While the helper is intentionally minimal, potential future enhancements include:

1. **Configurable packet size**: Add optional argument for packet size
2. **Multiple requests**: Support sending multiple pings in one invocation (batch mode)
3. **IPv6 support**: Dual-stack ping capability
4. **Payload patterns**: Customizable payload for detecting corruption
5. **Statistics mode**: Send multiple pings and output aggregate stats
6. **Raw output mode**: Include full ICMP header details in output
7. **Persistent worker mode**: Accept multiple ping requests without process restart
8. **Shared socket pool**: Reuse raw sockets for multiple pings to reduce overhead

**Performance-oriented extensions:**
- **Batch mode example**: `./bin/ping_helper --batch hosts.txt` to ping multiple hosts in one process
- **Persistent worker**: Helper accepts commands via stdin for rapid-fire pings without spawn overhead
- **Output streaming**: JSON-lines format for programmatic consumption

**Note**: Any extensions must maintain backward compatibility with the current CLI contract.

## Troubleshooting

### Common Issues and Solutions

#### Exit Code 4: Socket Error / Insufficient Privileges

**Symptoms:**
```
Error: cannot create raw socket: Operation not permitted
Note: This program requires cap_net_raw capability or root privileges
```

**Solutions:**
1. Verify capabilities are set (Linux):
   ```bash
   getcap ./bin/ping_helper
   # Should show: ping_helper = cap_net_raw+ep
   ```

2. Re-set capabilities if missing:
   ```bash
   sudo make setcap
   ```

3. Verify the binary hasn't been moved or rebuilt (capabilities are per-inode)

4. On non-Linux systems, run with `sudo` or set setuid bit (not recommended)

#### Exit Code 7: Timeout (Not an Error)

**Symptoms:**
- No output on stdout
- Exit code 7

**Context:**
Exit code 7 is **not an error**; it indicates a normal timeout (no ICMP reply received within timeout_ms). This is expected behavior when:
- Target host is unreachable or firewalled
- Network is experiencing packet loss
- Timeout is too short for the network conditions

**Solutions:**
- Increase `timeout_ms` value if network RTT is high
- Verify target host is reachable: `ping <host>` (using system ping)
- Check firewall rules blocking ICMP

#### Exit Code 2: Argument Validation Error

**Symptoms:**
```
Error: timeout_ms must be positive
Error: icmp_seq must be between 0 and 65535
```

**Solutions:**
- Verify arguments are integers in valid ranges:
  - `timeout_ms`: 1-60000 milliseconds
  - `icmp_seq`: 0-65535 (optional, default: 1)
- Check for typos or invalid characters in arguments

#### Exit Code 3: Host Resolution Failed

**Symptoms:**
```
Error: cannot resolve host example.invalid: Name or service not known
```

**Solutions:**
- Verify hostname is correct and resolvable: `nslookup <host>`
- Check DNS configuration: `/etc/resolv.conf`
- Use IP address directly to bypass DNS

#### Unexpected Timeouts Under High Load

**Symptoms:**
- Frequent exit code 7 when monitoring many hosts concurrently
- Timeouts on hosts that normally respond quickly

**Possible Causes and Solutions:**
1. **Kernel ICMP rate limiting**:
   ```bash
   # Check current limits (Linux)
   sysctl net.ipv4.icmp_ratelimit
   # Increase limit if needed (requires root)
   sudo sysctl -w net.ipv4.icmp_ratelimit=100
   ```

2. **File descriptor limits**:
   ```bash
   ulimit -n  # Check current limit
   ulimit -n 4096  # Increase limit
   ```

3. **Socket buffer drops** (check system logs):
   ```bash
   # Increase system-wide socket buffer limits (Linux)
   sudo sysctl -w net.core.rmem_max=8388608
   ```

4. **Process spawn overhead**: Consider increasing ping intervals or reducing concurrent host count

## Implementation Details

### Socket Configuration

- **Type**: `SOCK_RAW` with `IPPROTO_ICMP`
- **Connected socket**: Calls `connect()` to filter packets to target host only
- **Receive buffer**: Increased to 256KB to reduce drops under high ICMP volume
- **ICMP filter** (Linux only): Filters to accept only ECHOREPLY packets

### Time Handling

- Uses `gettimeofday()` for microsecond-precision timestamps
- Calculates absolute deadline to avoid time-drift in select() loop
- Recalculates remaining time on each iteration

### Checksum Calculation

Implements standard RFC 1071 Internet checksum:
- 16-bit one's complement sum
- Handles odd-length data correctly

## Testing

The helper is tested via:

1. **Python wrapper tests** (`tests/test_ping_wrapper.py`): Integration tests via `ping_wrapper.py`
2. **Contract tests** (`tests/test_ping_helper_contract.py`): CLI contract verification
   - Output format parsing
   - Exit code behavior
   - Argument validation
   - Error message format

Run tests:
```bash
python3 -m pytest tests/test_ping_wrapper.py tests/test_ping_helper_contract.py -v
```

## References

- RFC 792: Internet Control Message Protocol
- RFC 1071: Computing the Internet Checksum
- `capabilities(7)`: Linux capabilities man page
- `icmp(7)`: Linux ICMP socket programming

---

## 日本語

# ping_helper ドキュメント

## 概要

`ping_helper` は C で書かれた最小限の capability ベースの ICMP ping ユーティリティです。単一の ICMP エコーリクエストを送信し、応答を待ち、成功時にラウンドトリップ時間（RTT）と TTL を出力するか、失敗時に特定のエラーコードで終了します。

## 設計哲学

ヘルパーは意図的に最小限に設計されており、アプリケーション全体に root 権限を要求するのではなく、`cap_net_raw` capability（Linux 上）で実行するように設計されています。各呼び出しは：
- 正確に **1 つの ICMP エコーリクエスト** を送信
- 一致する応答を待つか、タイムアウト
- 有効な応答を受信した後、またはタイムアウト/エラー時にすぐに終了

この設計は **ping ごとに 1 つのヘルパープロセス** に最適化されており、これは ParaPing の現在の使用パターンです。

## コマンドラインインターフェース

### 使用方法

```bash
ping_helper <host> <timeout_ms> [icmp_seq]
```

### 引数

- `<host>`（必須）：ping するホスト名または IPv4 アドレス
- `<timeout_ms>`（必須）：タイムアウト（ミリ秒、1-60000）
- `[icmp_seq]`（オプション）：ICMP シーケンス番号（0-65535、デフォルト: 1）

### 例

```bash
# 1 秒のタイムアウトで基本的な ping（デフォルト icmp_seq=1）
./bin/ping_helper google.com 1000

# カスタムシーケンス番号で ping
./bin/ping_helper 8.8.8.8 2000 42

# 最小タイムアウトで ping
./bin/ping_helper 1.1.1.1 100 1
```

## 出力形式

### 成功

ping が成功すると、ヘルパーは標準出力に以下を出力します：

```
rtt_ms=<value> ttl=<value>
```

ここで：
- `rtt_ms`: ラウンドトリップ時間（ミリ秒、浮動小数点、小数点以下 3 桁）
- `ttl`: 応答の IP ヘッダーからの Time-to-Live（整数）

**例:**
```
rtt_ms=12.345 ttl=64
```

### タイムアウト

タイムアウト（timeout_ms 内に応答が受信されない）の場合、ヘルパーは：
- 標準出力には何も出力しない
- コード **7** で終了

### エラー

エラー時、ヘルパーは：
- エラーメッセージを標準エラー出力に出力
- ゼロ以外、7 以外の終了コードで終了

## 終了コード

| コード | 意味 | 注記 |
|------|------|------|
| 0 | 成功 | 有効な応答を受信 |
| 1 | 無効な引数 | 引数の数が間違っている |
| 2 | 引数検証エラー | 無効な timeout_ms または icmp_seq |
| 3 | ホスト解決失敗 | ホスト名を解決できない |
| 4 | ソケットエラー | ソケットを作成できないか、権限が不足 |
| 5 | 送信エラー | ICMP パケットの送信に失敗 |
| 6 | Select エラー | 内部 select() の失敗 |
| 7 | **タイムアウト** | timeout_ms 内に応答なし |
| 8 | 受信エラー | パケットの受信に失敗 |

**終了コード 7 はタイムアウト専用に予約されており**、エラーではなく「応答なし」として扱う必要があります。

## パケット検証

ヘルパーは、誤った帰属を避け、破損したパケットを処理するために堅牢なパケット検証を実装しています：

### 応答一致基準

受信したパケットは、**すべて** の条件が満たされた場合のみ有効な応答と見なされます：

1. **最小パケットサイズ**: 少なくとも 20 バイト（最小 IP ヘッダー）
2. **IP ヘッダー検証**:
   - IP ヘッダー長が 20-60 バイトの間
   - IP バージョンが 4
   - IP プロトコルが ICMP (1)
3. **ICMP ヘッダー検証**:
   - パケットが IP ヘッダー + 8 バイト ICMP ヘッダーに十分な長さ
   - ICMP タイプが ECHOREPLY (0)
   - ICMP コードが 0
4. **識別子の一致**:
   - ICMP ID が `getpid() & 0xFFFF` と一致
   - ICMP シーケンス番号が送信したシーケンスと一致
   - 送信元 IP アドレスが送信先と一致

これらの基準の **いずれか** に一致しないパケットは静かに破棄され、ヘルパーはタイムアウトまで有効な応答を待ち続けます。

### エッジケースに対する防御

- **短いパケット**: フィールドにアクセスする前に検証
- **破損した IP ヘッダー**: ヘッダー長の境界チェック
- **間違ったプロトコル**: IP プロトコルフィールドの検証
- **他のプロセスの ping**: ID とシーケンス番号のフィルタリング
- **間違ったホストからの応答**: 送信元アドレスの検証

## 前提と制限事項

### 現在の設計上の前提

1. **プロセスごとに 1 リクエスト**: 各ヘルパーインスタンスは正確に 1 つの ICMP エコーリクエストを送信
2. **識別子としてのプロセス ID**: ICMP ID に `getpid() & 0xFFFF` を使用
   - PID がリサイクルされた複数のヘルパーが実行されると衝突の可能性
   - シーケンス番号の一致と送信元アドレスの検証で緩和
3. **IPv4 のみ**: IPv6 サポートなし
4. **単一ホスト**: 各呼び出しは正確に 1 つのホストをターゲット
5. **リトライなし**: パケットロス時にリトライせず、タイムアウトで終了

### 安全な使用制約

- **ping ごとに 1 ヘルパー**: 単一のヘルパープロセスを複数の ping に再利用しないでください
- **順次呼び出し**: 同じホストで複数のヘルパーを実行する場合、異なるシーケンス番号を確保するか、タイミングをずらして ID 衝突を避ける
- **capability ベースのセキュリティ（Linux）**: バイナリに `cap_net_raw` を使用し、インタプリタには **決して** 使用しない
- **プラットフォーム固有**: Linux 向けに最適化、macOS/BSD では異なる権限処理が必要な場合がある

### マルチプロセスとバッチシナリオ

複数の ping_helper プロセスを同時に実行する場合（例：多数のホストを監視）：

**推奨プラクティス:**
- **同じホスト** に同時に ping する場合は、応答の混乱を避けるために異なる `icmp_seq` 値を使用
- システム制限を監視: ファイルディスクリプタ制限（`ulimit -n`）と ICMP レート制限を確認
- 高頻度シナリオでのプロセス生成オーバーヘッド（呼び出しごとに約 1-5ms）を考慮

**例: 複数のホストを並列監視**
```bash
# 異なるホストは一意のシーケンス番号を必要としない（応答は送信元 IP で区別される）
./bin/ping_helper 8.8.8.8 1000 &
./bin/ping_helper 1.1.1.1 1000 &
./bin/ping_helper 9.9.9.9 1000 &
wait
```

**例: 同じホストへの同時 ping（異なるシーケンス番号を使用）**
```bash
# 同じホストに同時に ping する場合、混乱を避けるために異なる icmp_seq が必要
./bin/ping_helper example.com 1000 1 &
./bin/ping_helper example.com 1000 2 &
./bin/ping_helper example.com 1000 3 &
wait
```

**例: 制御されたシーケンス番号での順次 ping**
```bash
# スクリプト化された監視ループに便利
for i in {1..10}; do
  ./bin/ping_helper example.com 1000 $i
  sleep 1
done
```

### 既知の制限事項

1. **固定パケットサイズ**: 64 バイトパケットを使用（設定不可）
2. **ペイロードのカスタマイズなし**: ゼロ埋めペイロードを送信
3. **非 Linux での ICMP フィルタリングなし**: `ICMP_FILTER` ソケットオプションは Linux 固有
4. **プロセス ID ラップ**: 迅速なプロセス作成を伴う非常に長時間実行されるシステムでは PID のリサイクルが発生する可能性
5. **プロセス生成オーバーヘッド**: 各呼び出しで新しいプロセスを作成、サブミリ秒間隔には最適化されていない

## セキュリティ上の考慮事項

### 権限の分離

ヘルパーは **capability ベースの権限分離** 向けに設計されています：

```bash
# ビルドして capabilities を設定（Linux）
make build
sudo make setcap

# capabilities を確認
getcap bin/ping_helper
# 出力: bin/ping_helper = cap_net_raw+ep
```

Python インタプリタや他の汎用ツールに `cap_net_raw` を付与 **しないでください**。

### 入力検証

すべての入力が検証されます：
- ホスト名: 適切なエラー処理で `getaddrinfo()` を介して解決
- `timeout_ms`: 範囲チェック（1-60000）、整数として検証
- `icmp_seq`: 範囲チェック（0-65535）、整数として検証

### 攻撃面

ヘルパーは：
- パケットからのユーザー制御データを解析 **しない**（標準ヘッダーを超えて）
- パケットの内容に基づいて割り当て **しない**
- 無制限の操作を実行 **しない**
- すべてのパケットフィールドアクセスに **厳格な境界チェック** を実装

## 将来の拡張ポイント

ヘルパーは意図的に最小限ですが、潜在的な将来の拡張には以下が含まれます：

1. **設定可能なパケットサイズ**: パケットサイズのオプション引数を追加
2. **複数のリクエスト**: 1 回の呼び出しで複数の ping を送信（バッチモード）
3. **IPv6 サポート**: デュアルスタック ping 機能
4. **ペイロードパターン**: 破損検出用のカスタマイズ可能なペイロード
5. **統計モード**: 複数の ping を送信し、集計統計を出力
6. **生出力モード**: 出力に完全な ICMP ヘッダー詳細を含める
7. **永続ワーカーモード**: プロセスを再起動せずに複数の ping リクエストを受け入れる
8. **共有ソケットプール**: 複数の ping で生ソケットを再利用してオーバーヘッドを削減

**パフォーマンス指向の拡張:**
- **バッチモード例**: `./bin/ping_helper --batch hosts.txt` で複数のホストを 1 つのプロセスで ping
- **永続ワーカー**: 生成オーバーヘッドなしで迅速な ping 用に stdin を介してコマンドを受け入れる長寿命のヘルパープロセス
- **出力ストリーミング**: プログラム的な消費のための JSON-lines 形式

**注**: 現在の 1 プロセス per ping モデルは意図的なもので、典型的な監視ワークロード（1 秒間隔で 1-128 ホスト）に対して最適なセキュリティ/信頼性のトレードオフを提供します。異なるワークロードの場合は、上記の最適化を検討してください。

## トラブルシューティング

### 一般的な問題と解決策

#### 終了コード 4: ソケットエラー / 権限不足

**症状:**
```
Error: cannot create raw socket: Operation not permitted
Note: This program requires cap_net_raw capability or root privileges
```

**解決策:**
1. capabilities が設定されているか確認（Linux）:
   ```bash
   getcap ./bin/ping_helper
   # 次のように表示されるはず: ping_helper = cap_net_raw+ep
   ```

2. 不足している場合は capabilities を再設定:
   ```bash
   sudo make setcap
   ```

3. バイナリが移動または再ビルドされていないか確認（capabilities はアイノードごと）

4. 非 Linux システムでは、`sudo` で実行するか、setuid ビットを設定（推奨しません）

#### 終了コード 7: タイムアウト（エラーではない）

**症状:**
- 標準出力に出力なし
- 終了コード 7

**コンテキスト:**
終了コード 7 は **エラーではありません**。通常のタイムアウト（timeout_ms 内に ICMP 応答が受信されなかった）を示します。これは以下の場合に予想される動作です：
- ターゲットホストが到達不可能またはファイアウォールで保護されている
- ネットワークでパケットロスが発生している
- ネットワーク条件に対してタイムアウトが短すぎる

**解決策:**
- ネットワーク RTT が高い場合は `timeout_ms` 値を増やす
- ターゲットホストが到達可能か確認: `ping <host>`（システム ping を使用）
- ICMP をブロックするファイアウォールルールを確認

#### 終了コード 2: 引数検証エラー

**症状:**
```
Error: timeout_ms must be positive
Error: icmp_seq must be between 0 and 65535
```

**解決策:**
- 引数が有効な範囲の整数であることを確認:
  - `timeout_ms`: 1-60000 ミリ秒
  - `icmp_seq`: 0-65535（オプション、デフォルト: 1）
- 引数のタイプミスや無効な文字を確認

#### 終了コード 3: ホスト解決失敗

**症状:**
```
Error: cannot resolve host example.invalid: Name or service not known
```

**解決策:**
- ホスト名が正しく解決可能か確認: `nslookup <host>`
- DNS 設定を確認: `/etc/resolv.conf`
- DNS をバイパスして IP アドレスを直接使用

#### 高負荷下での予期しないタイムアウト

**症状:**
- 多数のホストを同時監視している際に頻繁に終了コード 7
- 通常は迅速に応答するホストでのタイムアウト

**考えられる原因と解決策:**
1. **カーネル ICMP レート制限**:
   ```bash
   # 現在の制限を確認（Linux）
   sysctl net.ipv4.icmp_ratelimit
   # 必要に応じて制限を増やす（root が必要）
   sudo sysctl -w net.ipv4.icmp_ratelimit=100
   ```

2. **ファイルディスクリプタ制限**:
   ```bash
   ulimit -n  # 現在の制限を確認
   ulimit -n 4096  # 制限を増やす
   ```

3. **ソケットバッファドロップ**（システムログを確認）:
   ```bash
   # システム全体のソケットバッファ制限を増やす（Linux）
   sudo sysctl -w net.core.rmem_max=8388608
   ```

4. **プロセス生成オーバーヘッド**: ping 間隔を増やすか、同時ホスト数を減らすことを検討

## 実装の詳細

### ソケット設定

- **タイプ**: `IPPROTO_ICMP` を使用した `SOCK_RAW`
- **接続済みソケット**: `connect()` を呼び出してターゲットホストのみにパケットをフィルタリング
- **受信バッファ**: 高 ICMP ボリューム下でのドロップを削減するために 256KB に増加
- **ICMP フィルタ**（Linux のみ）: ECHOREPLY パケットのみを受け入れるようにフィルタリング

### 時間処理

- マイクロ秒精度のタイムスタンプに `gettimeofday()` を使用
- select() ループでの時間ドリフトを避けるために絶対期限を計算
- 各イテレーションで残り時間を再計算

### チェックサム計算

標準 RFC 1071 インターネットチェックサムを実装：
- 16 ビット 1 の補数和
- 奇数長データを正しく処理

## テスト

ヘルパーは以下を介してテストされます：

1. **Python ラッパーテスト**（`tests/test_ping_wrapper.py`）：`ping_wrapper.py` を介した統合テスト
2. **コントラクトテスト**（`tests/test_ping_helper_contract.py`）：CLI コントラクトの検証
   - 出力形式の解析
   - 終了コードの動作
   - 引数の検証
   - エラーメッセージの形式

テストを実行：
```bash
python3 -m pytest tests/test_ping_wrapper.py tests/test_ping_helper_contract.py -v
```

## 参考文献

- RFC 792: Internet Control Message Protocol
- RFC 1071: Computing the Internet Checksum
- `capabilities(7)`: Linux capabilities man ページ
- `icmp(7)`: Linux ICMP ソケットプログラミング
