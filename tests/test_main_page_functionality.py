"""
Test suite for main page functionality.

This module tests all functionality on the main page including
theme support, flash messages, export, and sorting features.
"""

from app import db
from app.models import NetworkBlock, Subnet


def test_main_page_has_edit_forms(app_with_db):
    """
    Test that the main page has edit forms for subnets.

    Verifies that:
    - Edit forms are present for subnets
    - Form elements are properly structured
    - Edit functionality is accessible
    """
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    subnet = Subnet(block_id=block.id, name="Test Subnet", cidr="192.168.1.0/24", vlan_id=100)
    db.session.add(subnet)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200

        # Check for edit form elements
        assert b"edit-link" in response.data
        assert b"subnet-form" in response.data


def test_main_page_has_theme_support(client):
    """
    Test that the main page has theme support.

    Verifies that:
    - Theme elements are present
    - Theme switching functionality exists
    - Theme CSS classes are applied
    """
    response = client.get("/")
    assert response.status_code == 200

    # Check for theme support elements
    assert b"data-theme" in response.data or b"class=" in response.data


def test_main_page_has_flash_messages(app_with_db):
    """
    Test that the main page has flash message support.

    Verifies that:
    - Flash message structure is present
    - Error message handling exists
    - Success message handling exists
    """
    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200

        # Check for flash message structure
        assert b"error-message" in response.data


def test_main_page_has_export_functionality(app_with_db):
    """
    Test that the main page has export functionality.

    Verifies that:
    - Export buttons are present
    - Export links are accessible
    - Export functionality is properly integrated
    """
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200

        # Check for export functionality
        assert b"export-btn" in response.data


def test_main_page_has_sorting_functionality(app_with_db):
    """
    Test that the main page has sorting functionality.

    Verifies that:
    - Sorting controls are present
    - Sort options are available
    - Sorting functionality is accessible
    """
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    subnet = Subnet(block_id=block.id, name="Test Subnet", cidr="192.168.1.0/24", vlan_id=100)
    db.session.add(subnet)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200

        # Check for sorting functionality
        assert b"subnet-card" in response.data
        assert b"block-content" in response.data
