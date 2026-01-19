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

# Pull Request Template

## Description

<!-- Provide a clear and concise description of the changes -->

### Related Issue(s)
<!-- Link to related issue(s), e.g., Fixes #123, Relates to #456 -->

### Summary of Changes
<!-- Brief summary of what was changed and why -->

### Rationale
<!-- Explain why these changes were made -->

### Tests Added
<!-- Describe any new tests added to validate the changes -->

### Documentation Updated
<!-- List any documentation that was updated (README, docs/, etc.) -->

### Backward Compatibility / Migration Notes
<!-- Note any breaking changes or migration steps required -->

## LLM Contribution Disclosure

**LLM Involvement:**
<!-- List files created/modified by LLM assistance -->
- Files created/modified with LLM assistance:
  - `<file1>`
  - `<file2>`
  - ...

**Human Review:**
<!-- Short note about human review performed -->
- Human review performed: [Describe review scope]

## Validation Commands

### Linting

**Flake8 (Strict - REQUIRED TO PASS):**
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```
Expected: 0 errors

**Flake8 (Style - INFORMATIONAL):**
```bash
flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
```
Expected: Informational output (violations reported but won't block)

**Pylint (REQUIRED TO PASS - Score >= 9.0/10):**
```bash
pylint . --fail-under=9.0
```
Expected: Score >= 9.0/10

**Ruff (Optional - Modern linter):**
```bash
ruff check . && ruff format . --check
```
Expected: No errors

### Testing

**Run all tests with coverage:**
```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```
Expected: All tests pass

**Run specific test suite:**
```bash
pytest tests/unit/ -v
pytest tests/contract/ -v
pytest tests/integration/ -v
```
Expected: All tests pass

### Type Checking (If applicable)

**MyPy (Optional):**
```bash
mypy .
```

### Formatting

**Black:**
```bash
black . --check
```
Expected: All files formatted correctly

**isort:**
```bash
isort . --check-only
```
Expected: All imports sorted correctly

### Build Validation (If applicable)

**Native build:**
```bash
make native 2>&1 | tee native_build.txt
```

**Helper binary:**
```bash
make build
```

### Pre-commit Hooks

**Run all pre-commit hooks:**
```bash
pre-commit run --all-files
```
Expected: All hooks pass

## PR Checklist

### License and Attribution
- [ ] License header (Apache-2.0 SPDX) added to new files
- [ ] Top-level LICENSE file is present in repository
- [ ] LLM attribution added to modified/generated files
- [ ] LLM-modified files explicitly listed in PR description above
- [ ] Human review notes included in PR description

### Code Quality
- [ ] Linting completed — Flake8 strict: 0 errors (command: `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`)
- [ ] Linting completed — Pylint score: ___/10 (command: `pylint . --fail-under=9.0`)
- [ ] Tests pass locally (command: `pytest tests/ -v --cov=. --cov-report=term-missing`)
- [ ] Static analysis/type checks pass (if applicable)
- [ ] Formatting applied (command: `black . --check && isort . --check-only`)
- [ ] Pre-commit hooks pass (command: `pre-commit run --all-files`)

### CI/CD
- [ ] CI build passes
- [ ] No merge conflicts with base branch
- [ ] Branch is up to date with base branch

### Documentation
- [ ] Changelog/versioning updated (if applicable)
- [ ] README.md updated (if functionality changed)
- [ ] Documentation updated in docs/ (if applicable)
- [ ] API docs updated (if applicable)
- [ ] Examples/quick-start updated (if applicable)

### Git Hygiene
- [ ] Commit messages follow repository conventions
- [ ] Commits are atomic and well-scoped
- [ ] No temporary files, build artifacts, or sensitive data committed

### PR Description Quality
- [ ] PR title is clear, descriptive, and uses imperative mood
- [ ] PR description includes: issue link, summary, rationale, tests, docs, migration notes
- [ ] PR description explicitly lists LLM-modified files and human review notes
- [ ] Validation commands listed with exact commands used

### Review Readiness
- [ ] Changes are minimal and focused on the issue
- [ ] No unrelated changes or fixes included
- [ ] Code is ready for human review
- [ ] Screenshots/logs attached (if UI or developer UX affected)

## Additional Notes

<!-- Any additional context, screenshots, logs, or information for reviewers -->

## Validation Logs

<details>
<summary>Flake8 Strict Output</summary>

```
<!-- Paste output here -->
```
</details>

<details>
<summary>Pylint Output</summary>

```
<!-- Paste output here -->
```
</details>

<details>
<summary>Test Output</summary>

```
<!-- Paste output here -->
```
</details>

---

**Human Review Required:** This PR includes LLM-generated code. Human review is mandatory before merging to verify correctness, security, and licensing compatibility.
