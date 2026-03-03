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

## English

# ParaPing Specification

## Scope

ParaPing is an interactive terminal ICMP monitor for multi-host operational triage.
It continuously pings multiple hosts in parallel and visualizes network state in real time.

## Core Capabilities

- Concurrent ping for multiple hosts
- Live timeline / sparkline visualization
- Sorting and filtering by latency/failure conditions
- Pause modes and snapshot export
- Per-host detail inspection (RTT and related stats)

## Runtime Requirements

- Python 3.9+
- Linux: `ping_helper` binary with `cap_net_raw` (recommended)
- macOS/BSD: run with `sudo` when raw ICMP is required
- Optional network access for ASN lookup

## Privileged ICMP Model (Linux)

- Raw-socket privilege is isolated to `ping_helper`
- Main Python process runs without elevated privileges
- Do not grant capabilities to generic interpreters (for example `/usr/bin/python3`)

See also: [Ping Helper Detail](ping_helper.md)

## Scheduling and Display Behavior

- Time-driven scheduler aligns timeline columns by wall-clock time
- Pending markers can be shown before responses arrive
- Display drift is minimized during latency fluctuation

## Safety Controls

- Global rate-limit protection
- Per-host outstanding-ping window limits

## Platform Notes

- IPv4 is the primary supported path
- Capability setup (`setcap`) is Linux-specific

## Related Documents

- [README](../README.md)
- [Usage Guide](usage.md)
- [Testing Guide](testing.md)
- [Docs Index](index.md)

---

## 日本語

# ParaPing 仕様

## スコープ

ParaPing は、複数ホストの運用トリアージ向けに設計された、インタラクティブなターミナル ICMP モニターです。
複数ホストへ並列に ping を継続実行し、ネットワーク状態をリアルタイムに可視化します。

## 主要機能

- 複数ホストへの並列 ping
- タイムライン / スパークラインによるライブ表示
- レイテンシ / 失敗条件でのソートとフィルタ
- 一時停止モードとスナップショット出力
- ホスト単位の詳細確認（RTT など）

## 実行要件

- Python 3.9+
- Linux: `cap_net_raw` を付与した `ping_helper`（推奨）
- macOS/BSD: raw ICMP が必要な場合は `sudo` で実行
- ASN 取得にはネットワーク接続が必要（任意）

## 特権 ICMP モデル（Linux）

- raw socket 権限は `ping_helper` に限定
- メインの Python プロセスは昇格なしで実行
- `/usr/bin/python3` のような汎用インタプリタに capability を付与しない

関連: [Ping Helper 詳細](ping_helper.md)

## スケジューリングと表示

- 時間駆動スケジューラでタイムライン列を壁時計ベースで整列
- 応答前の pending 表示に対応
- レイテンシ変動時の表示ドリフトを抑制

## 安全制御

- 全体レート制限
- ホスト単位の未応答 ping 上限制御

## プラットフォーム注意

- 主要サポートは IPv4
- `setcap` は Linux 専用

## 関連ドキュメント

- [README](../README.md)
- [使い方ガイド](usage.md)
- [テストガイド](testing.md)
- [ドキュメント一覧](index.md)
