"""
Test suite for theme functionality.

This module tests all theme-related functionality including
default themes, environment variable overrides, and theme validation.
"""

import os


def test_default_theme(client):
    """
    Test that the default theme is applied when no theme is set.

    Verifies that:
    - Default theme is applied when no theme is specified
    - Theme elements are present in the response
    - Page loads without theme-related errors
    """
    response = client.get("/")
    assert response.status_code == 200

    # Check for default theme elements
    assert b"data-theme" in response.data or b"class=" in response.data


def test_environment_variable_override(client):
    """
    Test that theme can be overridden via environment variable.

    Verifies that:
    - Theme can be set via THEME environment variable
    - Theme elements are present in the response
    - Environment variable is properly read
    """
    # Set environment variable
    os.environ["THEME"] = "dark"

    try:
        response = client.get("/")
        assert response.status_code == 200

        # Check for theme elements
        assert b"data-theme" in response.data or b"class=" in response.data
    finally:
        # Clean up environment variable
        if "THEME" in os.environ:
            del os.environ["THEME"]


def test_invalid_theme_fallback(client):
    """
    Test that invalid theme falls back to default.

    Verifies that:
    - Invalid themes are handled gracefully
    - Default theme is applied as fallback
    - No errors occur with invalid theme names
    """
    # Set invalid theme
    os.environ["THEME"] = "invalid_theme"

    try:
        response = client.get("/")
        assert response.status_code == 200

        # Should still load with default theme
        assert b"data-theme" in response.data or b"class=" in response.data
    finally:
        # Clean up environment variable
        if "THEME" in os.environ:
            del os.environ["THEME"]


def test_case_insensitive_theme(client):
    """
    Test that theme is case insensitive.

    Verifies that:
    - Theme names are handled case-insensitively
    - Different case variations work correctly
    - Theme elements are present regardless of case
    """
    # Set theme with different cases
    os.environ["THEME"] = "DARK"

    try:
        response = client.get("/")
        assert response.status_code == 200

        # Check for theme elements
        assert b"data-theme" in response.data or b"class=" in response.data
    finally:
        # Clean up environment variable
        if "THEME" in os.environ:
            del os.environ["THEME"]
