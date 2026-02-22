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

# ==============================================================================
# Configuration
# ==============================================================================
CC = gcc
CFLAGS = -Wall -Wextra -O2
TARGET = bin/ping_helper
SRC = src/native/ping_helper.c
VENV = .venv
PYTHON = python3

# ==============================================================================
# User Targets (for end users)
# ==============================================================================

# Default target: Setup user environment
.PHONY: all
all: user-setup
	@echo ""
	@echo "=============================================="
	@echo "User environment setup complete!"
	@echo "=============================================="
	@echo ""
	@echo "To run ParaPing:"
	@echo "  make run              # Run with default settings"
	@echo "  python3 paraping.py --help    # See all options"
	@echo ""
	@echo "To activate the virtual environment manually:"
	@echo "  source $(VENV)/bin/activate"
	@echo ""
	@echo "Next steps for Linux users:"
	@echo "  make setcap           # Configure ICMP helper (requires sudo)"
	@echo ""

# Setup user environment with virtual environment
.PHONY: user-setup
user-setup: $(VENV) build
	@echo "User environment ready. Run 'make run' or 'python3 paraping.py --help'"

# Create virtual environment and install runtime dependencies
$(VENV):
	@echo "Creating virtual environment in $(VENV)..."
	$(PYTHON) -m venv $(VENV)
	@echo "Installing runtime dependencies..."
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt
	@echo "Virtual environment created at $(VENV)"

# Run paraping with the virtual environment
.PHONY: run
run: $(VENV)
	@echo "Running ParaPing..."
	$(VENV)/bin/python paraping.py $(ARGS)

# ==============================================================================
# Developer Targets (for contributors and developers)
# ==============================================================================

# Setup developer environment with all dev tools
.PHONY: dev
dev: $(VENV) build
	@echo "Installing development dependencies..."
	$(VENV)/bin/pip install -r requirements-dev.txt
	@echo ""
	@echo "Installing pre-commit hooks..."
	$(VENV)/bin/pre-commit install || echo "Warning: pre-commit install failed"
	@echo ""
	@echo "=============================================="
	@echo "Development environment ready!"
	@echo "=============================================="
	@echo ""
	@echo "Activate the environment with:"
	@echo "  source $(VENV)/bin/activate"
	@echo ""
	@echo "Available development commands:"
	@echo "  make test             # Run tests"
	@echo "  make lint             # Run linters"
	@echo "  make format           # Format code"
	@echo "  make clean            # Clean build artifacts"
	@echo ""

# Run tests
.PHONY: test
test: $(VENV)
	@echo "Running tests..."
	$(VENV)/bin/pytest tests/ -v

# Run linters
.PHONY: lint
lint: $(VENV)
	@echo "Running linters..."
	@echo "==> flake8"
	$(VENV)/bin/flake8 . || true
	@echo ""
	@echo "==> pylint"
	$(VENV)/bin/pylint paraping/ main.py paraping.py || true
	@echo ""
	@echo "==> ruff"
	$(VENV)/bin/ruff check . || true

# Format code
.PHONY: format
format: $(VENV)
	@echo "Formatting code with black..."
	$(VENV)/bin/black .
	@echo "Sorting imports with isort..."
	$(VENV)/bin/isort .

# ==============================================================================
# Build Targets (cross-platform)
# ==============================================================================

# Build the ICMP helper
.PHONY: build
build: $(TARGET)

$(TARGET): $(SRC)
	@mkdir -p bin
	@echo "Building ICMP helper binary..."
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC)
	@echo "Build complete: $(TARGET)"

# ==============================================================================
# Linux-Specific Targets
# ==============================================================================

# Set capabilities on the helper (requires sudo, Linux only)
.PHONY: setcap
setcap: $(TARGET)
	@if ! command -v setcap >/dev/null 2>&1; then \
		echo "Error: setcap command not found."; \
		echo "On Debian/Ubuntu, install with: sudo apt-get install libcap2-bin"; \
		echo "On macOS/BSD, setcap is not available. Use setuid bit instead (not recommended)."; \
		exit 1; \
	fi
	@echo "Setting cap_net_raw+ep on $(TARGET)..."
	sudo setcap cap_net_raw+ep $(TARGET)
	@echo "Capabilities set successfully:"
	@getcap $(TARGET)

# ==============================================================================
# Cleanup Targets
# ==============================================================================

# Clean all build artifacts
.PHONY: clean
clean: clean-python clean-venv
	@echo "Removing ICMP helper binary..."
	rm -rf bin/
	@echo "All build artifacts cleaned."

.PHONY: clean-python
clean-python:
	@echo "Cleaning Python build artifacts..."
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	@echo "Python build artifacts cleaned."

.PHONY: clean-venv
clean-venv:
	@echo "Removing virtual environment..."
	rm -rf $(VENV)
	@echo "Virtual environment removed."

# ==============================================================================
# Help Target
# ==============================================================================

