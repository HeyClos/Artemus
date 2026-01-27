"""Basic tests to verify project setup is working correctly."""

import pytest
from hypothesis import given, strategies as st


def test_project_imports():
    """Verify the main package can be imported."""
    import newsletter_generator
    assert newsletter_generator.__version__ == "0.1.0"


def test_dependencies_available():
    """Verify all required dependencies are importable."""
    import yaml
    import feedparser
    import bs4
    import openai
    import macnotesapp
    import hypothesis
    
    assert yaml is not None
    assert feedparser is not None
    assert bs4 is not None
    assert openai is not None
    assert macnotesapp is not None
    assert hypothesis is not None


@pytest.mark.property
@given(st.integers())
def test_hypothesis_works(x: int):
    """Verify Hypothesis property-based testing is configured correctly."""
    assert isinstance(x, int)
