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

# ParaPing — 日本語ドキュメント

ParaPing は、複数のホストへ並列に ICMP ping を実行し、ライブのタイムラインまたはスパークラインとして結果を可視化する対話型のターミナルツールです。ソート、フィルタ、一時停止、スナップショット、ホストごとの RTT のフルスクリーングラフなどの操作が可能で、ネットワークのトラブルシュートに便利な情報を提供します。

## 機能
- 複数ホストへの並列 ICMP ping（capability ベースの補助バイナリを利用）
- 成功 / 遅延 / 失敗を示すライブのタイムライン / スパークライン表示
- 動的なアクティビティインジケータ（Knight Rider スタイル）
- ホスト別統計（RTT、ジッタ、標準偏差、集計カウント、TTL など）を表示するサマリーパネル
- 結果、サマリー、ステータス行をボックス化して表示
- 現在のソート順に合わせたサマリーホストの並び替え
- 失敗数・連続失敗・レイテンシ・ホスト名でのソートおよびフィルタリング
- 表示名モード切替：IP / 逆引き（rDNS）/ エイリアス
- 任意で ASN 表示（Team Cymru による取得、リトライ機能付き）
- 成功 / 遅延 / 失敗に応じた色分け（オプション）
- 表示のみ停止または ping も停止する一時停止モード
- タイムスタンプ付きスナップショットのテキスト出力
- ホストごとのフルスクリーン ASCII RTT グラフ（軸ラベル、スケール、X 軸に「何秒前」ラベル）
- タイムゾーン設定（画面表示・スナップショット名に利用可能）
- 入力ファイル対応（1 行に `IP,alias`、`#` 行はコメントとして無視）

## 要件
- Python 3.9 以上
- Linux では `cap_net_raw` を付与した `ping_helper` バイナリを使うことで通常ユーザ権限で実行可能
- 補助バイナリを使えない環境では管理者権限（sudo / Administrator）が必要
- ASN 取得を行う場合はネットワーク接続が必要（whois.cymru.com を使用）
- IPv4 のみサポート（ホストは IPv4 に解決される必要あり）

### Linux 特有: 権限を限定する ICMP ヘルパー（推奨）
Linux では Python を root で動かす代わりに、小さな専用バイナリ（`ping_helper`）だけに必要な権限を与えるやり方を推奨します。これにより権限を最小化できます。ヘルパーは生ソケットを用い、ICMP フィルタを適用してパケットのファンアウトを抑えるため、多数ホストの同時監視で安定性が高まります。

依存パッケージ（Debian/Ubuntu の例）:
```bash
sudo apt-get install gcc libcap2-bin
```

ビルドと設定手順:
```bash
# ヘルパーをビルド
make build

# ヘルパーに必要な capability を付与（sudo が必要）
sudo make setcap

# 動作確認（例）
python3 ping_wrapper.py google.com
```

ヘルパーの CLI（引数）:
```bash
ping_helper <host> <timeout_ms> [icmp_seq]
```
- `<host>`: ホスト名または IPv4 アドレス（必須）
- `<timeout_ms>`: タイムアウト（ミリ秒、1〜60000、必須）
- `[icmp_seq]`: ICMP シーケンス番号（オプション、0〜65535、デフォルト 1）

出力と終了コードの概略:
- 成功（exit 0）: stdout に `rtt_ms=<value> ttl=<value>`
- タイムアウト（exit 7）: 出力なし（正常なタイムアウト）
- エラー（exit 1–6, 8）: stderr にエラーメッセージ（引数エラー、解決失敗、ソケット/送受信エラー等）

macOS / BSD の注意:
- `setcap` は Linux 固有です。macOS / BSD では setuid による手段がありますが、セキュリティ上の理由で推奨しません。各プラットフォームのベストプラクティスに従って最小権限化してください。

セキュリティ注意:
- 汎用インタプリタ（例: `/usr/bin/python3`）へ `cap_net_raw` 等の権限を与えないでください。特定の小さなヘルパーバイナリのみに権限を付与してください。

## インストール
```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping
python -m pip install -r requirements.txt

# Linux の場合（オプション）: ヘルパーをビルドして権限を付与
make build
sudo make setcap
```

## 使い方

![ParaPing デモ](docs/images/usage-demo.gif)

```bash
./paraping [options] <host1> <host2> ...
```

例（ホスト一覧ファイルを使用しタイムアウト 2 秒）:
```bash
./paraping -t 2 -f hosts.txt
```

例（IPv4 を直接指定）:
```bash
./paraping 1.1.1.1 8.8.8.8
```

### コマンドラインオプション（主なもの）
- `-t, --timeout`: 各 ping のタイムアウト（秒、デフォルト 1）
- `-c, --count`: 各ホストの ping 回数（デフォルト 0 = 無限）
- `-i, --interval`: ping 間隔（秒、デフォルト 1.0、範囲 0.1–60.0）
- `-s, --slow-threshold`: 遅延判定の RTT 閾値（秒、デフォルト 0.5）
- `-v, --verbose`: 生パケット出力（非 UI）
- `-f, --input`: ホスト一覧ファイル（1 行 `IP,alias`、`#` はコメント）
- `-P, --panel-position`: サマリーパネル位置（`right|left|top|bottom|none`）
- `-m, --pause-mode`: 一時停止モード（`display|ping`）
- `-z, --timezone`: 表示用タイムゾーン（IANA 名、例: Asia/Tokyo。デフォルト UTC）
- `-Z, --snapshot-timezone`: スナップショット名に使うタイムゾーン（`utc|display`）
- `-F, --flash-on-fail`: 失敗時に画面を反転して注目を促す
- `-B, --bell-on-fail`: 失敗時に端末ベルを鳴らす
- `-C, --color`: 色付き表示を有効化
- `-H, --ping-helper`: `ping_helper` バイナリのパス（デフォルト `./ping_helper`）

