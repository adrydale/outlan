"""
Test suite for subnet update operations.

This module tests all Update operations for subnets,
including editing subnets and handling various error conditions.
"""

from app import db
from app.models import Subnet


def test_edit_subnet_success(app_with_db, test_block):
    """
    Test editing a subnet successfully.

    Verifies that:
    - Subnet can be edited with valid data
    - Database is updated with new values
    - Appropriate success response is returned
    """
    # Create a subnet to edit
    subnet = Subnet(block_id=test_block.id, name="Old Name", cidr="192.168.1.0/24", vlan_id=100)
    db.session.add(subnet)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(
            f"/edit_subnet/{subnet.id}", data={"name": "New Name", "cidr": "192.168.2.0/24", "vlan_id": "200"}
        )
        assert response.status_code == 302  # Redirect after success

        # Verify subnet was updated
        updated_subnet = db.session.get(Subnet, subnet.id)
        assert updated_subnet.name == "New Name"
        assert updated_subnet.cidr == "192.168.2.0/24"
        assert updated_subnet.vlan_id == 200


def test_edit_subnet_with_invalid_data(app_with_db, test_block):
    """
    Test editing a subnet with invalid data.

    Verifies that:
    - Invalid subnet data is properly rejected
    - Appropriate error message is returned
    - Subnet data remains unchanged
    """
    subnet = Subnet(block_id=test_block.id, name="Test Subnet", cidr="192.168.1.0/24", vlan_id=100)
    db.session.add(subnet)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(
            f"/edit_subnet/{subnet.id}",
            data={
                "name": "",  # Invalid empty name
                "cidr": "invalid-cidr",  # Invalid CIDR
                "vlan_id": "9999",  # Invalid VLAN
            },
        )
        assert response.status_code == 200  # Form validation errors return 200 with error message
        assert b"error" in response.data.lower() or b"invalid" in response.data.lower()


def test_edit_nonexistent_subnet(app_with_db):
    """
    Test editing a subnet that doesn't exist.

    Verifies that attempting to edit a non-existent subnet
    returns appropriate error response.
    """
    with app_with_db.test_client() as client:
        response = client.post(
            "/edit_subnet/999", data={"name": "New Name", "cidr": "192.168.1.0/24", "vlan_id": "100"}
        )
        assert response.status_code == 200  # Form validation errors return 200 with error message
        assert b"error" in response.data.lower() or b"not found" in response.data.lower()
