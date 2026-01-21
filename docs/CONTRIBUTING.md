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

# Contributing to ParaPing

Thank you for your interest in contributing to ParaPing! This document provides guidelines and instructions for developers.

## Development Setup

### Prerequisites
- Python 3.9 or newer
- GCC (for building the ping helper binary on Linux)
- libcap2-bin (for setting capabilities on Linux)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. Build the privileged ICMP helper (Linux only):
```bash
make build
sudo make setcap
```

## Code Quality Standards

ParaPing enforces strict code quality standards through automated linting and testing. All pull requests must pass these checks before merging.

### Linting Policy

The CI pipeline enforces the following lint checks:

#### 1. Flake8 (Strict - Syntax & Undefined Names)
Fails on Python syntax errors or undefined names. These are critical errors that must be fixed.

**Command:**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

**Error codes:**
- `E9`: Runtime errors (syntax errors, indentation errors)
- `F63`: Invalid print syntax
- `F7`: Syntax errors in type annotations
- `F82`: Undefined names in `__all__`

#### 2. Flake8 (Style Checks - Informational)
Reports style violations but does not fail the build. These should be fixed over time.

**Command:**
```bash
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
```

**Standards:**
- Maximum line length: 127 characters
- Maximum cyclomatic complexity: 10
- All PEP 8 style violations are reported

**Note:** This check is currently informational and will not block your PR. However, fixing these issues is encouraged to maintain code quality.

#### 3. Pylint (Code Quality)
Fails if the overall code score falls below 9.0/10. Ensures high code quality standards.

**Command:**
```bash
pylint . --fail-under=9.0
```

**What Pylint checks:**
- Code smells (duplicate code, too many arguments, etc.)
- Unused imports and variables
- Missing docstrings
- Naming conventions
- Code complexity metrics

### Running Lint Checks Locally

Before submitting a pull request, run all lint checks locally:

```bash
# Run all checks at once
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics && \
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics && \
pylint . --fail-under=9.0
```

