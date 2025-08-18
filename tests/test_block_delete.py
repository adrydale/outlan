"""
Test suite for block delete operations.

This module tests all Delete operations for network blocks,
including deletion with and without subnets, and error handling.
"""

from app import db
from app.models import NetworkBlock, Subnet


def test_delete_block_success(app_with_db):
    """
    Test deleting a block successfully.

    Verifies that:
    - Block can be deleted when it has no subnets
    - Database is properly updated
    - Appropriate success response is returned
    """
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(f"/delete_block/{block.id}")
        assert response.status_code == 302  # Redirect after success

        # Verify block was deleted
        blocks = NetworkBlock.query.all()
        assert len(blocks) == 0


def test_delete_block_with_subnets(app_with_db):
    """
    Test deleting a block that contains subnets.

    Verifies that:
    - Block deletion cascades to delete all subnets
    - All related data is properly removed
    - Database integrity is maintained
    """
    # Create block with subnets
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    subnet1 = Subnet(block_id=block.id, name="Subnet 1", cidr="192.168.1.0/24", vlan_id=100)
    subnet2 = Subnet(block_id=block.id, name="Subnet 2", cidr="192.168.2.0/24", vlan_id=101)
    db.session.add_all([subnet1, subnet2])
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(f"/delete_block/{block.id}")
        assert response.status_code == 302  # Redirect after success

        # Verify block and subnets were deleted
        blocks = NetworkBlock.query.all()
        subnets = Subnet.query.all()
        assert len(blocks) == 0
        assert len(subnets) == 0


def test_delete_nonexistent_block(app_with_db):
    """
    Test deleting a block that doesn't exist.

    Verifies that attempting to delete a non-existent block
    returns appropriate error response.
    """
    with app_with_db.test_client() as client:
        response = client.post("/delete_block/999")
        assert response.status_code == 200  # Form validation errors return 200 with error message
        assert b"error" in response.data.lower() or b"not found" in response.data.lower()
