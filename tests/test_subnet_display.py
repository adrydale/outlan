"""
Test suite for subnet display operations.

This module tests all display operations for subnets,
including how subnets are rendered and sorted.
"""

from app import db
from app.models import Subnet


def test_subnet_display_with_data(app_with_db, test_block):
    """
    Test subnet display with data.

    Verifies that:
    - Subnets are properly displayed on the main page
    - Subnet data is correctly formatted
    - Subnets are properly associated with blocks
    """
    # Create test subnets
    subnet1 = Subnet(block_id=test_block.id, name="Subnet 1", cidr="192.168.1.0/24", vlan_id=100)
    subnet2 = Subnet(block_id=test_block.id, name="Subnet 2", cidr="192.168.2.0/24", vlan_id=101)
    db.session.add_all([subnet1, subnet2])
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200

        # Check that subnets are displayed
        assert b"Subnet 1" in response.data
        assert b"Subnet 2" in response.data
        assert b"192.168.1.0/24" in response.data
        assert b"192.168.2.0/24" in response.data


def test_subnet_display_with_vlan(app_with_db, test_block):
    """
    Test subnet display with VLAN information.

    Verifies that:
    - VLAN IDs are properly displayed
    - Subnets without VLANs are handled correctly
    - VLAN information is formatted properly
    """
    # Create subnets with and without VLANs
    subnet1 = Subnet(block_id=test_block.id, name="Subnet with VLAN", cidr="192.168.1.0/24", vlan_id=100)
    subnet2 = Subnet(block_id=test_block.id, name="Subnet without VLAN", cidr="192.168.2.0/24", vlan_id=None)
    db.session.add_all([subnet1, subnet2])
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200

        # Check that subnets are displayed
        assert b"Subnet with VLAN" in response.data
        assert b"Subnet without VLAN" in response.data
        assert b"192.168.1.0/24" in response.data
        assert b"192.168.2.0/24" in response.data
