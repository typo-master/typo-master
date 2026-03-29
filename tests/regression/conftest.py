"""
Regression testing fixtures and utilities.
"""

import pytest
import json
from pathlib import Path


@pytest.fixture
def baselines_dir():
    """Path to baselines directory."""
    return Path(__file__).parent / "baselines"


@pytest.fixture
def load_baseline(baselines_dir):
    """Load a baseline file."""
    def _load(name):
        baseline_file = baselines_dir / f"{name}.json"
        if baseline_file.exists():
            with open(baseline_file) as f:
                return json.load(f)
        return None
    return _load


@pytest.fixture
def save_baseline(baselines_dir):
    """Save a baseline file."""
    def _save(name, data):
        baseline_file = baselines_dir / f"{name}.json"
        with open(baseline_file, 'w') as f:
            json.dump(data, f, indent=2)
    return _save
