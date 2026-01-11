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
CFLAGS = -Wall -O2
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
clean:
	rm -f $(TARGET)
