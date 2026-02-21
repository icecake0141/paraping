#!/usr/bin/env python3
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
# Review for correctness and security.

"""
Pytest configuration helpers for ParaPing tests.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator, List, Optional


@contextmanager
def captured_logs(
    logger_name: Optional[str] = None,
    level: int = logging.WARNING,
) -> Iterator[List[logging.LogRecord]]:
    """Capture logs from the specified logger during the context."""
    records: List[logging.LogRecord] = []

    class ListHandler(logging.Handler):
        """Logging handler that stores log records in a list."""

        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger = logging.getLogger(logger_name)
    handler = ListHandler()
    handler.setLevel(level)
    previous_level = logger.level
    previous_propagate = logger.propagate
    logger.setLevel(level if previous_level == logging.NOTSET else min(previous_level, level))
    logger.propagate = False
    logger.addHandler(handler)
    try:
        yield records
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate


logging.captured_logs = captured_logs
