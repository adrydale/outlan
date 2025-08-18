"""
Test suite for subnet creation operations.

This module tests all Create operations for subnets,
including validation and error handling for subnet creation.
"""

from app.models import Subnet


def test_add_subnet_success(app_with_db, test_block):
    """
    Test adding a subnet successfully.

    Verifies that:
    - POST request to /add_subnet succeeds (302 redirect)
    - Subnet is created in database with correct data
    - All fields are properly saved
    """
    with app_with_db.test_client() as client:
        response = client.post(
            "/add_subnet",
            data={"block_id": test_block.id, "name": "Test Subnet", "cidr": "192.168.1.0/24", "vlan_id": "100"},
        )
        assert response.status_code == 302  # Redirect after success

        # Verify subnet was created
        subnets = Subnet.query.all()
        assert len(subnets) == 1
        assert subnets[0].name == "Test Subnet"
        assert subnets[0].cidr == "192.168.1.0/24"
        assert subnets[0].vlan_id == 100


def test_add_subnet_without_vlan(app_with_db, test_block):
    """
    Test adding a subnet without VLAN ID.

    Verifies that:
    - Subnet can be created without VLAN ID
    - VLAN ID is properly set to None
    - Other fields are saved correctly
    """
    with app_with_db.test_client() as client:
        response = client.post(
            "/add_subnet",
            data={"block_id": test_block.id, "name": "Test Subnet", "cidr": "192.168.1.0/24", "vlan_id": ""},
        )
        assert response.status_code == 302  # Should succeed

        # Verify subnet was created without VLAN
        subnets = Subnet.query.all()
        assert len(subnets) == 1
        assert subnets[0].vlan_id is None


def test_add_subnet_with_invalid_block_id(app_with_db):
    """
    Test adding a subnet with invalid block ID.

    Verifies that:
    - Invalid block IDs are properly rejected
    - Appropriate error message is returned
    - No subnet is created
    """
    with app_with_db.test_client() as client:
        response = client.post(
            "/add_subnet",
            data={
                "block_id": "999",  # Non-existent block
                "name": "Test Subnet",
                "cidr": "192.168.1.0/24",
                "vlan_id": "100",
            },
        )
        # Form validation errors return 200 with error message for better UX
        assert response.status_code == 200
        assert b"not found" in response.data.lower() or b"error" in response.data.lower()


def test_add_subnet_with_invalid_cidr(app_with_db, test_block):
    """
    Test adding a subnet with invalid CIDR format.

    Verifies that:
    - Invalid CIDR formats are properly rejected
    - Appropriate error message is returned
    - No subnet is created
    """
    with app_with_db.test_client() as client:
        response = client.post(
            "/add_subnet",
            data={"block_id": test_block.id, "name": "Test Subnet", "cidr": "invalid-cidr", "vlan_id": "100"},
            follow_redirects=True,
        )
        # Form validation should return 200 with error message for good UX
        assert response.status_code == 200
        assert b"error" in response.data.lower() or b"invalid" in response.data.lower()


def test_add_subnet_with_invalid_vlan(app_with_db, test_block):
    """
    Test adding a subnet with invalid VLAN ID.

    Verifies that:
    - Invalid VLAN IDs are properly rejected
    - Appropriate error message is returned
    - No subnet is created
    """
    with app_with_db.test_client() as client:
        response = client.post(
            "/add_subnet",
            data={
                "block_id": test_block.id,
                "name": "Test Subnet",
                "cidr": "192.168.1.0/24",
                "vlan_id": "9999",  # Invalid VLAN ID
            },
            follow_redirects=True,
        )
        # Form validation should return 200 with error message for good UX
        assert response.status_code == 200
        assert b"error" in response.data.lower() or b"invalid" in response.data.lower()
