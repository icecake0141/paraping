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

# Native Sources

This directory contains native C sources and build scripts for the ParaPing ICMP helper.

## Contents

- `ping_helper.c` - Native C implementation of ICMP ping using raw sockets
- `Makefile` - Build configuration for compiling the native helper

## Build Instructions

### Prerequisites

- GCC compiler
- Linux operating system (for raw socket support)
- libcap2-bin (for setcap utility)

### Building

To compile the ping helper:

```bash
cd src/native
make build
```

This will produce the `ping_helper` executable.

### Setting Capabilities

The ping helper requires `cap_net_raw` capability to create raw sockets. To set the capability:

```bash
cd src/native
make setcap
```

Note: This requires sudo privileges.

### Cleaning

To remove build artifacts:

```bash
cd src/native
make clean
```

## Usage

The compiled `ping_helper` binary is used by the Python wrapper to perform ICMP pings:

```bash
./ping_helper <host> <timeout_ms> [icmp_seq]
```

Example:
```bash
./ping_helper google.com 1000 1
```

## Security Notes

- The helper requires `cap_net_raw` capability or root privileges to create raw sockets
- Input validation is performed on all command-line arguments
- The helper uses strict ICMP reply matching to prevent spoofing

## Exit Codes

- 0: Success (ping reply received)
- 1: Invalid usage/arguments
- 2: Invalid argument value
- 3: Cannot resolve host
- 4: Cannot create socket / connect failed
- 5: Send failed
- 6: Select failed
- 7: Timeout
- 8: Receive failed
