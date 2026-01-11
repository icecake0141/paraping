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

MultiPing は、複数ホストへの ICMP ping を並列に実行し、タイムライン/スパークラインとして表示する対話型ターミナルツールです。ソート・フィルタ・一時停止・スナップショット・ASN/rDNS 表示など、運用向けの操作機能を備えています。

> English README: [README.md](README.md)

## 特長
- 複数ホストへの同時 ICMP ping（Scapy ベース）。
- 成功/遅延/失敗を可視化するタイムライン/スパークライン表示。
- ホスト統計と合計値を示すサマリーパネル。
- 失敗回数・連続失敗・遅延・ホスト名でのソート/フィルタ。
- 表示名の切替（IP / rDNS / エイリアス）。
- ASN 表示（Team Cymru から取得、失敗時は再試行）。
- 表示のみ停止、または ping も停止する一時停止モード。
- タイムスタンプ付きテキストスナップショットの保存。
- 表示時刻・スナップショット時刻のタイムゾーン指定。
- 入力ファイルからのホスト読み込み（1 行 1 ホスト、コメント可）。

## 必要条件
- Python 3.9 以上。
- `scapy`（`requirements.txt` を参照）。
- ICMP を送信するための管理者権限。
- ASN 取得用のネットワーク接続（任意機能）。

## インストール
```bash
git clone https://github.com/icecake0141/multiping.git
cd multiping
python -m pip install -r requirements.txt
```

## 使い方
```bash
python main.py [options] <host1> <host2> ...
```

例（ホスト一覧ファイルと 2 秒タイムアウト）:
```bash
python main.py -t 2 -f hosts.txt
```

### コマンドラインオプション
- `-t`, `--timeout`: 1 回の ping のタイムアウト（秒）。
- `-c`, `--count`: 各ホストの試行回数。
- `--slow-threshold`: 遅延判定の閾値（秒）。
- `-v`, `--verbose`: 詳細ログ出力（UI なし）。
- `-f`, `--input`: ホスト一覧ファイル（1 行 1 ホスト、`#` はコメント）。
- `--panel-position`: サマリーパネルの位置（`right|left|top|bottom|none`）。
- `--pause-mode`: 一時停止の挙動（`display|ping`）。
- `--timezone`: 表示時刻のタイムゾーン（IANA 名）。
- `--snapshot-timezone`: スナップショット時刻のタイムゾーン（`utc|display`）。

### 対話操作
- `n`: 表示名モード切替（ip/rdns/alias）。
- `v`: 表示切替（timeline/sparkline）。
- `o`: ソート切替（failures/streak/latency/host）。
- `f`: フィルタ切替（failures/latency/all）。
- `a`: ASN 表示の切替（スペース不足時は自動的に非表示）。
- `p`: 一時停止/再開（表示のみ or ping + 表示）。
- `s`: `multiping_snapshot_YYYYMMDD_HHMMSS.txt` を保存。
- `H`: ヘルプ表示（任意キーで閉じる）。
- `q`: 終了。

### 記号の意味
- `.` 成功
- `!` 遅延（RTT >= `--slow-threshold`）
- `x` 失敗/タイムアウト

## 補足
- ICMP を送信するため、`sudo` など管理者権限で実行してください。
- ASN 取得は `whois.cymru.com` を使用します。アクセス不可の場合は空欄になります。

## ライセンス
Apache License 2.0。詳細は [LICENSE](LICENSE) を参照してください。
