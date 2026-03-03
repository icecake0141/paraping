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

# ParaPing API Documentation

## English

This directory will contain comprehensive API documentation for ParaPing's Python modules and C helper components.

## Module Layout

ParaPing is organized into the following modules:

### Core Modules

#### `main.py`
Main application entry point and orchestration logic.
- **Purpose**: Application initialization, command-line parsing, main event loop
- **Key Functions**: (documentation coming soon)

#### `scheduler.py`
Time-driven ping scheduler that eliminates timeline drift.
- **Purpose**: Compute precise next-ping timestamps for each host using configurable interval and stagger
- **Documentation**: See [scheduler.md](scheduler.md) for the full API reference and examples

#### `ping_wrapper.py`
Python wrapper for the privileged ICMP helper binary.
- **Purpose**: Interface between Python application and `ping_helper` C binary
- **Key Functions**:
  - Process spawning and management
  - JSON parsing of helper output
  - Error handling and timeout management
- **Documentation**: See [../ping_helper.md](../ping_helper.md) for the C helper contract

### Display & UI Modules

#### `ui_render.py`
Terminal UI rendering and display formatting.
- **Purpose**: Screen rendering, layout management, display formatting
- **Key Functions**: (documentation coming soon)

#### `input_keys.py`
Keyboard input handling and interactive controls.
- **Purpose**: Key event processing, command dispatch
- **Key Functions**: (documentation coming soon)

### Network Modules

#### `network_rdns.py`
Reverse DNS lookup functionality.
- **Purpose**: Resolve IP addresses to hostnames
- **Key Functions**: (documentation coming soon)

#### `network_asn.py`
Autonomous System Number (ASN) lookup.
- **Purpose**: Query ASN information from Team Cymru's whois service
- **Key Functions**: (documentation coming soon)

### Statistics & History

#### `stats.py`
Statistical calculations and metrics.
- **Purpose**: RTT statistics, jitter, success rates
- **Key Functions**: (documentation coming soon)

#### `history.py`
Historical data management and navigation.
- **Purpose**: Time-series data storage, history navigation
- **Key Functions**: (documentation coming soon)

## C Helper Binary

### `ping_helper.c`
Privileged ICMP ping helper binary.
- **Purpose**: Execute ICMP echo requests with minimal privileges
- **Security Model**: Capability-based access control (`cap_net_raw`)
- **Documentation**: See [../ping_helper.md](../ping_helper.md)

## Module Dependencies

```
main.py
├── ping_wrapper.py (ping_helper.c)
├── ui_render.py
├── input_keys.py
├── network_rdns.py
├── network_asn.py
├── stats.py
└── history.py
```

## Development Status

This API documentation is a work in progress. Detailed function-level documentation will be added incrementally as the codebase evolves.

For now, please refer to:
- [Modularization Guide](../MODULARIZATION.md) for module boundaries and ownership
- Source code docstrings for function-specific documentation

## Contributing to Documentation

When adding new modules or functions:
1. Update this index with the module's purpose
2. Add docstrings to all public functions
3. Document key data structures and algorithms
4. Note any security considerations
5. Include usage examples where appropriate

For documentation standards, see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Future Work

Planned documentation enhancements:
- [ ] Detailed function-level API reference
- [ ] Data structure documentation (buffers, state objects)
- [ ] Sequence diagrams for key workflows
- [ ] Performance characteristics and scalability notes
- [ ] Platform-specific implementation details
- [ ] Integration guide for embedding ParaPing

## 日本語

# ParaPing API ドキュメント

このディレクトリには、ParaPing の Python モジュールと C ヘルパーの API ドキュメントを配置します。

## モジュール構成

ParaPing は以下のモジュールで構成されています。

### コアモジュール

#### `main.py`
アプリケーションのエントリポイントと全体オーケストレーション。
- **目的**: 初期化、CLI 解析、メインイベントループ

#### `scheduler.py`
タイムラインのドリフトを防ぐ時間駆動スケジューラ。
- **目的**: interval/stagger を使ってホストごとの次回 ping 時刻を計算
- **詳細**: [scheduler.md](scheduler.md)

#### `ping_wrapper.py`
特権 ICMP ヘルパーバイナリの Python ラッパー。
- **目的**: `ping_helper` との連携、結果解析、エラー処理
- **関連**: [../ping_helper.md](../ping_helper.md)

### 表示/UI モジュール

#### `ui_render.py`
ターミナル UI の描画と整形。

#### `input_keys.py`
キーボード入力処理とインタラクティブ操作。

### ネットワークモジュール

#### `network_rdns.py`
逆引き DNS 解決。

#### `network_asn.py`
Team Cymru whois を用いた ASN 取得。

### 統計・履歴

#### `stats.py`
RTT、ジッタ、成功率などの統計計算。

#### `history.py`
履歴データの保存とナビゲーション。

## C ヘルパーバイナリ

### `ping_helper.c`
最小権限で ICMP echo を実行する補助バイナリ。
- **セキュリティモデル**: capability ベース（`cap_net_raw`）
- **詳細**: [../ping_helper.md](../ping_helper.md)

## 依存関係

```
main.py
├── ping_wrapper.py (ping_helper.c)
├── ui_render.py
├── input_keys.py
├── network_rdns.py
├── network_asn.py
├── stats.py
└── history.py
```

## 開発状況

本 API ドキュメントは継続整備中です。現時点では以下を参照してください。
- [../MODULARIZATION.md](../MODULARIZATION.md)
- 各ソースコードの docstring

## ドキュメントへの貢献

新しいモジュールや関数を追加する際は、次を更新してください。
1. 本 index への目的追記
2. 公開関数への docstring 追加
3. 重要データ構造・アルゴリズムの説明
4. セキュリティ考慮事項の明記
5. 利用例の追加

規約は [../CONTRIBUTING.md](../CONTRIBUTING.md) を参照してください。
