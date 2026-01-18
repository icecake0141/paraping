# Post-Refactor Environment Setup

## Overview

This document describes the environment setup process for post-refactor work on the ParaPing project. The setup script automates branch creation, dependency installation, and development tool setup.

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
4. **Build the ping helper** (Linux): `make` or `gcc -o ping_helper ping_helper.c`

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
