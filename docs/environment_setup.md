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

# Development Environment Setup (Advanced)

## Overview

This document describes the **advanced development environment setup** for feature branch work on the ParaPing project. It uses the automated `scripts/setup_env.sh` script to streamline branch creation, dependency installation, and development tool setup.

**For general installation instructions**, see the [main README](../README.md#installation).

**For contributor setup**, see [CONTRIBUTING.md](CONTRIBUTING.md#development-setup).

This guide is specifically for developers who need to:
- Create and work on feature branches using the automated setup script
- Set up a reproducible development environment with specific tooling
- Follow the project's post-refactor development workflow

## Prerequisites

- Git configured with access to the repository
- Python 3.9 or newer
- pip package manager

## Quick Start

### For new setup (creates branch from origin/master)

```bash
# Run the setup script from the repository root
./scripts/setup_env.sh
```

This will:
1. Fetch the latest changes from `origin`
2. Create and checkout `feature/post-refactor-checks` from `origin/master`
3. Upgrade pip to the latest version
4. Install runtime dependencies (from `requirements.txt`)
5. Install development tools: pytest, flake8, pylint
6. Install optional dev dependencies (from `requirements-dev.txt`)

### For existing branch (skip branch creation)

If you're already on the target branch or want to skip branch creation:

```bash
./scripts/setup_env.sh --skip-branch
```

## Manual Setup (alternative)

If you prefer to run the commands manually:

```bash
# 1. Fetch and create branch
git fetch origin
git checkout -b feature/post-refactor-checks origin/master

# 2. Upgrade pip
python -m pip install --upgrade pip

# 3. Install dependencies
pip install -r requirements.txt || true

# 4. Install development tools
pip install pytest flake8 pylint

# 5. Optional: Install dev requirements
pip install -r requirements-dev.txt || true
```

## Capturing Setup Logs

To save the setup output for audit purposes:

```bash
./scripts/setup_env.sh 2>&1 | tee logs/setup_env.txt
```

The logs directory is configured to track the directory structure but ignore log files (*.txt, *.log).

## Verification

After running the setup script, verify the installation:

```bash
# Check branch
git branch

# Check tool versions
pytest --version
flake8 --version
pylint --version
```

## Next Steps

Once the environment is set up:

1. **Run tests**: `pytest tests/`
2. **Run linting**: `flake8 .`
3. **Run pylint**: `pylint *.py`
4. **Build the ping helper** (Linux): `make build` (outputs to `bin/ping_helper`)

## Troubleshooting

### Branch already exists

If `feature/post-refactor-checks` already exists locally:
- The script will switch to it instead of creating a new one
- Use `git branch -D feature/post-refactor-checks` to delete it first if you want a fresh start

### Permission issues

If you get permission errors during pip install:
- The script uses user installation (`--user` flag is automatic)
- Or use a virtual environment: `python -m venv venv && source venv/bin/activate`

### Origin/master not found

If the repository uses `main` instead of `master`:
- Edit `scripts/setup_env.sh` and change `BASE_BRANCH="origin/master"` to `BASE_BRANCH="origin/main"`

## Notes

- The script is idempotent - it's safe to run multiple times
- Log files in `logs/` are excluded from git commits
- All tools are installed at the user level to avoid requiring sudo

---

## 日本語

# 開発環境セットアップ（上級者向け）

## 概要

このドキュメントでは、ParaPingプロジェクトのフィーチャーブランチ作業のための**上級開発環境セットアップ**について説明します。自動化された`scripts/setup_env.sh`スクリプトを使用して、ブランチ作成、依存関係のインストール、開発ツールのセットアップを効率化します。

**一般的なインストール手順については**、[メインREADME](../README.md#installation)を参照してください。

**コントリビューターセットアップについては**、[CONTRIBUTING.md](CONTRIBUTING.md#development-setup)を参照してください。

このガイドは、以下のような開発者向けです：
- 自動化されたセットアップスクリプトを使用してフィーチャーブランチを作成し作業する
- 特定のツールを使用して再現可能な開発環境をセットアップする
- プロジェクトのリファクタリング後の開発ワークフローに従う

## 前提条件

- リポジトリへのアクセス権が設定されたGit
- Python 3.9以降
- pipパッケージマネージャー

## クイックスタート

### 新規セットアップ（origin/masterからブランチを作成）

```bash
# リポジトリルートからセットアップスクリプトを実行
./scripts/setup_env.sh
```

これにより、以下が実行されます：
1. `origin`から最新の変更を取得
2. `origin/master`から`feature/post-refactor-checks`を作成してチェックアウト
3. pipを最新バージョンにアップグレード
4. ランタイム依存関係をインストール（`requirements.txt`から）
5. 開発ツールをインストール：pytest、flake8、pylint
6. オプションの開発依存関係をインストール（`requirements-dev.txt`から）

### 既存のブランチ（ブランチ作成をスキップ）

すでに対象ブランチにいる場合、またはブランチ作成をスキップしたい場合：

```bash
./scripts/setup_env.sh --skip-branch
```

## 手動セットアップ（代替方法）

コマンドを手動で実行したい場合：

```bash
# 1. フェッチしてブランチを作成
git fetch origin
git checkout -b feature/post-refactor-checks origin/master

# 2. pipをアップグレード
python -m pip install --upgrade pip

# 3. 依存関係をインストール
pip install -r requirements.txt || true

# 4. 開発ツールをインストール
pip install pytest flake8 pylint

# 5. オプション：開発要件をインストール
pip install -r requirements-dev.txt || true
```

## セットアップログの保存

監査目的でセットアップ出力を保存するには：

```bash
./scripts/setup_env.sh 2>&1 | tee logs/setup_env.txt
```

logsディレクトリは、ディレクトリ構造を追跡するように設定されていますが、ログファイル（*.txt、*.log）は無視されます。

## 検証

セットアップスクリプトを実行した後、インストールを確認します：

```bash
# ブランチを確認
git branch

# ツールのバージョンを確認
pytest --version
flake8 --version
pylint --version
```

## 次のステップ

環境がセットアップされたら：

1. **テストを実行**：`pytest tests/`
2. **リンティングを実行**：`flake8 .`
3. **pylintを実行**：`pylint *.py`
4. **pingヘルパーをビルド**（Linux）：`make build`（`bin/ping_helper`に出力）

## トラブルシューティング

### ブランチが既に存在する

`feature/post-refactor-checks`がローカルに既に存在する場合：
- スクリプトは新しいブランチを作成する代わりに、既存のブランチに切り替えます
- 最初からやり直したい場合は、`git branch -D feature/post-refactor-checks`を使用して削除してください

### 権限の問題

pip installで権限エラーが発生した場合：
- スクリプトはユーザーインストールを使用します（`--user`フラグは自動）
- または仮想環境を使用：`python -m venv venv && source venv/bin/activate`

### origin/masterが見つからない

リポジトリが`master`の代わりに`main`を使用している場合：
- `scripts/setup_env.sh`を編集し、`BASE_BRANCH="origin/master"`を`BASE_BRANCH="origin/main"`に変更してください

## 注意事項

- このスクリプトはべき等です - 複数回実行しても安全です
- `logs/`のログファイルはgitコミットから除外されます
- すべてのツールはsudoを必要としないようにユーザーレベルでインストールされます
