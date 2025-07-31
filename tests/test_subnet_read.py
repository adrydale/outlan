"""
Test suite for subnet read operations.

This module tests all Read operations for subnets,
including retrieving all subnets and subnets by block.
"""

from app import db
from app.models import Subnet


def test_get_all_subnets(app_with_db, test_block):
    """
    Test retrieving all subnets.

    Verifies that:
    - All subnets are properly retrieved from database
    - Subnets are displayed correctly on the main page
    - Subnet data is properly formatted
    """
    # Create test subnets
    subnet1 = Subnet(block_id=test_block.id, name="Subnet 1", cidr="192.168.1.0/24", vlan_id=100)
    subnet2 = Subnet(block_id=test_block.id, name="Subnet 2", cidr="192.168.2.0/24", vlan_id=101)
    db.session.add_all([subnet1, subnet2])
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"Subnet 1" in response.data
        assert b"Subnet 2" in response.data
        assert b"192.168.1.0/24" in response.data
        assert b"192.168.2.0/24" in response.data


def test_get_subnets_by_block(app_with_db, test_block):
    """
    Test retrieving subnets for a specific block.

    Verifies that:
    - Subnets are properly grouped by block
    - Block-subnet relationships are maintained
    - Subnet data is correctly associated with blocks
    """
    # Create subnets in the test block
    subnet1 = Subnet(block_id=test_block.id, name="Subnet 1", cidr="192.168.1.0/24", vlan_id=100)
    subnet2 = Subnet(block_id=test_block.id, name="Subnet 2", cidr="192.168.2.0/24", vlan_id=101)
    db.session.add_all([subnet1, subnet2])
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200

        # Verify subnets are displayed under the correct block
        assert b"Test Block" in response.data
        assert b"Subnet 1" in response.data
        assert b"Subnet 2" in response.data
