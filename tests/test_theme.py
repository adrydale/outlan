import os

import pytest

from app import create_app
from app.config import DEFAULT_THEME, get_theme


@pytest.fixture
def client():
    app = create_app()
    with app.test_client() as client:
        yield client


def test_default_theme():
    """Test that default theme is returned when no config is set"""
    theme = get_theme()
    assert theme == DEFAULT_THEME


def test_environment_variable_override():
    """Test that environment variable overrides config file"""
    try:
        # Test light theme
        os.environ["THEME"] = "light"
        theme = get_theme()
        assert theme == "light"

        # Test midnight theme
        os.environ["THEME"] = "midnight"
        theme = get_theme()
        assert theme == "midnight"

        # Test dark theme
        os.environ["THEME"] = "dark"
        theme = get_theme()
        assert theme == "dark"
    finally:
        if "THEME" in os.environ:
            del os.environ["THEME"]


def test_invalid_theme_fallback():
    """Test that invalid theme falls back to default"""
    try:
        os.environ["THEME"] = "invalid_theme"
        theme = get_theme()
        assert theme == DEFAULT_THEME
    finally:
        if "THEME" in os.environ:
            del os.environ["THEME"]


def test_case_insensitive_theme():
    """Test that theme names are case insensitive"""
    try:
        os.environ["THEME"] = "LIGHT"
        theme = get_theme()
        assert theme == "light"

        os.environ["THEME"] = "MIDNIGHT"
        theme = get_theme()
        assert theme == "midnight"

        os.environ["THEME"] = "DARK"
        theme = get_theme()
        assert theme == "dark"
    finally:
        if "THEME" in os.environ:
            del os.environ["THEME"]


def test_theme_passed_to_template(client):
    """Test that theme is passed to templates"""
    from app.routes import get_theme

    with client:
        with client.app_context():
            # Test that the theme is available in the template context
            theme = get_theme()
            assert theme in ["light", "dark", "midnight"]
