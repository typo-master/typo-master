"""
Snapshot comparison utilities for regression tests.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class SnapshotComparator:
    """Compare API responses against baselines."""

    def __init__(self, baselines_dir: Path):
        self.baselines_dir = baselines_dir

    def load_baseline(self, name: str) -> Optional[Dict]:
        """Load a baseline file."""
        baseline_file = self.baselines_dir / f"{name}.json"
        if baseline_file.exists():
            with open(baseline_file) as f:
                return json.load(f)
        return None

    def save_baseline(self, name: str, data: Dict) -> None:
        """Save a baseline file."""
        baseline_file = self.baselines_dir / f"{name}.json"
        with open(baseline_file, 'w') as f:
            json.dump(data, f, indent=2)

    def compare_structure(self, actual: Dict, expected: Dict, path: str = "") -> List[str]:
        """Compare two dictionaries for structural equality."""
        differences = []

        for key in expected:
            full_path = f"{path}.{key}" if path else key

            if key not in actual:
                differences.append(f"Missing key: {full_path}")
                continue

            expected_type = type(expected[key])
            actual_type = type(actual[key])

            if expected_type != actual_type:
                differences.append(
                    f"Type mismatch at {full_path}: expected {expected_type.__name__}, got {actual_type.__name__}"
                )
                continue

            if isinstance(expected[key], dict):
                differences.extend(
                    self.compare_structure(actual[key], expected[key], full_path)
                )
            elif isinstance(expected[key], list) and expected[key]:
                # Check first item structure
                if actual[key]:
                    if isinstance(expected[key][0], dict):
                        differences.extend(
                            self.compare_structure(actual[key][0], expected[key][0], full_path + "[0]")
                        )

        return differences

    def assert_matches_baseline(self, actual: Dict, baseline_name: str) -> None:
        """Assert that actual matches baseline."""
        baseline = self.load_baseline(baseline_name)
        if baseline is None:
            raise AssertionError(f"Baseline not found: {baseline_name}")

        differences = self.compare_structure(actual, baseline)
        if differences:
            raise AssertionError(
                f"Response structure differs from baseline:\n" + "\n".join(differences)
            )


def normalize_response(response: Dict, ignore_fields: Optional[List[str]] = None) -> Dict:
    """Normalize a response for comparison."""
    if ignore_fields is None:
        ignore_fields = ["timestamp", "created_at", "updated_at", "executed_at"]

    result = {}
    for key, value in response.items():
        if key in ignore_fields:
            result[key] = "<ignored>"
        elif isinstance(value, dict):
            result[key] = normalize_response(value, ignore_fields)
        elif isinstance(value, list):
            result[key] = [
                normalize_response(item, ignore_fields) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result
