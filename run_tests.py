#!/usr/bin/env python3
"""
Typo Master Backend Test Runner

Usage:
    python run_tests.py [category] [options]

Categories:
    unit        - Run unit tests only
    regression  - Run regression tests
    security    - Run security tests
    integration - Run integration tests
    critical    - Run critical tests (subset of all)
    all         - Run all tests

Options:
    --parallel          Run tests in parallel (requires pytest-xdist)
    --coverage          Generate coverage report
    --html-report       Generate HTML test report
    --fail-fast         Stop on first failure
    --verbose           Verbose output

Examples:
    python run_tests.py unit --parallel
    python run_tests.py regression --coverage
    python run_tests.py security --html-report
    python run_tests.py all --parallel --coverage --html-report
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """Test orchestration and execution."""

    CATEGORIES = {
        "unit": "tests/unit",
        "regression": "tests/regression",
        "security": "tests/security",
        "integration": "tests",
        "critical": "tests -m critical",
        "all": "tests",
    }

    MARKERS = {
        "unit": "unit",
        "regression": "regression",
        "security": "security",
        "integration": "integration",
        "critical": "critical",
        "all": None,
    }

    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.reports_dir = self.root_dir / "tests" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def build_command(
        self,
        category: str,
        parallel: bool = False,
        coverage: bool = False,
        html_report: bool = False,
        fail_fast: bool = False,
        verbose: bool = False,
    ) -> List[str]:
        """Build pytest command."""
        cmd = ["python", "-m", "pytest"]

        # Add category/marker
        marker = self.MARKERS.get(category)
        if marker:
            cmd.extend(["-m", marker])
        elif category == "all":
            cmd.append("tests")
        else:
            cmd.append(self.CATEGORIES.get(category, "tests"))

        # Add options
        if verbose:
            cmd.append("-v")

        if fail_fast:
            cmd.append("-x")

        if parallel:
            cmd.extend(["-n", "auto", "--dist", "loadgroup"])

        if coverage:
            cmd.extend([
                "--cov=app/backend",
                "--cov-report=term-missing:skip-covered",
                f"--cov-report=html:{self.reports_dir}/htmlcov",
                f"--cov-report=xml:{self.reports_dir}/coverage.xml",
            ])

        if html_report:
            cmd.extend([
                f"--html={self.reports_dir}/report.html",
                "--self-contained-html",
            ])

        # Always generate JUnit XML for CI
        cmd.extend([f"--junitxml={self.reports_dir}/junit.xml"])

        return cmd

    def run_tests(
        self,
        category: str,
        parallel: bool = False,
        coverage: bool = False,
        html_report: bool = False,
        fail_fast: bool = False,
        verbose: bool = False,
    ) -> int:
        """Run tests and return exit code."""
        cmd = self.build_command(
            category=category,
            parallel=parallel,
            coverage=coverage,
            html_report=html_report,
            fail_fast=fail_fast,
            verbose=verbose,
        )

        print(f"Running: {' '.join(cmd)}")
        print("=" * 80)

        result = subprocess.run(cmd, cwd=self.root_dir)

        print("=" * 80)
        if result.returncode == 0:
            print(f"\n✅ All {category} tests passed!")
        else:
            print(f"\n❌ Some {category} tests failed.")
            print(f"   See reports at: {self.reports_dir}")

        return result.returncode

    def list_categories(self):
        """List available test categories."""
        print("Available test categories:")
        for cat, path in self.CATEGORIES.items():
            print(f"  - {cat:12} : {path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Typo Master Backend Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py unit --parallel
  python run_tests.py regression --coverage
  python run_tests.py security --html-report
  python run_tests.py all --parallel --coverage --html-report
        """,
    )

    parser.add_argument(
        "category",
        choices=["unit", "regression", "security", "integration", "critical", "all"],
        help="Test category to run",
    )

    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)",
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report",
    )

    parser.add_argument(
        "--html-report",
        action="store_true",
        help="Generate HTML test report",
    )

    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_categories",
        help="List available test categories",
    )

    args = parser.parse_args()

    runner = TestRunner()

    if args.list_categories:
        runner.list_categories()
        return 0

    return runner.run_tests(
        category=args.category,
        parallel=args.parallel,
        coverage=args.coverage,
        html_report=args.html_report,
        fail_fast=args.fail_fast,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
