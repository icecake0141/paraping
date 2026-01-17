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
# Review required for correctness, security, and licensing.

"""
Coverage Summary Script

This script parses pytest coverage output and generates a summary suitable for
tracking coverage over time and comparing between branches/commits.

Usage:
    # Generate current coverage summary
    pytest tests/ --cov=. --cov-report=term > coverage_output.txt
    python scripts/coverage_summary.py coverage_output.txt

    # Compare coverage between baseline and current
    python scripts/coverage_summary.py coverage_baseline.txt coverage_current.txt --compare
"""

import argparse
import re
import sys
from typing import Any, Dict


def parse_coverage_report(content: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse pytest coverage output and extract module coverage data.

    Args:
        content: The raw text output from pytest --cov-report=term

    Returns:
        Dictionary mapping module names to coverage data (statements, miss, cover%)
    """
    coverage_data = {}

    # Find the coverage table in the output
    lines = content.split('\n')
    in_table = False

    for line in lines:
        # Look for the start of coverage table
        if 'Name' in line and 'Stmts' in line and 'Miss' in line and 'Cover' in line:
            in_table = True
            continue

        # Look for the end of coverage table
        if in_table and line.startswith('---'):
            continue

        if in_table and (line.startswith('TOTAL') or line.strip() == ''):
            # Parse TOTAL line
            if line.startswith('TOTAL'):
                parts = line.split()
                if len(parts) >= 4:
                    coverage_data['TOTAL'] = {
                        'stmts': int(parts[1]),
                        'miss': int(parts[2]),
                        'cover': parts[3].rstrip('%')
                    }
            in_table = False
            continue

        # Parse module coverage lines
        if in_table:
            # Match pattern: module_name.py    stmts   miss   cover%
            # Supports both integer and decimal percentages (e.g., 80% or 80.5%)
            match = re.match(r'^(\S+\.py)\s+(\d+)\s+(\d+)\s+(\d+(?:\.\d+)?)%', line)
            if match:
                module = match.group(1)
                coverage_data[module] = {
                    'stmts': int(match.group(2)),
                    'miss': int(match.group(3)),
                    'cover': match.group(4)
                }

    return coverage_data


def format_coverage_table(coverage_data: Dict[str, Dict[str, Any]],
                         title: str = "Coverage Summary") -> str:
    """
    Format coverage data as a readable table.

    Args:
        coverage_data: Module coverage data from parse_coverage_report
        title: Title for the table

    Returns:
        Formatted table as string
    """
    output = [f"\n{title}", "=" * len(title), ""]

    # Header
    output.append(f"{'Module':<40} {'Stmts':>8} {'Miss':>8} {'Cover':>8}")
    output.append("-" * 67)

    # Sort modules alphabetically, but put TOTAL last
    modules = sorted([k for k in coverage_data.keys() if k != 'TOTAL'])

    for module in modules:
        data = coverage_data[module]
        output.append(f"{module:<40} {data['stmts']:>8} {data['miss']:>8} {data['cover']:>7}%")

    # Add TOTAL if present
    if 'TOTAL' in coverage_data:
        output.append("-" * 67)
        data = coverage_data['TOTAL']
        output.append(f"{'TOTAL':<40} {data['stmts']:>8} {data['miss']:>8} {data['cover']:>7}%")

    return '\n'.join(output)


def _calculate_coverage_delta(baseline: Dict[str, Dict[str, Any]],
                              current: Dict[str, Dict[str, Any]],
                              module: str) -> tuple:
    """Calculate coverage delta for a module."""
    base_cov = baseline.get(module, {}).get('cover', '0')
    curr_cov = current.get(module, {}).get('cover', '0')

    base_val = float(base_cov)
    curr_val = float(curr_cov)
    delta = curr_val - base_val

    if module not in baseline:
        delta_str = f"+{curr_val:.1f}% (new)"
    elif module not in current:
        delta_str = f"-{base_val:.1f}% (removed)"
    elif delta != 0:
        sign = "+" if delta > 0 else ""
        delta_str = f"{sign}{delta:.1f}%"
    else:
        delta_str = "—"

    return (module, f"{base_val:.1f}%", f"{curr_val:.1f}%", delta_str, delta)


def compare_coverage(baseline: Dict[str, Dict[str, Any]],
                    current: Dict[str, Dict[str, Any]]) -> str:
    """
    Compare two coverage reports and show deltas.

    Args:
        baseline: Baseline coverage data
        current: Current coverage data

    Returns:
        Formatted comparison as string
    """
    output = ["\nCoverage Comparison (Baseline → Current)", "=" * 42, ""]

    # Header
    output.append(f"{'Module':<40} {'Baseline':>10} {'Current':>10} {'Delta':>10}")
    output.append("-" * 73)

    # Get all modules from both reports
    all_modules = sorted(set(baseline.keys()) | set(current.keys()) - {'TOTAL'})

    changes = [_calculate_coverage_delta(baseline, current, module)
               for module in all_modules]

    # Sort by delta (largest improvements first)
    changes.sort(key=lambda x: x[4], reverse=True)

    for module, base, curr, delta_str, _ in changes:
        output.append(f"{module:<40} {base:>10} {curr:>10} {delta_str:>10}")

    # TOTAL comparison
    if 'TOTAL' in baseline and 'TOTAL' in current:
        output.append("-" * 73)
        base_total = float(baseline['TOTAL']['cover'])
        curr_total = float(current['TOTAL']['cover'])
        delta_total = curr_total - base_total
        sign = "+" if delta_total > 0 else ""
        delta_str = f"{sign}{delta_total:.1f}%" if delta_total != 0 else "—"

        output.append(f"{'TOTAL':<40} {base_total:>9.1f}% {curr_total:>9.1f}% {delta_str:>10}")

        # Summary message
        output.append("")
        if delta_total > 0:
            output.append(f"✅ Coverage improved by {delta_total:.1f}%")
        elif delta_total < 0:
            output.append(f"⚠️  Coverage decreased by {abs(delta_total):.1f}%")
        else:
            output.append("➡️  Coverage unchanged")

    return '\n'.join(output)


def main():
    """Main entry point for coverage summary script."""
    parser = argparse.ArgumentParser(
        description="Parse and compare pytest coverage reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show coverage summary
  python scripts/coverage_summary.py coverage.txt

  # Compare baseline vs current
  python scripts/coverage_summary.py baseline.txt current.txt --compare
        """
    )
    parser.add_argument('baseline', help='Baseline coverage report file')
    parser.add_argument('current', nargs='?', help='Current coverage report file (for comparison)')
    parser.add_argument('--compare', action='store_true',
                       help='Compare baseline and current reports')

    args = parser.parse_args()

    # Read baseline report
    try:
        with open(args.baseline, 'r', encoding='utf-8') as f:
            baseline_content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {args.baseline}", file=sys.stderr)
        return 1

    baseline_data = parse_coverage_report(baseline_content)

    if not baseline_data:
        print("Error: Could not parse coverage data from baseline file", file=sys.stderr)
        return 1

    # If compare mode, read and compare with current
    if args.compare:
        if not args.current:
            print("Error: --compare requires two files", file=sys.stderr)
            return 1

        try:
            with open(args.current, 'r', encoding='utf-8') as f:
                current_content = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {args.current}", file=sys.stderr)
            return 1

        current_data = parse_coverage_report(current_content)

        if not current_data:
            print("Error: Could not parse coverage data from current file", file=sys.stderr)
            return 1

        # Show comparison
        print(format_coverage_table(baseline_data, "Baseline Coverage"))
        print(format_coverage_table(current_data, "Current Coverage"))
        print(compare_coverage(baseline_data, current_data))
    else:
        # Just show the single report
        print(format_coverage_table(baseline_data))

    return 0


if __name__ == '__main__':
    sys.exit(main())
