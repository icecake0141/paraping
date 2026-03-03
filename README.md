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

# ParaPing

[![CI/CD Pipeline](https://github.com/icecake0141/paraping/actions/workflows/ci.yml/badge.svg)](https://github.com/icecake0141/paraping/actions/workflows/ci.yml)
[![PR Checks](https://github.com/icecake0141/paraping/actions/workflows/pr-checks.yml/badge.svg)](https://github.com/icecake0141/paraping/actions/workflows/pr-checks.yml)

## English

### Overview

ParaPing is an interactive terminal monitor that runs ICMP ping in parallel for multiple hosts and displays results in real time.

- Live display (timeline / sparkline)
- Interactive controls such as sorting, filtering, and pause
- On Linux, minimal-privilege operation via `ping_helper` + `cap_net_raw`

Detailed specifications, usage guides, and testing procedures are separated under `docs/`.

### Installation

#### Quick Start

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# Create local .venv and set up required components
make

# Linux only: set capability on ICMP helper
sudo make setcap

# Show help
make run ARGS='--help'
# On macOS/BSD, run with sudo
# sudo make run ARGS='--help'
```

### Documentation

- [Specification](docs/specification.md)
- [Testing](docs/testing.md)
- [Docs Index](docs/index.md)
- [Contributing](CONTRIBUTING.md)

### License

[Apache License 2.0](LICENSE)

---

## 日本語

### 概要

ParaPing は、複数ホストに対する ICMP ping を並列実行し、ターミナル上でリアルタイム表示する監視ツールです。

- ライブ表示（タイムライン / スパークライン）
- ソート・フィルタ・一時停止などの対話操作
- Linux では `ping_helper` + `cap_net_raw` による最小権限運用

詳細な仕様、使い方、テスト手順は `docs/` に分離しています。

### インストール

#### クイックスタート

```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping

# local .venv を作成し、必要コンポーネントをセットアップ
make

# Linux のみ: ICMP helper に capability を付与
sudo make setcap

# ヘルプ表示
make run ARGS='--help'
# macOS/BSD の場合は sudo 付きで実行
# sudo make run ARGS='--help'
```

### ドキュメント

- [仕様 / Specification](docs/specification.md)
- [テスト / Testing](docs/testing.md)
- [ドキュメント一覧 / Docs Index](docs/index.md)
- [コントリビュート / Contributing](CONTRIBUTING.md)

### ライセンス

[Apache License 2.0](LICENSE)
