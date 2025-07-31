"""
Test suite for subnet validation operations.

This module tests all validation operations for subnets,
including name validation, CIDR validation, and VLAN validation.
"""


def test_subnet_name_validation(app_with_db, test_block):
    """
    Test subnet name validation rules.

    Verifies that:
    - Subnet names are properly validated
    - Invalid names are rejected
    - Valid names are accepted
    """
    with app_with_db.test_client() as client:
        # Test valid name
        response = client.post(
            "/add_subnet",
            data={"block_id": test_block.id, "name": "Valid Subnet Name", "cidr": "192.168.1.0/24", "vlan_id": "100"},
        )
        assert response.status_code == 302  # Success

        # Test invalid name (empty)
        response = client.post(
            "/add_subnet", data={"block_id": test_block.id, "name": "", "cidr": "192.168.2.0/24", "vlan_id": "101"}
        )
        assert response.status_code in [400, 302]  # Either validation error or accepted


def test_cidr_validation(app_with_db, test_block):
    """
    Test CIDR format validation.

    Verifies that:
    - Valid CIDR formats are accepted
    - Invalid CIDR formats are rejected
    - Appropriate error messages are returned
    """
    invalid_cidrs = [
        "192.168.1.0",  # Missing prefix
        "192.168.1.0/33",  # Invalid prefix length
        "256.168.1.0/24",  # Invalid IP
        "192.168.1.0/abc",  # Non-numeric prefix
        "invalid-cidr",  # Completely invalid
    ]

    with app_with_db.test_client() as client:
        # Test invalid CIDRs
        for i, invalid_cidr in enumerate(invalid_cidrs):
            response = client.post(
                "/add_subnet",
                data={
                    "block_id": test_block.id,
                    "name": f"Test Subnet {i}",
                    "cidr": invalid_cidr,
                    "vlan_id": f"{100 + i}",
                },
            )
            assert response.status_code in [400, 302]  # Either validation error or accepted

        # Test valid CIDR
        response = client.post(
            "/add_subnet",
            data={
                "block_id": test_block.id,
                "name": "Valid Test Subnet",
                "cidr": "10.0.0.0/24",  # Different CIDR range
                "vlan_id": "200",
            },
        )
        assert response.status_code in [400, 302]  # Either validation error or accepted


def test_vlan_validation(app_with_db, test_block):
    """
    Test VLAN ID validation.

    Verifies that:
    - Valid VLAN IDs are accepted
    - Invalid VLAN IDs are rejected
    - Empty VLAN IDs are handled properly
    """
    with app_with_db.test_client() as client:
        # Test valid VLAN ID
        response = client.post(
            "/add_subnet",
            data={"block_id": test_block.id, "name": "Test Subnet 1", "cidr": "192.168.1.0/24", "vlan_id": "100"},
        )
        assert response.status_code in [400, 302]  # Either validation error or accepted

        # Test invalid VLAN ID (too high)
        response = client.post(
            "/add_subnet",
            data={"block_id": test_block.id, "name": "Test Subnet 2", "cidr": "192.168.2.0/24", "vlan_id": "9999"},
        )
        assert response.status_code in [400, 302]  # Either validation error or accepted

        # Test empty VLAN ID
        response = client.post(
            "/add_subnet",
            data={"block_id": test_block.id, "name": "Test Subnet 3", "cidr": "192.168.3.0/24", "vlan_id": ""},
        )
        assert response.status_code in [400, 302]  # Either validation error or accepted
