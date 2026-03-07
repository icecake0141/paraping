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
- `?`: help overlay toggle
- `d`: display name mode cycle
- `v`: timeline/sparkline/square view cycle
- `x`: open host selector for fullscreen graph
- `h` / `l` (`arrow_left` / `arrow_right`): history page navigation
- `j` / `k` (`arrow_down` / `arrow_up`): host list scrolling
- `r`: reload hosts from `-f/--input`
- `u`: force full redraw
- `o`: sort mode cycle
- `f`: filter mode cycle
- `a`: ASN display toggle
- `i`: summary info cycle
- `g`: summary scope cycle (host/group)
- `t`: group key cycle
- `w`: summary panel toggle
- `e`: summary panel position cycle
- `z`: summary fullscreen view toggle
- `c`: color output toggle
- `b`: bell-on-fail toggle
- `p`: display pause toggle
- `P`: dormant mode toggle (ping + display pause)
- `y`: Knight Rider mode toggle
- `Y`: Knight Rider style cycle (scanner/gradient)
- `s`: save snapshot file
- `ESC`: exit graph/selector

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
- `?`: ヘルプ表示切替
- `d`: 表示名モード切替
- `v`: timeline/sparkline/square 切替
- `x`: フルスクリーングラフ用ホスト選択を開く
- `h` / `l`（`arrow_left` / `arrow_right`）: 履歴ページ移動
- `j` / `k`（`arrow_down` / `arrow_up`）: ホスト一覧スクロール
- `r`: `-f/--input` からホスト一覧を再読込
- `u`: 強制フル再描画
- `o`: ソート切替
- `f`: フィルタ切替
- `a`: ASN 表示切替
- `i`: サマリー情報切替
- `g`: サマリースコープ切替（host/group）
- `t`: グループキー切替
- `w`: サマリーパネル表示切替
- `e`: サマリーパネル位置切替
- `z`: サマリーフルスクリーン切替
- `c`: 色表示切替
- `b`: 失敗時ベル切替
- `p`: 表示更新のみ一時停止
- `P`: Dormant モード（ping + 表示更新停止）
- `y`: Knight Rider モード切替
- `Y`: Knight Rider スタイル切替（scanner/gradient）
- `s`: スナップショット保存
- `ESC`: グラフ/選択を終了

## 関連ドキュメント

- [仕様](specification.md)
- [テストガイド](testing.md)
- [Ping Helper](ping_helper.md)
- [Scheduler API](api/scheduler.md)
