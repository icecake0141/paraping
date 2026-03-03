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

## Overview

ParaPing は、複数ホストに対する ICMP ping を並列実行し、ターミナル上でリアルタイム表示する監視ツールです。

- ライブ表示（タイムライン / スパークライン）
- ソート・フィルタ・一時停止などの対話操作
- Linux では `ping_helper` + `cap_net_raw` による最小権限運用

詳細な仕様、使い方、テスト手順は `docs/` に分離しています。

## Installation

### Quick Start

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

## ドキュメント / Documentation

- [仕様 / Specification](docs/specification.md)
- [テスト / Testing](docs/testing.md)
- [ドキュメント一覧 / Docs Index](docs/index.md)
- [コントリビュート / Contributing](CONTRIBUTING.md)

## ライセンス / License

[Apache License 2.0](LICENSE)
