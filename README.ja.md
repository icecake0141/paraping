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
- 複数ホストへの同時 ICMP ping（capability 付き helper バイナリ）。
- 成功/遅延/失敗を可視化するタイムライン/スパークライン表示。
- ping 実行中に動作インジケータ（ナイトライダー風の左右移動）。
- ホスト統計、合計値、TTL 表示を含むサマリーパネル。
- 失敗回数・連続失敗・遅延・ホスト名でのソート/フィルタ。
- 表示名の切替（IP / rDNS / エイリアス）。
- ASN 表示（Team Cymru から取得、失敗時は再試行）。
- 成功/遅延/失敗に応じたカラー表示（任意）。
- 表示のみ停止、または ping も停止する一時停止モード。
- タイムスタンプ付きテキストスナップショットの保存。
- 表示時刻・スナップショット時刻のタイムゾーン指定。
- 入力ファイルからのホスト読み込み（1 行 1 ホスト、コメント可）。

## 必要条件
- Python 3.9 以上。
- `ping_helper` バイナリを `cap_net_raw` 付きでビルド（Linux 環境で sudo 不要）。
- helper が使えない場合は ICMP を送信するための管理者権限。
- ASN 取得用のネットワーク接続（任意機能）。

### Linux 専用: 特権 ICMP ヘルパー（任意）

Linux では、Python を root で実行する代わりに、ケーパビリティベースの特権を持つ `ping_helper` バイナリを使用できます。これにより、生のソケットアクセスを単一の小さなバイナリに限定できるため、より安全です。

**依存関係:**
- `gcc`（ヘルパーのビルド用）
- `libcap2-bin`（`setcap` でケーパビリティを設定するため）

Debian/Ubuntu での依存関係のインストール:
```bash
sudo apt-get install gcc libcap2-bin
```

**ヘルパーのビルドと設定:**
```bash
# ヘルパーバイナリをビルド
make build

# ケーパビリティを設定（sudo が必要）
sudo make setcap

# ヘルパーをテスト
python3 ping_wrapper.py google.com
```

`ping_wrapper.py` が失敗した場合、JSON 出力の `error` フィールドに `ping_helper` の詳細 (stderr を含む場合あり) が入ります。トラブルシュートに利用してください。

**macOS/BSD ユーザーへの注意:** `setcap` コマンドは Linux 専用であり、macOS や BSD システムでは利用できません。これらのプラットフォームでは、代わりに setuid ビットを使用する必要があります（例: `sudo chown root:wheel ping_helper && sudo chmod u+s ping_helper`）が、セキュリティ上の理由から推奨されません。これらのプラットフォームでは、メインの Python スクリプトを `sudo` で実行する方が良いでしょう。

**セキュリティ注意:** `/usr/bin/python3` や他の汎用インタプリタに `cap_net_raw` やその他のケーパビリティを付与しないでください。特定の `ping_helper` バイナリにのみ、必要最小限の特権を付与してください。

## インストール
```bash
git clone https://github.com/icecake0141/multiping.git
cd multiping
python -m pip install -r requirements.txt

# 任意: 特権 ICMP ヘルパーをビルド（Linux のみ）
make build
sudo make setcap
```

## 使い方

![MultiPing デモ](docs/images/usage-demo.gif)

```bash
python main.py [options] <host1> <host2> ...
```

例（ホスト一覧ファイルと 2 秒タイムアウト）:
```bash
python main.py -t 2 -f hosts.txt
```

### コマンドラインオプション
- `-t`, `--timeout`: 1 回の ping のタイムアウト（秒、デフォルト: 1）。
- `-c`, `--count`: 各ホストの試行回数（デフォルト: 0 で無限）。
- `-i`, `--interval`: ホストごとの ping 間隔（秒、デフォルト: 1.0、範囲: 0.1-60.0）。
- `--slow-threshold`: 遅延判定の閾値（秒、デフォルト: 0.5）。
- `-v`, `--verbose`: 詳細ログ出力（UI なし）。
- `-f`, `--input`: ホスト一覧ファイル（1 行 1 ホスト、`#` はコメント）。
- `--panel-position`: サマリーパネルの位置（`right|left|top|bottom|none`）。
- `--pause-mode`: 一時停止の挙動（`display|ping`）。
- `--timezone`: 表示時刻のタイムゾーン（IANA 名）。
- `--snapshot-timezone`: スナップショット時刻のタイムゾーン（`utc|display`）。
- `--flash-on-fail`: ping に失敗したときに画面をフラッシュ（色反転）して注意を惹く。
- `--bell-on-fail`: ping に失敗したときにターミナルベルを鳴らして注意を惹く。
- `--color`: カラー表示を有効化（成功=青、遅延=黄、失敗=赤）。
- `--ping-helper`: `ping_helper` バイナリのパス（デフォルト: `./ping_helper`）。

### 対話操作
- `n`: 表示名モード切替（ip/rdns/alias）。
- `v`: 表示切替（timeline/sparkline）。
- `o`: ソート切替（failures/streak/latency/host）。
- `f`: フィルタ切替（failures/latency/all）。
- `a`: ASN 表示の切替（スペース不足時は自動的に非表示）。
- `m`: サマリー表示内容の切替（成功率/平均 RTT/TTL/連続回数）。
- `w`: サマリーパネルの表示切替。
- `p`: 一時停止/再開（表示のみ or ping + 表示）。
- `s`: `multiping_snapshot_YYYYMMDD_HHMMSS.txt` を保存。
- `←` / `→`: 時間を遡る/進める（最大30分前まで監視履歴を表示可能）。
- `H`: ヘルプ表示（任意キーで閉じる）。
- `q`: 終了。

### 記号の意味
- `.` 成功
- `!` 遅延（RTT >= `--slow-threshold`）
- `x` 失敗/タイムアウト
- `--color` 有効時: 成功=青、遅延=黄、失敗=赤

## 補足
- helper を使えない環境では ICMP を送信するため、`sudo` など管理者権限で実行してください。
- ASN 取得は `whois.cymru.com` を使用します。アクセス不可の場合は空欄になります。
- サマリーパネルを上/下に配置した場合、余白行を利用して表示行数を広げます。

## ライセンス
Apache License 2.0。詳細は [LICENSE](LICENSE) を参照してください。
