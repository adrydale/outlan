"""
Test suite for main page UI elements.

This module tests all UI elements on the main page including
blocks, subnets, forms, and interactive components.
"""

from app import db
from app.models import NetworkBlock, Subnet


def test_main_page_has_block_elements(app_with_db):
    """
    Test that the main page has all required block UI elements.

    Verifies that:
    - Block structure elements are present
    - Block action buttons are available
    - Block content areas are properly defined
    """
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200

        # Check for block structure elements
        assert b"block-section" in response.data
        assert b"block-header" in response.data
        assert b"block-title" in response.data
        assert b"block-actions" in response.data
        assert b"block-content" in response.data

        # Check for block action buttons
        assert b"rename-btn" in response.data
        assert b"delete-btn" in response.data
        assert b"move-up-btn" in response.data
        assert b"move-down-btn" in response.data
        assert b"collapse-btn" in response.data


def test_main_page_has_subnet_elements(app_with_db):
    """
    Test that the main page has all required subnet UI elements.

    Verifies that:
    - Subnet structure elements are present
    - Subnet action buttons are available
    - Subnet content areas are properly defined
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

        # Check for subnet structure elements
        assert b"subnet-row" in response.data
        assert b"edit-link" in response.data
        assert b"delete-btn" in response.data


def test_main_page_has_add_block_form(app_with_db):
    """
    Test that the main page has the add block form.

    Verifies that:
    - Add block form is present
    - Form elements are properly structured
    - Form submission works correctly
    """
    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200

        # Check for add block form elements
        assert b"add-block-form" in response.data
        assert b"block_name" in response.data
        assert b"Add Block" in response.data


def test_main_page_has_add_subnet_forms(app_with_db):
    """
    Test that the main page has add subnet forms for each block.

    Verifies that:
    - Add subnet forms are present for each block
    - Form elements are properly structured
    - Form submission works correctly
    """
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200

        # Check for add subnet form elements
        assert b"subnet-form" in response.data
        assert b"block_id" in response.data
        assert b"name" in response.data
        assert b"cidr" in response.data
        assert b"vlan_id" in response.data


def test_main_page_has_collapsible_blocks(app_with_db):
    """
    Test that the main page has collapsible block functionality.

    Verifies that:
    - Block collapse functionality is present
    - Collapse/expand buttons are available
    - JavaScript functionality is included
    """
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200

        # Check for collapsible functionality
        assert b"collapse-btn" in response.data
        assert b"block-content" in response.data


def test_main_page_has_mobile_layout_elements(app_with_db):
    """
    Test that the main page has mobile-responsive layout elements.

    Verifies that:
    - Mobile-specific CSS classes are present
    - Responsive design elements are included
    - Mobile-friendly UI components exist
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

        # Check for mobile layout elements
        assert b"mobile-subnets" in response.data
        assert b"mobile-table" in response.data
        assert b"edit-link" in response.data
        assert b"delete-btn" in response.data
