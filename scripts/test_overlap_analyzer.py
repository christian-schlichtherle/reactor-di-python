#!/usr/bin/env python3
"""
Test Overlap Analyzer - Identifies which tests hit the same lines of code.

This tool helps optimize test disjunctness by identifying overlapping test coverage,
allowing you to refactor tests so each line is tested by as few tests as possible.

Usage:
    python scripts/test_overlap_analyzer.py

Output:
    - Lines tested by multiple tests (overlap candidates for optimization)
    - Test disjunctness score
    - Recommendations for improving test isolation
"""

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set


def run_coverage_for_single_test(test_name: str) -> Set[str]:
    """Run coverage for a single test and return covered lines."""
    try:
        # Run single test with coverage
        result = subprocess.run(
            [
                "python",
                "-m",
                "pytest",
                test_name,
                "--cov=src",
                "--cov-report=json",
                "--tb=no",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        if result.returncode != 0:
            print(f"Warning: Test {test_name} failed")
            return set()

        # Parse coverage JSON
        with open("coverage.json") as f:
            coverage_data = json.load(f)

        covered_lines = set()
        for file_path, file_data in coverage_data["files"].items():
            if "src/reactor_di" in file_path:
                # Convert to relative path for consistency
                rel_path = file_path.replace("src/reactor_di/", "")
                for line_num in file_data["executed_lines"]:
                    covered_lines.add(f"{rel_path}:{line_num}")

        return covered_lines

    except Exception as e:
        print(f"Error running coverage for {test_name}: {e}")
        return set()


def get_all_test_names() -> List[str]:
    """Get list of all individual test names."""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        test_names = []
        for line in result.stdout.split("\n"):
            if "::" in line and "test_" in line:
                # Extract full test path like "tests/test_module.py::TestClass::test_method"
                test_names.append(line.strip())

        return test_names

    except Exception as e:
        print(f"Error collecting test names: {e}")
        return []


def analyze_test_overlap() -> Dict[str, List[str]]:
    """Analyze which tests cover the same lines."""
    print("🔍 Analyzing test overlap...")

    all_tests = get_all_test_names()
    print(f"Found {len(all_tests)} total tests")

    line_to_tests = defaultdict(list)

    for i, test in enumerate(all_tests):
        print(f"Analyzing test {i+1}/{len(all_tests)}: {test}")
        covered_lines = run_coverage_for_single_test(test)

        for line in covered_lines:
            line_to_tests[line].append(test)

    # Find overlapping lines (covered by multiple tests)
    return {line: tests for line, tests in line_to_tests.items() if len(tests) > 1}


def calculate_disjunctness_score(
    overlaps: Dict[str, List[str]], total_lines: int
) -> float:
    """Calculate test disjunctness score (0-100%)."""
    if total_lines == 0:
        return 100.0

    # Count lines with minimal overlap (1-2 tests)
    minimal_overlap_lines = sum(1 for tests in overlaps.values() if len(tests) <= 2)

    # Perfect disjunctness would be each line tested by exactly 1 test
    # Good disjunctness allows up to 2 tests per line (unit + integration)
    score = ((total_lines - len(overlaps) + minimal_overlap_lines) / total_lines) * 100

    return min(100.0, score)


def print_overlap_analysis(overlaps: Dict[str, List[str]]):
    """Print detailed overlap analysis."""
    print("\n" + "=" * 80)
    print("📊 TEST OVERLAP ANALYSIS RESULTS")
    print("=" * 80)

    if not overlaps:
        print("🎉 PERFECT DISJUNCTNESS: No test overlaps detected!")
        return

    # Group by overlap severity
    high_overlap = {line: tests for line, tests in overlaps.items() if len(tests) >= 5}
    medium_overlap = {
        line: tests for line, tests in overlaps.items() if 3 <= len(tests) < 5
    }
    low_overlap = {line: tests for line, tests in overlaps.items() if len(tests) == 2}

    total_lines_analyzed = len(overlaps) + 100  # Estimate total lines
    disjunctness_score = calculate_disjunctness_score(overlaps, total_lines_analyzed)

    print(f"📈 Test Disjunctness Score: {disjunctness_score:.1f}%")
    print(f"📊 Total overlapping lines: {len(overlaps)}")
    print(f"🔴 High overlap (5+ tests): {len(high_overlap)} lines")
    print(f"🟡 Medium overlap (3-4 tests): {len(medium_overlap)} lines")
    print(f"🟢 Low overlap (2 tests): {len(low_overlap)} lines")

    # Show high overlap issues
    if high_overlap:
        print("\n🔴 HIGH OVERLAP ISSUES (5+ tests per line):")
        for line, tests in sorted(high_overlap.items()):
            print(f"  📍 {line}")
            for test in tests[:3]:  # Show first 3 tests
                print(f"    - {test}")
            if len(tests) > 3:
                print(f"    ... and {len(tests)-3} more tests")
            print()

    # Show medium overlap
    if medium_overlap:
        print("\n🟡 MEDIUM OVERLAP (3-4 tests per line):")
        for line, tests in sorted(list(medium_overlap.items())[:5]):  # Show top 5
            print(f"  📍 {line}: {len(tests)} tests")

    print("\n💡 OPTIMIZATION RECOMMENDATIONS:")
    if high_overlap:
        print("  1. HIGH PRIORITY: Refactor tests hitting the same lines 5+ times")
        print("  2. Create more targeted unit tests for specific code paths")
        print("  3. Separate integration tests from unit tests")

    if medium_overlap:
        print("  4. MEDIUM PRIORITY: Review tests with 3-4 overlaps")
        print("  5. Consider using parametrized tests to reduce duplication")

    print(
        "  6. LOW PRIORITY: 2-test overlaps are often acceptable (unit + integration)"
    )


def main():
    """Main analysis function."""
    print("🚀 Ultra Test Strategy - Overlap Analysis Tool")
    print("=" * 50)

    # Change to project root
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    try:
        overlaps = analyze_test_overlap()
        print_overlap_analysis(overlaps)

        # Cleanup coverage files
        for file in ["coverage.json", ".coverage"]:
            if Path(file).exists():
                Path(file).unlink()

    except KeyboardInterrupt:
        print("\n⚠️ Analysis interrupted by user")
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
