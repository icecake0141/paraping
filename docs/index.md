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

# ParaPing Documentation

Welcome to the ParaPing documentation hub. This directory contains comprehensive documentation for the ParaPing project, including setup guides, API references, design documents, and code review artifacts.

## Documentation Structure

### Setup & Environment
- [Environment Setup (Advanced)](environment_setup.md) - Advanced development environment setup for feature branch work using automated scripts

### Component Documentation
- [Ping Helper](ping_helper.md) - Detailed documentation for the privileged ICMP helper binary
  - CLI contract and usage
  - Security model and capabilities
  - Validation logic and error codes
  - Platform considerations

### API Reference
- [API Documentation](api/index.md) - Module and API documentation (placeholder)

### Images & Diagrams
- [images/](images/) - Screenshots, diagrams, and visual documentation

## Quick Links

### For Users
- [Main README](../README.md) - Project overview and usage instructions (available in English and Japanese)

### For Contributors
- [Contributing Guidelines](CONTRIBUTING.md) - Development guidelines and PR requirements
- [Modularization Guide](MODULARIZATION.md) - Module ownership and test organization

### For Developers
- [API Documentation](api/index.md) - Module layout and API reference (coming soon)
- [Ping Helper Documentation](ping_helper.md) - Deep dive into the ICMP helper

## Repository Overview

ParaPing is an interactive terminal-based ICMP monitor that pings multiple hosts in parallel with live visualization. Key features include:

- **Concurrent monitoring** of up to 128 hosts
- **Live visualization** with timeline/sparkline modes
- **Security-focused design** using capability-based privileges (Linux)
- **Rich statistics** including RTT, jitter, TTL, and ASN information
- **Interactive controls** for sorting, filtering, and navigation

## Getting Started

1. **Installation**: See the [main README](../README.md#installation) for user and system installation options
2. **Development Setup**: See [CONTRIBUTING.md](CONTRIBUTING.md#development-setup) for contributor setup
3. **Advanced/Automated Setup**: See [environment_setup.md](environment_setup.md) for feature branch automation with scripts
4. **Understanding the Code**: Review [MODULARIZATION.md](MODULARIZATION.md)

## Documentation Conventions

- All documentation files use Markdown format
- Code examples include syntax highlighting where applicable
- Security notes are prominently highlighted
- Platform-specific information is clearly marked

## Feedback

Found an issue with the documentation? Please open an issue on the [GitHub repository](https://github.com/icecake0141/paraping/issues).

---

## 日本語

# ParaPingドキュメント

ParaPingドキュメントハブへようこそ。このディレクトリには、セットアップガイド、APIリファレンス、設計ドキュメント、コードレビュー成果物を含むParaPingプロジェクトの包括的なドキュメントが含まれています。

## ドキュメント構造

### セットアップと環境
- [環境セットアップ（上級者向け）](environment_setup.md) - 自動化スクリプトを使用したフィーチャーブランチ作業のための上級開発環境セットアップ

### コンポーネントドキュメント
- [Pingヘルパー](ping_helper.md) - 特権ICMPヘルパーバイナリの詳細ドキュメント
  - CLIコントラクトと使用方法
  - セキュリティモデルとケイパビリティ
  - 検証ロジックとエラーコード
  - プラットフォームに関する考慮事項

### APIリファレンス
- [APIドキュメント](api/index.md) - モジュールとAPIドキュメント（プレースホルダー）

### 画像と図
- [images/](images/) - スクリーンショット、図、視覚的ドキュメント

## クイックリンク

### ユーザー向け
- [メインREADME](../README.md) - プロジェクト概要と使用方法（英語と日本語 / English and Japanese）

### コントリビューター向け
- [コントリビューティングガイドライン](CONTRIBUTING.md) - 開発ガイドラインとPR要件
- [モジュール化ガイド](MODULARIZATION.md) - モジュール所有権とテスト構成

### 開発者向け
- [APIドキュメント](api/index.md) - モジュールレイアウトとAPIリファレンス（近日公開）
- [Pingヘルパードキュメント](ping_helper.md) - ICMPヘルパーの詳細

## リポジトリ概要

ParaPingは、複数のホストを並列でpingし、ライブ視覚化を行うインタラクティブなターミナルベースのICMPモニターです。主な機能：

- 最大128ホストの**並行監視**
- タイムライン/スパークラインモードでの**ライブ視覚化**
- ケイパビリティベースの特権を使用した**セキュリティ重視の設計**（Linux）
- RTT、ジッター、TTL、ASN情報を含む**豊富な統計**
- ソート、フィルタリング、ナビゲーションのための**インタラクティブコントロール**

## はじめに

1. **インストール**：ユーザーおよびシステムインストールオプションについては、[メインREADME](../README.md#installation)を参照してください
2. **開発セットアップ**：コントリビューターセットアップについては、[CONTRIBUTING.md](CONTRIBUTING.md#development-setup)を参照してください
3. **上級/自動セットアップ**：スクリプトによるフィーチャーブランチ自動化については、[environment_setup.md](environment_setup.md)を参照してください
4. **コードの理解**：[MODULARIZATION.md](MODULARIZATION.md)を確認してください

## ドキュメント規約

- すべてのドキュメントファイルはMarkdown形式を使用
- コード例には該当する場合シンタックスハイライトを含む
- セキュリティに関する注意事項は目立つように強調表示
- プラットフォーム固有の情報は明確にマーク

## フィードバック

ドキュメントに問題を見つけましたか？[GitHubリポジトリ](https://github.com/icecake0141/paraping/issues)でissueを開いてください。