**Expected output:**
- Flake8 strict: `0` errors (must pass)
- Flake8 style: informational (violations reported but won't block)
- Pylint: Score >= 9.0/10 (must pass)

If the strict flake8 or pylint checks fail, fix the issues before committing.

### Fixing Common Lint Issues

#### Flake8 Issues
- Line too long: Break long lines using parentheses or backslashes
- Trailing whitespace: Remove spaces at end of lines
- Unused imports: Remove or comment out unused imports

#### Pylint Issues
- Unused imports: Remove imports that aren't used
- Missing docstrings: Add docstrings to public functions/classes
- Too many arguments: Refactor to use configuration objects or reduce complexity
- Code duplication: Extract common code into shared functions

## Testing

Run the test suite before submitting changes:

```bash
# Run all tests with coverage
pytest tests/ -v --cov=. --cov-report=term-missing

# Run specific test file
pytest tests/test_main.py -v
```

Tests must pass with good coverage. Add tests for new functionality.

## Making Changes

1. **Create a feature branch:**
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes:**
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Run lint checks:**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
pylint *.py tests/*.py --fail-under=9.0
```

4. **Run tests:**
```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

5. **Commit your changes:**
```bash
git add .
git commit -m "Brief description of changes"
```

6. **Push and create a pull request:**
```bash
git push origin feature/your-feature-name
```

## Pull Request Guidelines

- **Title**: Use a clear, descriptive title
- **Description**: Explain what changes were made and why
- **Testing**: Describe how you tested the changes
- **Lint**: Ensure all lint checks pass (CI will verify)
- **Tests**: Ensure all tests pass and add new tests if needed
- **Documentation**: Update README.md or other docs if behavior changed

## CI/CD Pipeline

The CI pipeline runs automatically on all pull requests and includes:

1. **Lint checks** (Python 3.10):
   - Flake8 strict checks (syntax errors, undefined names) - **BLOCKING**
   - Flake8 style checks (line length, complexity, PEP 8) - **INFORMATIONAL**
   - Pylint quality checks (minimum score: 9.0/10) - **BLOCKING**

2. **Tests** (Python 3.10, 3.11):
   - Unit tests with pytest
   - Code coverage reporting
   - Coverage upload to Codecov

The flake8 strict and pylint checks must pass before a pull request can be merged.

## Code Review Process

1. Submit your pull request
2. Wait for automated CI checks to complete
3. Address any CI failures
4. Wait for maintainer review
5. Address review feedback if any
6. Once approved, your PR will be merged

## Questions or Issues?

If you have questions or run into issues:
- Check existing issues on GitHub
- Open a new issue with details about your problem
- Include error messages and steps to reproduce

Thank you for contributing to ParaPing!

---

## 日本語

# ParaPing への貢献

ParaPing への貢献にご興味をお持ちいただきありがとうございます！このドキュメントは開発者向けのガイドラインと手順を提供します。

## 開発環境のセットアップ

### 前提条件
- Python 3.9 以降
- GCC（Linux で ping ヘルパーバイナリをビルドするため）
- libcap2-bin（Linux で capabilities を設定するため）

### インストール

1. リポジトリをクローン：
```bash
git clone https://github.com/icecake0141/paraping.git
cd paraping
```

2. Python 依存関係をインストール：
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. 権限付与された ICMP ヘルパーをビルド（Linux のみ）：
```bash
make build
sudo make setcap
```

## コード品質基準

ParaPing は自動化された linting とテストを通じて厳格なコード品質基準を適用しています。すべてのプルリクエストはマージ前にこれらのチェックをパスする必要があります。

### Linting ポリシー

CI パイプラインは以下の lint チェックを適用します：

#### 1. Flake8（厳格 - 構文と未定義名）
Python 構文エラーまたは未定義名でエラーになります。これらは修正が必要な重大なエラーです。

**コマンド:**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

**エラーコード:**
- `E9`: 実行時エラー（構文エラー、インデントエラー）
- `F63`: 無効な print 構文
- `F7`: 型注釈の構文エラー
- `F82`: `__all__` で未定義の名前

#### 2. Flake8（スタイルチェック - 情報提供）
スタイル違反を報告しますが、ビルドは失敗しません。これらは時間をかけて修正する必要があります。

**コマンド:**
```bash
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
```

**基準:**
- 最大行長: 127 文字
- 最大循環的複雑度: 10
- すべての PEP 8 スタイル違反が報告されます

**注:** このチェックは現在情報提供のみで、PR をブロックしません。ただし、これらの問題を修正することでコード品質を維持することが推奨されます。

#### 3. Pylint（コード品質）
全体的なコードスコアが 9.0/10 を下回ると失敗します。高いコード品質基準を保証します。

**コマンド:**
```bash
pylint . --fail-under=9.0
```

**Pylint がチェックする内容:**
- コードスメル（重複コード、引数が多すぎるなど）
- 未使用のインポートと変数
- 不足している docstring
- 命名規則
- コード複雑度メトリクス

### ローカルで Lint チェックを実行

プルリクエストを提出する前に、すべての lint チェックをローカルで実行してください：

```bash
# すべてのチェックを一度に実行
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics && \
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics && \
pylint . --fail-under=9.0
```

**期待される出力:**
- Flake8 厳格: `0` エラー（必須パス）
- Flake8 スタイル: 情報提供（違反が報告されますがブロックされません）
- Pylint: スコア >= 9.0/10（必須パス）

厳格な flake8 または pylint チェックが失敗した場合、コミット前に問題を修正してください。

### 一般的な Lint 問題の修正

#### Flake8 の問題
- 行が長すぎる: 括弧またはバックスラッシュを使用して長い行を分割
- 末尾の空白: 行末のスペースを削除
- 未使用のインポート: 使用されていないインポートを削除またはコメントアウト

#### Pylint の問題
- 未使用のインポート: 使用されていないインポートを削除
- docstring の欠落: パブリック関数/クラスに docstring を追加
- 引数が多すぎる: 設定オブジェクトを使用するようにリファクタリングするか、複雑さを減らす
- コードの重複: 共通のコードを共有関数に抽出

## テスト

変更を提出する前にテストスイートを実行してください：

```bash
# カバレッジ付きですべてのテストを実行
pytest tests/ -v --cov=. --cov-report=term-missing

# 特定のテストファイルを実行
pytest tests/test_main.py -v
```

テストは良好なカバレッジでパスする必要があります。新機能にはテストを追加してください。

## 変更の作成

1. **フィーチャーブランチを作成:**
```bash
git checkout -b feature/your-feature-name
```

2. **変更を加える:**
   - 既存のコードスタイルに従う
   - 新機能にテストを追加
   - 必要に応じてドキュメントを更新

3. **lint チェックを実行:**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
pylint *.py tests/*.py --fail-under=9.0
```

4. **テストを実行:**
```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

5. **変更をコミット:**
```bash
git add .
git commit -m "Brief description of changes"
```

6. **プッシュしてプルリクエストを作成:**
```bash
git push origin feature/your-feature-name
```

## プルリクエストのガイドライン

- **タイトル**: 明確で説明的なタイトルを使用
- **説明**: 何が変更され、なぜ変更されたかを説明
- **テスト**: 変更をどのようにテストしたかを説明
- **Lint**: すべての lint チェックがパスすることを確認（CI が検証）
- **テスト**: すべてのテストがパスし、必要に応じて新しいテストを追加
- **ドキュメント**: 動作が変更された場合は README.md または他のドキュメントを更新

## 双方向言語ドキュメントの維持

ParaPing のすべてのドキュメントは、英語優先の双方向言語形式に従います：

1. **英語セクション**: 各ドキュメントは英語のコンテンツで始まります
2. **日本語翻訳**: 同じファイル内で英語セクションの直後に完全な日本語翻訳が続きます
3. **セクション見出し**: 言語セクションを区切るために `## English` と `## 日本語` を使用します
4. **一貫性**: 両方の言語セクションのコンテンツと構造を一貫させます

### ドキュメントを更新する際：

- 英語セクションと日本語セクションの両方を更新してください
- 両方の言語で同じ情報が利用可能であることを確認してください
- コード例、コマンド、技術用語は両方のセクションで一貫性を保ってください
- 新しいドキュメントファイルを作成する場合は、最初から双方向言語形式を使用してください

### 例：

```markdown
## English

# Document Title

Content in English...

## 日本語

# ドキュメントタイトル

日本語のコンテンツ...
```

## CI/CD パイプライン

CI パイプラインはすべてのプルリクエストで自動的に実行され、以下が含まれます：

1. **Lint チェック**（Python 3.10）：
   - Flake8 厳格チェック（構文エラー、未定義名） - **ブロッキング**
   - Flake8 スタイルチェック（行長、複雑さ、PEP 8） - **情報提供**
   - Pylint 品質チェック（最小スコア: 9.0/10） - **ブロッキング**

2. **テスト**（Python 3.10、3.11）：
   - pytest によるユニットテスト
   - コードカバレッジレポート
   - Codecov へのカバレッジアップロード

flake8 厳格チェックと pylint チェックは、プルリクエストをマージする前にパスする必要があります。

## コードレビュープロセス

1. プルリクエストを提出
2. 自動化された CI チェックが完了するまで待つ
3. CI の失敗に対処
4. メンテナーのレビューを待つ
5. レビューフィードバックがあれば対処
6. 承認されると、PR がマージされます

## 質問や問題？

質問がある場合や問題が発生した場合：
- GitHub で既存の issue を確認
- 問題の詳細を含む新しい issue を開く
- エラーメッセージと再現手順を含める

ParaPing への貢献ありがとうございます！
