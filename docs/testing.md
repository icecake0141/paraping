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

# Testing Guide

## 1. Test Structure

- `tests/unit/`: unit tests
- `tests/integration/`: integration tests
- `tests/contract/`: contract/compatibility tests

## 2. Quick Run

```bash
pytest tests/ -v
```

## 3. Coverage Run

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

## 4. Selective Run Examples

```bash
pytest tests/unit/test_cli.py -v
pytest tests/integration/test_multi_host_integration.py -v
```

## 5. Recommended Pre-PR Checks

```bash
# blocking checks
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
pylint . --fail-under=9.0

# full test suite
pytest tests/ -v --cov=. --cov-report=term-missing
```

## 6. Notes

- Add tests with behavior changes and bug fixes.
- Keep CI checks green before opening or updating a PR.

## 7. Related Documents

- [Contributing](../CONTRIBUTING.md)
- [Docs Index](index.md)
