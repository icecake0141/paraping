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

ROOT_DIR = ../..
ROOT_HELPER = $(ROOT_DIR)/bin/ping_helper
LOCAL_HELPER = ping_helper

# Default target: build the helper
.PHONY: all
all: build

# Build the ICMP helper
.PHONY: build
build:
	@echo "Delegating build to repository root Makefile..."
	@$(MAKE) -C $(ROOT_DIR) build
	@cp $(ROOT_HELPER) $(LOCAL_HELPER)
	@echo "Synced local helper: $(LOCAL_HELPER)"

# Set capabilities on the helper (requires sudo)
.PHONY: setcap
setcap:
	@echo "Delegating setcap to repository root Makefile..."
	@$(MAKE) -C $(ROOT_DIR) setcap

# Clean build artifacts
.PHONY: clean
clean:
	@rm -f $(LOCAL_HELPER) $(ROOT_HELPER)
	@echo "Removed native helper artifacts."
