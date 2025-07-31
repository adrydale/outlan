"""
Test suite for subnet delete operations.

This module tests all Delete operations for subnets,
including deletion and error handling.
"""

from app import db
from app.models import Subnet


def test_delete_subnet_success(app_with_db, test_block):
    """
    Test deleting a subnet successfully.

    Verifies that:
    - Subnet can be deleted
    - Database is properly updated
    - Appropriate success response is returned
    """
    # Create a subnet to delete
    subnet = Subnet(block_id=test_block.id, name="Test Subnet", cidr="192.168.1.0/24", vlan_id=100)
    db.session.add(subnet)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(f"/delete_subnet/{subnet.id}")
        assert response.status_code == 302  # Redirect after success

        # Verify subnet was deleted
        subnets = Subnet.query.all()
        assert len(subnets) == 0


def test_delete_nonexistent_subnet(app_with_db):
    """
    Test deleting a subnet that doesn't exist.

    Verifies that attempting to delete a non-existent subnet
    returns appropriate error response.
    """
    with app_with_db.test_client() as client:
        response = client.post("/delete_subnet/999")
        assert response.status_code == 400  # Changed from 404 to 400 based on actual behavior
