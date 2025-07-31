"""
Test suite for basic main page functionality.

This module tests basic main page operations including
page loading with empty and populated databases.
"""

from app import db
from app.models import NetworkBlock, Subnet


def test_main_page_loads_with_empty_database(app_with_db):
    """
    Test that the main page loads successfully with an empty database.

    Verifies that:
    - Page loads without errors
    - Basic UI elements are present
    - No data-related errors occur
    """
    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"Outlan" in response.data
        assert b"Add Block" in response.data


def test_main_page_loads_with_data(app_with_db):
    """
    Test that the main page loads successfully with existing data.

    Verifies that:
    - Page loads with blocks and subnets
    - Data is properly displayed
    - All UI elements are present
    """
    # Create test data
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    subnet = Subnet(block_id=block.id, name="Test Subnet", cidr="192.168.1.0/24", vlan_id=100)
    db.session.add(subnet)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"Test Block" in response.data
        assert b"Test Subnet" in response.data
        assert b"192.168.1.0/24" in response.data
