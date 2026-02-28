"""Guardrail: removed legacy history module should not be importable."""

import importlib

import pytest


def test_v2_legacy_history_module_is_removed() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("paraping_v2.legacy_history")
