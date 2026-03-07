#!/usr/bin/env python3
# Copyright 2026 icecake0141
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
"""Enforce baseline GitHub Actions security policies.

This checker blocks high-risk workflow patterns:
1) pull_request_target + checkout of pull_request.head.sha
2) Direct github.* expression interpolation inside run steps
   (require env indirection and shell-quoted usage instead)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

WORKFLOWS_DIR = Path(".github/workflows")

TRIGGER_PATTERN = re.compile(r"^\s*pull_request_target\s*:", re.MULTILINE)
HEAD_SHA_PATTERN = re.compile(
    r"\${{\s*github\.event\.pull_request\.head\.sha\s*}}",
    re.IGNORECASE,
)
UNSAFE_RUN_EXPR_PATTERN = re.compile(
    r"\${{\s*github\.(head_ref|event\.[^}]+)\s*}}",
    re.IGNORECASE,
)
RUN_START_PATTERN = re.compile(r"^\s*run\s*:\s*(\||>|[^\n]*)\s*$")


def _iter_run_blocks(lines: list[str]) -> list[tuple[int, str]]:
    """Return (line_number, line_text) for lines inside multiline run blocks."""
    findings: list[tuple[int, str]] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        match = RUN_START_PATTERN.match(line)
        if not match:
            idx += 1
            continue

        run_value = match.group(1).strip()
        if run_value in ("|", ">", "|-", ">-", "|+", ">+"):
            base_indent = len(line) - len(line.lstrip(" "))
            idx += 1
            while idx < len(lines):
                run_line = lines[idx]
                if run_line.strip() == "":
                    idx += 1
                    continue
                indent = len(run_line) - len(run_line.lstrip(" "))
                if indent <= base_indent:
                    break
                findings.append((idx + 1, run_line))
                idx += 1
            continue

        findings.append((idx + 1, line))
        idx += 1

    return findings


def check_workflow(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    violations: list[str] = []

    has_pull_request_target = bool(TRIGGER_PATTERN.search(content))
    has_head_sha_checkout = bool(HEAD_SHA_PATTERN.search(content))
    if has_pull_request_target and has_head_sha_checkout:
        violations.append(
            (
                "HIGH: pull_request_target is combined with checkout ref "
                "github.event.pull_request.head.sha (attacker-controlled code in privileged context)."
            )
        )

    for line_no, run_line in _iter_run_blocks(lines):
        if UNSAFE_RUN_EXPR_PATTERN.search(run_line):
            violations.append(
                (
                    f"MEDIUM: untrusted GitHub expression used directly in run block "
                    f"at line {line_no}. Use env: then quote shell variables."
                )
            )

    return violations


def main() -> int:
    if not WORKFLOWS_DIR.exists():
        print("No .github/workflows directory found; skipping workflow security check.")
        return 0

    workflow_files = sorted(
        list(WORKFLOWS_DIR.glob("*.yml")) + list(WORKFLOWS_DIR.glob("*.yaml")),
    )
    if not workflow_files:
        print("No workflow files found; skipping workflow security check.")
        return 0

    failed = False
    for workflow in workflow_files:
        violations = check_workflow(workflow)
        if not violations:
            continue

        failed = True
        print(f"[FAIL] {workflow}")
        for violation in violations:
            print(f"  - {violation}")

    if failed:
        print("\nWorkflow security policy violations detected.")
        print("Policy:")
        print("  - Never combine pull_request_target with checkout of pull_request.head.sha")
        print("  - Never place github.head_ref or github.event.* directly in run scripts")
        return 1

    print("Workflow security policy check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
