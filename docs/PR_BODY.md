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

# Pull Request Template

## Description

<!-- Provide a clear and concise description of the changes -->

### Related Issue(s)
<!-- Link to related issue(s), e.g., Fixes #123, Relates to #456 -->

### Summary of Changes
<!-- Brief summary of what was changed and why -->

### Rationale
<!-- Explain why these changes were made -->

### Tests Added
<!-- Describe any new tests added to validate the changes -->

### Documentation Updated
<!-- List any documentation that was updated (README, docs/, etc.) -->

### Backward Compatibility / Migration Notes
<!-- Note any breaking changes or migration steps required -->

## LLM Contribution Disclosure

**LLM Involvement:**
<!-- List files created/modified by LLM assistance -->
- Files created/modified with LLM assistance:
  - `<file1>`
  - `<file2>`
  - ...

**Human Review:**
<!-- Short note about human review performed -->
- Human review performed: [Describe review scope]

## Validation Commands

### Linting

**Flake8 (Strict - REQUIRED TO PASS):**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```
Expected: 0 errors

**Flake8 (Style - INFORMATIONAL):**
```bash
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
```
Expected: Informational output (violations reported but won't block)

**Pylint (REQUIRED TO PASS - Score >= 9.0/10):**
```bash
pylint . --fail-under=9.0
```
Expected: Score >= 9.0/10

**Ruff (Optional - Modern linter):**
```bash
ruff check . && ruff format . --check
```
Expected: No errors

### Testing

**Run all tests with coverage:**
```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```
Expected: All tests pass

**Run specific test suite:**
```bash
pytest tests/unit/ -v
pytest tests/contract/ -v
pytest tests/integration/ -v
```
Expected: All tests pass

### Type Checking (If applicable)

**MyPy (Optional):**
```bash
mypy .
```

### Formatting

**Black:**
```bash
black . --check
```
Expected: All files formatted correctly

**isort:**
```bash
isort . --check-only
```
Expected: All imports sorted correctly

### Build Validation (If applicable)

**Native build:**
```bash
make native 2>&1 | tee native_build.txt
```

**Helper binary:**
```bash
make build
```

### Pre-commit Hooks

**Run all pre-commit hooks:**
```bash
pre-commit run --all-files
```
Expected: All hooks pass

## PR Checklist

### License and Attribution
- [ ] License header (Apache-2.0 SPDX) added to new files
- [ ] Top-level LICENSE file is present in repository
- [ ] LLM attribution added to modified/generated files
- [ ] LLM-modified files explicitly listed in PR description above
- [ ] Human review notes included in PR description

### Code Quality
- [ ] Linting completed — Flake8 strict: 0 errors (command: `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`)
- [ ] Linting completed — Pylint score: ___/10 (command: `pylint . --fail-under=9.0`)
- [ ] Tests pass locally (command: `pytest tests/ -v --cov=. --cov-report=term-missing`)
- [ ] Static analysis/type checks pass (if applicable)
- [ ] Formatting applied (command: `black . --check && isort . --check-only`)
- [ ] Pre-commit hooks pass (command: `pre-commit run --all-files`)

### CI/CD
- [ ] CI build passes
- [ ] No merge conflicts with base branch
- [ ] Branch is up to date with base branch

### Documentation
- [ ] Changelog/versioning updated (if applicable)
- [ ] README.md updated (if functionality changed)
- [ ] Documentation updated in docs/ (if applicable)
- [ ] API docs updated (if applicable)
- [ ] Examples/quick-start updated (if applicable)

### Git Hygiene
- [ ] Commit messages follow repository conventions
- [ ] Commits are atomic and well-scoped
- [ ] No temporary files, build artifacts, or sensitive data committed

### PR Description Quality
- [ ] PR title is clear, descriptive, and uses imperative mood
- [ ] PR description includes: issue link, summary, rationale, tests, docs, migration notes
- [ ] PR description explicitly lists LLM-modified files and human review notes
- [ ] Validation commands listed with exact commands used

### Review Readiness
- [ ] Changes are minimal and focused on the issue
- [ ] No unrelated changes or fixes included
- [ ] Code is ready for human review
- [ ] Screenshots/logs attached (if UI or developer UX affected)

## Additional Notes

<!-- Any additional context, screenshots, logs, or information for reviewers -->

## Validation Logs

<details>
<summary>Flake8 Strict Output</summary>

```
<!-- Paste output here -->
```
</details>

<details>
<summary>Pylint Output</summary>

```
<!-- Paste output here -->
```
</details>

<details>
<summary>Test Output</summary>

```
<!-- Paste output here -->
```
</details>

---

**Human Review Required:** This PR includes LLM-generated code. Human review is mandatory before merging to verify correctness, security, and licensing compatibility.

---

## 日本語

# プルリクエストテンプレート

## 説明

<!-- 変更内容の明確で簡潔な説明を提供してください -->

### 関連Issue
<!-- 関連するissueへのリンク、例：Fixes #123、Relates to #456 -->

### 変更内容の要約
<!-- 何が変更され、なぜ変更されたかの簡潔な要約 -->

### 理由
<!-- これらの変更が行われた理由を説明してください -->

### 追加されたテスト
<!-- 変更を検証するために追加された新しいテストを説明してください -->

### 更新されたドキュメント
<!-- 更新されたドキュメントをリストしてください（README、docs/など） -->

### 後方互換性/移行に関する注意事項
<!-- 破壊的変更や必要な移行手順があれば記載してください -->

## LLM貢献の開示

**LLMの関与：**
<!-- LLMの支援により作成/変更されたファイルをリストしてください -->
- LLMの支援により作成/変更されたファイル：
  - `<ファイル1>`
  - `<ファイル2>`
  - ...

**人間によるレビュー：**
<!-- 実施された人間によるレビューについての簡単な注記 -->
- 実施された人間によるレビュー：[レビュー範囲を記述]

## 検証コマンド

### リンティング

**Flake8（厳格 - 合格必須）：**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```
期待値：0エラー

