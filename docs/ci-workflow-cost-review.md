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

# GitHub Actions CI レビュー（コスト最適化観点）

## 結論（優先度順）

1. **`pr-checks.yml` は `ci.yml`（pull_request トリガー）と役割が重複しているため、統合または削除候補**。
2. **Dependabot 専用ワークフローは、既存 CI の条件分岐で代替可能**（二重実行削減）。
3. **テストマトリクスをイベント別に最適化**（PR は 1 バージョン、push/main は複数）。
4. **`pytest` を同一ジョブ内で複数回呼ぶ設計を減らす**（coverage summary 生成のための再実行削減）。

---

## ワークフローごとの冗長性レビュー

### 1) `.github/workflows/ci.yml`

- `pull_request` と `push` の両方で動作し、lint/test/mypy/coverage まで実行。
- test ジョブは Python `3.10` と `3.11` のマトリクスで実行されるため、PR あたりの実行時間は大きめ。
- `Coverage report by module` で `pytest` を再実行しており、コスト増の要因。

**コスト最適化提案**
- PR では `3.10` のみ、`push`（main/master）では `3.10/3.11` を回すよう条件分岐。
- coverage summary は `coverage xml/json` 等から生成して、`pytest` の再実行を避ける。

### 2) `.github/workflows/pr-checks.yml`

- `pull_request` で lint/mypy/pytest を再実行しており、`ci.yml` の PR 実行と強く重複。
- `logs/*.txt` 保存のために各ステップで手動リダイレクトを行っているが、これは必須ではない。
- `native build` が `continue-on-error: true` で実施されており、コストに対する品質ゲート効果が限定的。

**コスト最適化提案**
- 原則として `pr-checks.yml` は削除し、`ci.yml` に必要なログ/アーティファクト生成だけ統合。
- どうしても残す場合は、`paths` フィルタで対象を絞る（例: `src/native/**` 変更時のみ native build）。

### 3) `.github/workflows/dependabot-test.yml`

- Dependabot PR に限定してテストを実行する意図は明確。
- ただし `ci.yml` も pull_request で動くため、Dependabot PR では二重実行になりうる。
- 依存管理方式（poetry / requirements）の分岐が汎用的で、既存プロジェクト構成より広い。

**コスト最適化提案**
- `ci.yml` 側で `if: github.actor != 'dependabot[bot]'` を使い、Dependabot PR は専用ワークフローだけに寄せる、
  もしくは
- 専用ワークフローを廃止し、`ci.yml` に一本化して条件を整理する。

---

## すぐ効く最適化アクション（実施容易）

1. **PR の重複実行停止**
   - `pr-checks.yml` を削除 or 無効化。
2. **concurrency を導入**
   - 同一 PR への連続 push で古い実行をキャンセル。
3. **paths フィルタ導入**
   - ドキュメント変更のみでは重いテストをスキップ。
4. **pytest 再実行削減**
   - coverage summary 作成のための 2 回目 `pytest` を除去。

---

## 推奨ターゲット構成（例）

- `ci.yml` のみを主ワークフロー化。
- `pull_request`:
  - lint + mypy + unit test（Python 3.10 のみ）
- `push` on `main/master`:
  - lint + mypy + unit test（Python 3.10/3.11）
  - coverage upload
- native build:
  - `src/native/**` または `Makefile` 変更時のみ起動

この構成で、現状より GitHub Actions 実行分数を減らしつつ、品質ゲートの実効性を維持しやすい。
