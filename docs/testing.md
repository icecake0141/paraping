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

## English

# Testing Guide

## Test Structure

- `tests/unit/`: unit tests
- `tests/integration/`: integration tests
- `tests/contract/`: contract/compatibility tests

## Quick Runs

```bash
# default suite
make test

# full suite with verbose output
pytest tests/ -v

# coverage report
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml
```

## Selective Runs

```bash
pytest tests/unit/test_cli.py -v
pytest tests/integration/test_multi_host_integration.py -v
pytest tests/contract/test_ping_helper_contract.py -v
```

## Recommended Pre-PR Checks

```bash
# style and static checks (informational aggregate)
make lint

# strict blocking checks used by CI policy
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
pylint . --fail-under=9.0
mypy

# tests with coverage
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml
```

## Related Documents

- [Contributing (docs)](CONTRIBUTING.md)
- [Specification](specification.md)
- [Docs Index](index.md)

---

## 日本語

# テストガイド

## テスト構成

- `tests/unit/`: ユニットテスト
- `tests/integration/`: 統合テスト
- `tests/contract/`: 契約/互換テスト

## クイック実行

```bash
# デフォルト実行
make test

# 詳細表示で全体実行
pytest tests/ -v

# カバレッジ付き実行
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml
```

## 個別実行

```bash
pytest tests/unit/test_cli.py -v
pytest tests/integration/test_multi_host_integration.py -v
pytest tests/contract/test_ping_helper_contract.py -v
```

## PR 前の推奨チェック

```bash
# スタイル/静的チェック（総合）
make lint

# CI で重視される厳格チェック
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
pylint . --fail-under=9.0
mypy

# カバレッジ付きテスト
pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=xml
```

## 関連ドキュメント

- [Contributing（docs）](CONTRIBUTING.md)
- [仕様](specification.md)
- [ドキュメント一覧](index.md)
