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

Thank you for your interest in contributing! This guide explains how to set up
your development environment and the quality checks that run before each commit.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/icecake0141/paraping.git
cd paraping

# Set up the full development environment (installs deps + pre-commit hooks)
make dev

# Activate the virtual environment
source .venv/bin/activate
```

`make dev` does the following automatically:

1. Creates a `.venv` virtual environment.
2. Installs all runtime and development dependencies (see `requirements-dev.txt`).
3. Runs `pre-commit install` so the hooks fire on every `git commit`.

## Pre-commit Hooks

Once installed the hooks run automatically on `git commit`. To run them
manually against all files at any time:

```bash
pre-commit run --all-files
```

This will:

- **Auto-format** your code with [black](https://black.readthedocs.io/) and sort
  imports with [isort](https://pycqa.github.io/isort/) — no manual formatting
  needed.
- **Block the commit** if any of the following checks fail:
  | Hook | What it enforces |
  |------|-----------------|
  | `trailing-whitespace` | No trailing whitespace |
  | `end-of-file-fixer` | Files end with a newline |
  | `check-yaml` | Valid YAML syntax |
  | `check-merge-conflict` | No leftover merge-conflict markers |
  | `ruff` | Fast Python linting (auto-fix enabled) |
  | `flake8` | PEP 8 style errors |
  | `pylint` | Pylint score **≥ 9.0** (commits are blocked below this threshold) |
  | `mypy` | Static type checking |

## Running Checks Individually

```bash
# Linting (non-blocking informational run)
make lint

# Auto-format
make format

# Tests
make test
```

## Code Style

- Line length: **127** characters (configured in `pyproject.toml`).
- Formatter: **black** + **isort** (profile `black`).
- Type hints are encouraged; `mypy --strict` is enforced by the pre-commit hook.

## Pull Request Checklist

Before opening a PR, please ensure:

- [ ] `pre-commit run --all-files` passes with no errors.
- [ ] `make test` passes locally.
- [ ] New behaviour is covered by tests.
- [ ] Relevant documentation is updated.
