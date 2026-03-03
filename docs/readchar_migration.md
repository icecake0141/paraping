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

# Keyboard Input Migration to readchar

## English

## Overview

As of version 1.x, ParaPing migrated keyboard input handling to the [`readchar`](https://github.com/magmax/python-readchar)
library for cross-platform key definitions, while continuing to read directly from `sys.stdin` to avoid flushing buffered
input on some terminals.

## Changes

### What Changed

**Before (Custom Implementation):**
- Manual parsing of ANSI escape sequences
- Platform-specific handling using `select.select()` and `sys.stdin.read()`
- Custom timeout logic with `time.monotonic()`
- All code in `paraping/input_keys.py`

**After (readchar-assisted Implementation):**
- Reads input via `sys.stdin.read(1)` with `select.select()` for non-blocking behavior
- Uses `readchar` key constants and `parse_escape_sequence()` for consistent arrow-key mapping
- Preserves the public API and escape-sequence compatibility

### API Compatibility

The public API remains **fully compatible**. No changes are required for existing code:

- `read_key()` - Returns arrow key names ('arrow_up', 'arrow_down', etc.), characters, or None
- `parse_escape_sequence(seq)` - Still available for parsing custom sequences

### Benefits

1. **Cross-platform Support**: readchar handles platform differences (Linux, macOS, Windows) internally
2. **Maintainability**: Less custom code to maintain
3. **Reliability**: Well-tested library used by many projects
4. **Future Features**: Easier to add support for more special keys (F1-F12, etc.)

## Technical Details

### Implementation Strategy

The migration preserves the original non-blocking behavior by:

1. Using `select.select()` with zero timeout to check if input is available
2. Reading single bytes directly from `sys.stdin` once input is ready
3. Mapping arrow key sequences with `parse_escape_sequence()` (and `readchar` constants for compatibility)

### Sequence Handling

readchar provides key constants that map to escape sequences (e.g., `readchar.key.UP` is `"\x1b[A"`). The
`_map_readchar_key()` helper:

1. Maps readchar's standard constants (UP, DOWN, LEFT, RIGHT) to arrow key names
2. Falls back to `parse_escape_sequence()` for non-standard sequences
3. Supports modified keys (Ctrl+Arrow, Shift+Arrow, etc.)
4. Returns original value for unrecognized input

### Fallback Behavior

If readchar is not available, arrow-key constants are unavailable, but direct stdin reads still work for single-byte
input.

## Testing

All original tests were updated to work with the readchar-assisted implementation:

- 9 tests for `parse_escape_sequence()` - unchanged
- 11 tests for `read_key()` - updated to mock `sys.stdin.read()`
- Added test for exception handling and direct-read behavior

Run tests with:
```bash
make test
# or
pytest tests/unit/test_input_keys.py -v
```

## Dependencies

### New Dependency

- **readchar** >= 4.2.1 (Apache-2.0 license)
  - No known security vulnerabilities
  - Cross-platform support (Linux, macOS, Windows)
  - Active maintenance

### Installation

The dependency is automatically installed via:
```bash
make dev  # For development
# or
pip install -r requirements.txt  # For production
```

## Migration Notes for Maintainers

### If You Need to Debug Input Issues

1. Check if readchar is available: `READCHAR_AVAILABLE` flag
2. Test with different terminal emulators (xterm, iTerm2, Windows Terminal, etc.)
3. Use the unit tests as a reference for expected behavior
4. Remember: `select.select()` handles the non-blocking part, readchar handles the parsing

### Known Limitations

1. **Timeout Behavior**: Reading escape sequences relies on `select.select()` for timeouts
2. **No Input Simulation**: Can't easily simulate keypresses without mocking (tests use mocks)
3. **Terminal Requirements**: Still requires a TTY (checked via `sys.stdin.isatty()`)

### Compatibility Notes

- **Windows**: readchar uses `msvcrt` module on Windows
- **Unix/Linux/macOS**: readchar uses `termios` and `tty` modules
- **SSH/Remote Sessions**: Works, but may have increased latency (see ARROW_KEY_READ_TIMEOUT)

## Future Improvements

Potential enhancements enabled by readchar:

1. Support for function keys (F1-F12)
2. Support for Home/End/PageUp/PageDown
3. Better handling of modifier key combinations
4. Improved Windows console support

## References

- [readchar GitHub Repository](https://github.com/magmax/python-readchar)
- [ParaPing Issue Tracker](https://github.com/icecake0141/paraping/issues)
- Original implementation: commit before this migration

---

**Last Updated**: 2026-01-26
**Author**: ParaPing Team (with LLM assistance)
**License**: Apache-2.0

## 日本語

# readchar へのキーボード入力移行

## 概要

ParaPing は 1.x 系でキーボード入力処理を [`readchar`](https://github.com/magmax/python-readchar) に移行しました。
一方で、一部端末でバッファ済み入力がフラッシュされる問題を避けるため、入力取得自体は引き続き `sys.stdin` の直接読み取りを維持しています。

## 変更点

### 何が変わったか

**移行前（独自実装）:**
- ANSI エスケープシーケンスを手動解析
- `select.select()` と `sys.stdin.read()` によるプラットフォーム個別処理
- `time.monotonic()` を使った独自タイムアウト処理
- すべて `paraping/input_keys.py` に実装

**移行後（readchar 併用実装）:**
- ノンブロッキング判定は `select.select()`、入力は `sys.stdin.read(1)` を使用
- 矢印キー定義は `readchar` の定数と `parse_escape_sequence()` を利用
- 公開 API と既存のエスケープシーケンス互換性を維持

### API 互換性

公開 API は **完全互換** です。既存コードの変更は不要です。

- `read_key()`: 矢印キー名（`arrow_up` など）、通常文字、または `None` を返す
- `parse_escape_sequence(seq)`: カスタムシーケンス解析 API として継続

### 主な利点

1. **クロスプラットフォーム対応**: Linux/macOS/Windows 差異を `readchar` が吸収
2. **保守性向上**: 独自実装コードの削減
3. **信頼性向上**: 実績のあるライブラリ利用
4. **拡張容易性**: F1-F12 など追加キー対応がしやすい

## 技術詳細

### 実装方針

以下により、従来のノンブロッキング挙動を維持しています。

1. `select.select()`（ゼロタイムアウト）で入力有無を判定
2. 入力可能時に `sys.stdin` から 1 バイト読み取り
3. `parse_escape_sequence()` と `readchar` 定数でキーを正規化

### フォールバック

`readchar` が使えない環境でも、単一バイト入力は直接読み取りで動作します（矢印キー定数は利用不可）。

## テスト

- `parse_escape_sequence()` の既存 9 テストは維持
- `read_key()` の 11 テストを `sys.stdin.read()` モック前提で更新
- 例外処理と直接読み取り動作のテストを追加

実行コマンド:

```bash
make test
# or
pytest tests/unit/test_input_keys.py -v
```

## 依存関係

- **readchar** >= 4.2.1（Apache-2.0）
  - 既知の重大脆弱性なし
  - Linux/macOS/Windows 対応
  - 継続的にメンテナンスされている

インストール:

```bash
make dev
# or
pip install -r requirements.txt
```