**Flake8（スタイル - 情報提供のみ）：**
```bash
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
```
期待値：情報出力（違反は報告されますがブロックしません）

**Pylint（合格必須 - スコア >= 9.0/10）：**
```bash
pylint . --fail-under=9.0
```
期待値：スコア >= 9.0/10

**Ruff（オプション - モダンなリンター）：**
```bash
ruff check . && ruff format . --check
```
期待値：エラーなし

### テスト

**カバレッジ付きですべてのテストを実行：**
```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```
期待値：すべてのテストが合格

**特定のテストスイートを実行：**
```bash
pytest tests/unit/ -v
pytest tests/contract/ -v
pytest tests/integration/ -v
```
期待値：すべてのテストが合格

### 型チェック（該当する場合）

**MyPy（オプション）：**
```bash
mypy .
```

### フォーマット

**Black：**
```bash
black . --check
```
期待値：すべてのファイルが正しくフォーマットされている

**isort：**
```bash
isort . --check-only
```
期待値：すべてのインポートが正しくソートされている

### ビルド検証（該当する場合）

**ネイティブビルド：**
```bash
make native 2>&1 | tee native_build.txt
```

**ヘルパーバイナリ：**
```bash
make build
```

### プリコミットフック

**すべてのプリコミットフックを実行：**
```bash
pre-commit run --all-files
```
期待値：すべてのフックが合格

## PRチェックリスト

### ライセンスと帰属

- [ ] 新しいファイルにライセンスヘッダー（Apache-2.0 SPDX）を追加
- [ ] リポジトリにトップレベルのLICENSEファイルが存在する
- [ ] 変更/生成されたファイルにLLM帰属を追加
- [ ] 上記のPR説明にLLM変更ファイルを明示的にリスト
- [ ] PR説明に人間によるレビューの注記を含む

### コード品質

- [ ] リンティング完了 — Flake8厳格：0エラー（コマンド：`flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`）
- [ ] リンティング完了 — Pylintスコア：___/10（コマンド：`pylint . --fail-under=9.0`）
- [ ] テストがローカルで合格（コマンド：`pytest tests/ -v --cov=. --cov-report=term-missing`）
- [ ] 静的解析/型チェックが合格（該当する場合）
- [ ] フォーマット適用（コマンド：`black . --check && isort . --check-only`）
- [ ] プリコミットフックが合格（コマンド：`pre-commit run --all-files`）

### CI/CD

- [ ] CIビルドが合格
- [ ] ベースブランチとのマージコンフリクトなし
- [ ] ブランチがベースブランチと最新の状態

### ドキュメント

- [ ] 変更履歴/バージョニングを更新（該当する場合）
- [ ] README.mdを更新（機能が変更された場合）
- [ ] docs/のドキュメントを更新（該当する場合）
- [ ] APIドキュメントを更新（該当する場合）
- [ ] 例/クイックスタートを更新（該当する場合）

### Git衛生管理

- [ ] コミットメッセージがリポジトリの規約に従っている
- [ ] コミットがアトミックで適切にスコープされている
- [ ] 一時ファイル、ビルド成果物、機密データがコミットされていない

### PR説明の品質

- [ ] PRタイトルが明確、説明的で、命令形を使用している
- [ ] PR説明に含まれる内容：issueリンク、要約、理由、テスト、ドキュメント、移行に関する注記
- [ ] PR説明にLLM変更ファイルと人間によるレビューの注記を明示的にリスト
- [ ] 使用した正確なコマンドとともに検証コマンドをリスト

### レビュー準備完了

- [ ] 変更は最小限でissueに焦点を当てている
- [ ] 無関係な変更や修正は含まれていない
- [ ] コードは人間によるレビューの準備ができている
- [ ] スクリーンショット/ログを添付（UIまたは開発者UXに影響がある場合）

## 追加の注記

<!-- レビュアーのための追加のコンテキスト、スクリーンショット、ログ、または情報 -->

## 検証ログ

<details>
<summary>Flake8厳格出力</summary>

```
<!-- ここに出力を貼り付けてください -->
```
</details>

<details>
<summary>Pylint出力</summary>

```
<!-- ここに出力を貼り付けてください -->
```
</details>

<details>
<summary>テスト出力</summary>

```
<!-- ここに出力を貼り付けてください -->
```
</details>

---

**人間によるレビューが必要：** このPRにはLLM生成コードが含まれています。正確性、セキュリティ、ライセンスの互換性を検証するために、マージ前に人間によるレビューが必須です。
