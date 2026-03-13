#!/usr/bin/env python3
# Copyright 2026 icecake0141
# SPDX-License-Identifier: Apache-2.0

"""Regression guards for usage doc synchronization."""

from pathlib import Path


def _usage_text() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / "docs" / "usage.md").read_text(encoding="utf-8")


def test_usage_doc_lists_new_cli_boolean_pairs() -> None:
    text = _usage_text()
    assert "--color, --no-color" in text
    assert "--flash-on-fail, --no-flash-on-fail" in text
    assert "--bell-on-fail, --no-bell-on-fail" in text
    assert "--ui-log-errors, --no-ui-log-errors" in text
    assert "--show-asn, --no-show-asn" in text


def test_usage_doc_lists_centralized_hotkeys() -> None:
    text = _usage_text()
    for token in ("`?`", "`d`", "`x`", "`h` / `l`", "`j` / `k`", "`u`", "`y`", "`Y`", "`S`"):
        assert token in text