.PHONY: help
help:
	@echo "ParaPing Makefile - Available Targets"
	@echo "======================================"
	@echo ""
	@echo "User Targets (End Users):"
	@echo "  make                  Setup user environment (default)"
	@echo "  make user-setup       Create .venv and build bin/ping_helper"
	@echo "  make run [ARGS=...]   Run paraping.py with optional arguments"
	@echo "                        Example: make run ARGS='--help'"
	@echo "                        Example: make run ARGS='8.8.8.8 1.1.1.1'"
	@echo ""
	@echo "Developer Targets (Contributors):"
	@echo "  make dev              Setup development environment with dev tools"
	@echo "  make test             Run test suite"
	@echo "  make lint             Run linters (flake8, pylint, ruff)"
	@echo "  make format           Format code (black, isort)"
	@echo ""
	@echo "Build Targets:"
	@echo "  make build            Build the ping_helper ICMP binary (output: bin/ping_helper)"
	@echo "  make setcap           Set Linux capabilities on bin/ping_helper (requires sudo)"
	@echo ""
	@echo "Installation Targets (Alternative):"
	@echo "  make install-user     Install package to ~/.local (pip --user)"
	@echo "  make install-system   Install package system-wide (requires sudo)"
	@echo "  make install-wrapper  Install shell wrapper to /usr/local/bin"
	@echo "  make uninstall-user   Uninstall user installation"
	@echo "  make uninstall-system Uninstall system installation"
	@echo "  make uninstall-wrapper Remove wrapper script"
	@echo ""
	@echo "Cleanup Targets:"
	@echo "  make clean            Remove all build artifacts and .venv"
	@echo "  make clean-python     Remove Python build artifacts"
	@echo "  make clean-venv       Remove virtual environment only"
	@echo ""
	@echo "Platform Notes:"
	@echo "  - Virtual environment (.venv) works on Linux, macOS, and Windows"
	@echo "  - The 'setcap' target is Linux-only (use sudo on other platforms)"
	@echo "  - All user targets are cross-platform compatible"
	@echo ""

# ==============================================================================
# Installation Targets (alternative to virtual environment)
# ==============================================================================

# Build native components in src/native/
.PHONY: native
native:
	@echo "Building native components in src/native..."
	@cd src/native && if [ -f Makefile ]; then $(MAKE) build || exit 1; else echo "No native Makefile found in src/native"; fi

# Python package installation targets
.PHONY: build-python
build-python:
	@echo "Building Python wheel..."
	@if ! python3 -c "import build" 2>/dev/null; then \
		echo "Installing python build package..."; \
		python3 -m pip install --user --upgrade build; \
	fi
	python3 -m build

.PHONY: install-user
install-user: build-python
	@echo "Installing paraping for current user (--user)..."
	python3 -m pip install --user .
	@echo ""
	@echo "Installation complete!"
	@echo "The 'paraping' command should now be available."
	@echo ""
	@case ":$$PATH:" in \
		*":$$HOME/.local/bin:"*) ;; \
		*) echo "WARNING: ~/.local/bin is not in your PATH."; \
		   echo "Add it to your PATH by adding this line to your ~/.bashrc or ~/.zshrc:"; \
		   echo "  export PATH=\"\$$HOME/.local/bin:\$$PATH\""; \
		   echo "Then run: source ~/.bashrc  (or restart your shell)"; \
		   echo ""; \
		   ;; \
	esac

.PHONY: install-system
install-system: build-python
	@echo "Installing paraping system-wide (requires sudo)..."
	sudo python3 -m pip install .
	@echo ""
	@echo "System-wide installation complete!"
	@echo "The 'paraping' command should now be available."

.PHONY: install-wrapper
install-wrapper:
	@echo "Installing paraping shell wrapper to /usr/local/bin..."
	@if [ ! -f scripts/paraping ]; then \
		echo "Error: scripts/paraping wrapper not found."; \
		exit 1; \
	fi
	sudo cp scripts/paraping /usr/local/bin/paraping
	sudo chmod +x /usr/local/bin/paraping
	@echo ""
	@echo "Wrapper installation complete!"
	@echo "The 'paraping' command should now be available."
	@echo ""
	@echo "Note: This wrapper requires the paraping Python module to be importable."
	@echo "Either install the module with 'make install-user' or 'make install-system',"
	@echo "or run paraping from this directory with the module in PYTHONPATH."

.PHONY: uninstall-user
uninstall-user:
	@echo "Uninstalling paraping from user site-packages..."
	python3 -m pip uninstall -y paraping || true
	@echo "User installation uninstalled."

.PHONY: uninstall-system
uninstall-system:
	@echo "Uninstalling paraping from system site-packages..."
	sudo python3 -m pip uninstall -y paraping || true
	@echo "System installation uninstalled."

.PHONY: uninstall-wrapper
uninstall-wrapper:
	@echo "Removing paraping wrapper from /usr/local/bin..."
	sudo rm -f /usr/local/bin/paraping
	@echo "Wrapper removed."
