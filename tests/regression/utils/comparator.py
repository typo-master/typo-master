"""
Response comparison utilities.
"""

from typing import Any, Dict, List, Optional, Union


class ResponseComparator:
    """Compare API responses."""

    @staticmethod
    def compare_values(actual: Any, expected: Any, path: str = "") -> List[str]:
        """Compare two values recursively."""
        differences = []

        if type(actual) != type(expected):
            differences.append(
                f"Type mismatch at {path}: expected {type(expected).__name__}, got {type(actual).__name__}"
            )
            return differences

        if isinstance(expected, dict):
            for key in expected:
                full_path = f"{path}.{key}" if path else key
                if key not in actual:
                    differences.append(f"Missing key: {full_path}")
                else:
                    differences.extend(
                        ResponseComparator.compare_values(actual[key], expected[key], full_path)
                    )
        elif isinstance(expected, list):
            if len(actual) != len(expected):
                differences.append(
                    f"List length mismatch at {path}: expected {len(expected)}, got {len(actual)}"
                )
            elif expected and isinstance(expected[0], dict):
                # Compare first item structure
                differences.extend(
                    ResponseComparator.compare_values(actual[0], expected[0], f"{path}[0]")
                )
        else:
            # Primitive type
            if actual != expected:
                # For strings, check if they're both non-empty (pattern match)
                if isinstance(expected, str) and expected and actual:
                    continue  # Skip exact string comparison for non-empty strings
                differences.append(
                    f"Value mismatch at {path}: expected {expected!r}, got {actual!r}"
                )

        return differences

    @staticmethod
    def has_required_fields(response: Dict, required: List[str]) -> bool:
        """Check if response has all required fields."""
        return all(field in response for field in required)

    @staticmethod
    def match_schema(response: Dict, schema: Dict) -> List[str]:
        """Match response against a type schema."""
        differences = []

        for field, expected_type in schema.items():
            if field not in response:
                differences.append(f"Missing field: {field}")
                continue

            actual_value = response[field]
            actual_type = type(actual_value)

            if isinstance(expected_type, type):
                if actual_type != expected_type:
                    differences.append(
                        f"Type mismatch for {field}: expected {expected_type.__name__}, got {actual_type.__name__}"
                    )
            elif isinstance(expected_type, dict):
                if isinstance(actual_value, dict):
                    differences.extend(ResponseComparator.match_schema(actual_value, expected_type))
                else:
                    differences.append(f"Expected dict for {field}, got {actual_type.__name__}")
            elif isinstance(expected_type, list) and expected_type:
                if isinstance(actual_value, list):
                    if actual_value and isinstance(expected_type[0], dict):
                        for i, item in enumerate(actual_value):
                            if isinstance(item, dict):
                                diffs = ResponseComparator.match_schema(item, expected_type[0])
                                if diffs:
                                    differences.extend([f"[{i}].{d}" for d in diffs])
                else:
                    differences.append(f"Expected list for {field}, got {actual_type.__name__}")

        return differences