### インタラクティブ操作（キーバインド）
- `n`: 表示名モードを切替（ip / rdns / alias）
- `v`: 表示切替（timeline / sparkline）
- `g`: ホスト選択を開いてフルスクリーン RTT グラフへ
- `o`: ソート方式を切替（failures / streak / latency / host）
- `f`: フィルタを切替（failures / latency / all）
- `a`: ASN 表示をトグル（表示領域が狭いと自動で非表示）
- `m`: サマリ表示内容を切替（rates / avg RTT / TTL / streak）
- `c`: 色付き表示をトグル
- `b`: 失敗時のベルをトグル
- `F`: サマリのフルスクリーン表示をトグル
- `w`: サマリーパネルの表示/非表示をトグル
- `W`: サマリーパネル位置を切替（left / right / top / bottom）
- `p`: 一時停止 / 再開（表示のみ、または ping も停止）
- `s`: スナップショットを `paraping_snapshot_YYYYMMDD_HHMMSS.txt` として保存
- `←` / `→`: 履歴を1ページ単位で遡る / 進める（履歴は録り続けられ、ライブ表示に戻るまで画面は固定）
- `↑` / `↓`: ホスト選択モードでないときはホスト一覧をスクロールします。ホスト選択モードでは選択の移動に `n`（次） と `p`（前） を使用してください。選択が表示領域を超えると一覧がスクロールして選択を視界に保ちます。
- `H`: ヘルプ表示（任意のキーで閉じる）
- `ESC`: フルスクリーングラフを終了
- `q`: 終了

### タイムライン / スパークライン凡例
- `.` 成功
- `!` 遅延（RTT >= `--slow-threshold`）
- `x` 失敗 / タイムアウト
- 色付き表示が有効な場合: 白=成功、黄=遅延、赤=失敗

## 注意事項
- ICMP は特権操作です。Linux では capability ベースの `ping_helper` を利用することで通常ユーザ権限で実行できますが、補助バイナリが使えない環境では管理者権限が必要です。
- ASN の取得は `whois.cymru.com` を利用します。ネットワーク側でブロックされている場合、ASN 情報は取得できません。
- IPv6 はサポートしていません。IPv4 アドレス、または IPv4 に解決されるホスト名を使用してください。
- 各ホストに対してワーカースレッドを 1 スレッド起動し、128 ホストの上限を設けています。上限を超えるとエラーで終了します。
- サマリーパネルを上／下に配置した場合、利用可能な空き行を使って表示を拡張します。端末幅が十分であれば全フィールドを表示します。

## パフォーマンスとスケーラビリティ

### 現行アーキテクチャ
ParaPing は「1 ping = 1 ヘルパープロセス」のモデルを採用しています。利点はセキュリティ、実装のシンプルさ、プロセス分離による信頼性です。

### マルチホスト性能
- 中規模（最大 128 ホスト）までの同時監視を想定
- 各ホストは独立したワーカースレッドと ping プロセスを持つ
- 接続済みソケットと ICMP フィルタでパケットのファンアウトを低減
- 受信バッファ（例: 256KB）により受信ドロップを抑制

### スケーラビリティに関する注意点
- プロセス生成のオーバーヘッド: 各 ping でプロセス生成が発生するため約 1–5 ms の追加遅延が生じる可能性
- システム制限: 生ソケットやファイルディスクリプタの数に注意（`ulimit -n` 等）
- カーネル負荷: 高頻度・多数ホストの監視ではソケットバッファや ICMP レート制限の調整が必要

### 将来の改善案
- バッチモード: 単一のヘルパープロセスで複数ホストを処理
- 永続ワーカー: 長寿命のプロセスで複数リクエストを受ける方式
- 共有ソケットプール: 同一宛先間でソケットを再利用する設計

## 貢献
貢献歓迎です。開発ルールやコントリビューション手順は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。モジュール分割やテスト方針については [MODULARIZATION.md](MODULARIZATION.md) を参照してください。

## 開発と検証（ローカルでの再現コマンド）
以下は CI と同等のチェックをローカルで行うためのコマンド例です。

### ビルド（ヘルパー）
```bash
make build
```

### 権限付与（Linux）
```bash
sudo make setcap
```

### Lint
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
pylint . --fail-under=9.0
```

### テスト（カバレッジ付）
```bash
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml
```

### Pre-PR チェックリスト（PR 作成前に確実に実施）
- LICENSE がプロジェクトルートに存在し、ファイルヘッダにライセンス表記がある
- LLM 帰属表記が新規／変更ファイルに含まれている
- Flake8 / Pylint を実行し問題を解消した
- テストがすべてパスしている（必要に応じてカバレッジ閾値を満たす）
- フォーマッタ（black 等）を実行した
- pre-commit フックを通した
- 最新の base ブランチにリベースし、コンフリクトがないことを確認した
- CI がグリーンであることを確認した
- ドキュメント／README／CHANGELOG の更新が含まれている（該当する場合）
- 人間によるレビューをリクエストした

PR の説明には上記チェックリストと、ローカルで実行した正確なコマンド・ログを含めてください。

## ライセンス
Apache License 2.0 — 詳細は [LICENSE](LICENSE) を参照してください。
