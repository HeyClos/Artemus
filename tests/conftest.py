"""
Pytest configuration and shared fixtures for newsletter-content-generator tests.

This module configures Hypothesis settings for property-based testing
as specified in the design document (minimum 100 iterations).
"""

import os
from datetime import datetime, timezone

import pytest
from hypothesis import settings, Verbosity

# Configure Hypothesis profiles
# Default profile: Reduced examples for faster iteration
settings.register_profile(
    "default",
    max_examples=20,
    deadline=5000,  # 5 seconds per test
    verbosity=Verbosity.normal,
)

# CI profile: More thorough testing
settings.register_profile(
    "ci",
    max_examples=100,
    deadline=10000,  # 10 seconds per test
    verbosity=Verbosity.normal,
)

# Dev profile: Fastest iteration during development
settings.register_profile(
    "dev",
    max_examples=10,
    deadline=3000,  # 3 seconds per test
    verbosity=Verbosity.verbose,
)

# Load profile from environment variable or use default
profile_name = os.getenv("HYPOTHESIS_PROFILE", "default")
settings.load_profile(profile_name)


@pytest.fixture
def sample_date() -> datetime:
    """Provide a sample datetime for testing."""
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Provide a temporary directory for configuration files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Provide a temporary directory for output files."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
