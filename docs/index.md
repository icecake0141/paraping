<!--
Copyright 2026 icecake0141
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
-->

# ParaPing Documentation

Welcome to the ParaPing documentation hub. This directory contains comprehensive documentation for the ParaPing project, including setup guides, API references, design documents, and code review artifacts.

## Documentation Structure

### Setup & Environment
- [Environment Setup](environment_setup.md) - Development environment setup instructions

### Component Documentation
- [Ping Helper](ping_helper.md) - Detailed documentation for the privileged ICMP helper binary
  - CLI contract and usage
  - Security model and capabilities
  - Validation logic and error codes
  - Platform considerations

### API Reference
- [API Documentation](api/index.md) - Module and API documentation (placeholder)

### Code Reviews & Quality
- [Code Review Reports](reviews/) - Comprehensive code review artifacts
  - [CODE_REVIEW.md](reviews/CODE_REVIEW.md) - Full detailed code review report
  - [REVIEW_SUMMARY.md](reviews/REVIEW_SUMMARY.md) - Executive summary of code review

### Images & Diagrams
- [images/](images/) - Screenshots, diagrams, and visual documentation

## Quick Links

### For Users
- [Main README](../README.md) - Project overview and usage instructions
- [日本語版 README](../README.ja.md) - Japanese version of the README

### For Contributors
- [Contributing Guidelines](CONTRIBUTING.md) - Development guidelines and PR requirements
- [Modularization Guide](MODULARIZATION.md) - Module ownership and test organization
- [Code Review Report](reviews/CODE_REVIEW.md) - Security and quality analysis

### For Developers
- [API Documentation](api/index.md) - Module layout and API reference (coming soon)
- [Ping Helper Documentation](ping_helper.md) - Deep dive into the ICMP helper

## Repository Overview

ParaPing is an interactive terminal-based ICMP monitor that pings multiple hosts in parallel with live visualization. Key features include:

- **Concurrent monitoring** of up to 128 hosts
- **Live visualization** with timeline/sparkline modes
- **Security-focused design** using capability-based privileges (Linux)
- **Rich statistics** including RTT, jitter, TTL, and ASN information
- **Interactive controls** for sorting, filtering, and navigation

## Getting Started

1. **Installation**: See the [main README](../README.md#installation)
2. **Development Setup**: See [environment_setup.md](environment_setup.md)
3. **Contributing**: Read [CONTRIBUTING.md](CONTRIBUTING.md)
4. **Understanding the Code**: Review [MODULARIZATION.md](MODULARIZATION.md)

## Documentation Conventions

- All documentation files use Markdown format
- Code examples include syntax highlighting where applicable
- Security notes are prominently highlighted
- Platform-specific information is clearly marked

## Feedback

Found an issue with the documentation? Please open an issue on the [GitHub repository](https://github.com/icecake0141/paraping/issues).
