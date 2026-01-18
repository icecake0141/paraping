#!/usr/bin/env bash
# Copyright 2025 icecake0141
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

# Environment Setup Script for Post-Refactor Work
# ================================================
# This script prepares the development environment for post-refactor checks
# on the feature/post-refactor-checks branch.
#
# Usage:
#   ./scripts/setup_env.sh [--skip-branch]
#
# Options:
#   --skip-branch   Skip the branch creation step (useful if already on the target branch)

set -e  # Exit on error
set -u  # Exit on undefined variable

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_BRANCH="feature/post-refactor-checks"
BASE_BRANCH="origin/master"
SKIP_BRANCH=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --skip-branch)
            SKIP_BRANCH=true
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--skip-branch]"
            exit 1
            ;;
    esac
done

cd "${REPO_ROOT}"

echo "=================================="
echo "ParaPing Environment Setup"
echo "=================================="
echo "Repository: ${REPO_ROOT}"
echo "Target branch: ${TARGET_BRANCH}"
echo "Base branch: ${BASE_BRANCH}"
echo ""

# Step 1: Fetch latest changes from origin
echo "[1/5] Fetching latest changes from origin..."
git fetch origin || true
echo ""

# Step 2: Create/switch to feature branch (unless --skip-branch is set)
if [ "${SKIP_BRANCH}" = false ]; then
    echo "[2/5] Creating/switching to ${TARGET_BRANCH} from ${BASE_BRANCH}..."
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    
    if [ "${CURRENT_BRANCH}" = "${TARGET_BRANCH}" ]; then
        echo "Already on ${TARGET_BRANCH}"
    elif git show-ref --verify --quiet "refs/heads/${TARGET_BRANCH}"; then
        echo "Branch ${TARGET_BRANCH} already exists, switching to it..."
        git checkout "${TARGET_BRANCH}"
    else
        echo "Creating new branch ${TARGET_BRANCH} from ${BASE_BRANCH}..."
        git checkout -b "${TARGET_BRANCH}" "${BASE_BRANCH}" || {
            echo "Warning: Failed to create branch from ${BASE_BRANCH}"
            echo "Attempting to create from current HEAD..."
            git checkout -b "${TARGET_BRANCH}"
        }
    fi
    echo ""
else
    echo "[2/5] Skipping branch creation (--skip-branch flag set)"
    echo "Current branch: $(git rev-parse --abbrev-ref HEAD)"
    echo ""
fi

# Step 3: Upgrade pip
echo "[3/5] Upgrading pip..."
python -m pip install --upgrade pip
echo ""

# Step 4: Install project dependencies
echo "[4/5] Installing project dependencies..."
if [ -f requirements.txt ]; then
    echo "Installing from requirements.txt..."
    pip install -r requirements.txt || echo "Warning: Some requirements.txt dependencies failed to install"
else
    echo "No requirements.txt found, skipping..."
fi
echo ""

# Step 5: Install development tools
echo "[5/5] Installing development tools..."
if [ -f requirements-dev.txt ]; then
    echo "Installing from requirements-dev.txt (includes pytest, flake8, pylint)..."
    pip install -r requirements-dev.txt || echo "Warning: Some requirements-dev.txt dependencies failed to install"
else
    echo "No requirements-dev.txt found, installing individual tools..."
    pip install pytest flake8 pylint
fi
echo ""

echo "=================================="
echo "Environment setup complete!"
echo "=================================="
echo ""
echo "Current branch: $(git rev-parse --abbrev-ref HEAD)"
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"
echo ""
echo "Next steps:"
echo "  - Run tests: pytest tests/"
echo "  - Run linting: flake8 ."
echo "  - Run pylint: pylint *.py"
echo ""
