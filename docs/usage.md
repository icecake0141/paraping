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

## English

# Usage Guide

## Basic Commands

```bash
# show help
make run ARGS='--help'

# monitor two hosts
make run ARGS='8.8.8.8 1.1.1.1'

# load hosts from file
make run ARGS='-f hosts.txt'
```

## Input File Format

- Basic: `IP,alias`
- Extended: `IP,alias,site,tags`
- `tags` must be separated by `;`
- Lines starting with `#` are ignored

## Important CLI Options

- `-t, --timeout`: timeout seconds per ping
- `-i, --interval`: seconds between pings per host (`0.1` to `60.0`)
- `-c, --count`: ping count per host (`0` for infinite)
- `-s, --slow-threshold`: threshold for slow marker
- `-f, --input`: host input file
- `--group-by`: `none|asn|site|tag|site>tag1`
- `-P, --panel-position`: `right|left|top|bottom|none`
- `-m, --pause-mode`: `display|ping`
- `-z, --timezone`: display timezone
- `-Z, --snapshot-timezone`: snapshot filename timezone (`utc|display`)
- `-C, --color`: enable color output
- `-F, --flash-on-fail`: flash on failures
- `-B, --bell-on-fail`: bell on failures
- `-H, --ping-helper`: helper binary path
- `--no-config`: skip `~/.paraping.conf`

## Interactive Keys

- `q`: quit
- `H` / `h`: help overlay
- `n`: display name mode cycle
- `v`: timeline/sparkline toggle
- `o`: sort mode cycle
- `f`: filter mode cycle
- `p`: display pause toggle
- `P`: dormant mode toggle (ping + display pause)
- `s`: save snapshot file
- `g`: open host selector for fullscreen graph
- `ESC`: exit graph/selector
- `R`: reload hosts from `-f/--input`
- `arrow_left` / `arrow_right`: history page navigation
- `arrow_up` / `arrow_down`: host list scrolling

## Related Documents

- [Specification](specification.md)
- [Testing Guide](testing.md)
- [Ping Helper](ping_helper.md)
- [Scheduler API](api/scheduler.md)

---

## 日本語

# 使い方ガイド

## 基本コマンド

```bash
# ヘルプ表示
make run ARGS='--help'

# 2ホストを監視
make run ARGS='8.8.8.8 1.1.1.1'

# ファイルからホスト読み込み
make run ARGS='-f hosts.txt'
```

## 入力ファイル形式

- 基本形式: `IP,alias`
- 拡張形式: `IP,alias,site,tags`
- `tags` は `;` 区切り
- `#` で始まる行はコメントとして無視

## 主要 CLI オプション

- `-t, --timeout`: ping ごとのタイムアウト秒
- `-i, --interval`: ホストごとの送信間隔秒（`0.1`〜`60.0`）
- `-c, --count`: ホストごとの送信回数（`0` は無限）
- `-s, --slow-threshold`: 遅延判定しきい値
- `-f, --input`: ホスト入力ファイル
- `--group-by`: `none|asn|site|tag|site>tag1`
- `-P, --panel-position`: `right|left|top|bottom|none`
- `-m, --pause-mode`: `display|ping`
- `-z, --timezone`: 画面表示タイムゾーン
- `-Z, --snapshot-timezone`: スナップショット名タイムゾーン（`utc|display`）
- `-C, --color`: 色表示を有効化
- `-F, --flash-on-fail`: 失敗時フラッシュ
- `-B, --bell-on-fail`: 失敗時ベル
- `-H, --ping-helper`: ヘルパーバイナリパス
- `--no-config`: `~/.paraping.conf` を読み込まない

## インタラクティブキー

- `q`: 終了
- `H` / `h`: ヘルプ表示
- `n`: 表示名モード切替
- `v`: timeline/sparkline 切替
- `o`: ソート切替
- `f`: フィルタ切替
- `p`: 表示更新のみ一時停止
- `P`: Dormant モード（ping + 表示更新停止）
- `s`: スナップショット保存
- `g`: フルスクリーングラフ用ホスト選択を開く
- `ESC`: グラフ/選択を終了
- `R`: `-f/--input` からホスト一覧を再読込
- `arrow_left` / `arrow_right`: 履歴ページ移動
- `arrow_up` / `arrow_down`: ホスト一覧スクロール

## 関連ドキュメント

- [仕様](specification.md)
- [テストガイド](testing.md)
- [Ping Helper](ping_helper.md)
- [Scheduler API](api/scheduler.md)
