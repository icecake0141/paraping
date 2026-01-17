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
