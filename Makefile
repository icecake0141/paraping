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

CC = gcc
CFLAGS = -Wall -Wextra -O2
TARGET = ping_helper
SRC = ping_helper.c

# Default target: build the helper
.PHONY: all
all: build

# Build the ICMP helper
.PHONY: build
build: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC)

# Set capabilities on the helper (requires sudo)
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

# Clean build artifacts
.PHONY: clean
clean: clean-python
	rm -f $(TARGET)

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

.PHONY: clean-python
clean-python:
	@echo "Cleaning Python build artifacts..."
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	@echo "Python build artifacts cleaned."
