"""
Test suite for block update operations.

This module tests all Update operations for network blocks,
including renaming blocks and handling various error conditions.
"""

from app import db
from app.models import NetworkBlock


def test_rename_block_success(app_with_db):
    """
    Test renaming a block successfully.

    Verifies that:
    - Block can be renamed with valid new name
    - Database is updated with new name
    - Appropriate success response is returned
    """
    block = NetworkBlock(name="Old Name", position=1)
    db.session.add(block)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(f"/rename_block/{block.id}", data={"new_block_name": "New Name"})
        assert response.status_code == 302  # Redirect after success

        # Verify block was renamed
        updated_block = db.session.get(NetworkBlock, block.id)
        assert updated_block.name == "New Name"


def test_rename_block_with_invalid_name(app_with_db):
    """
    Test renaming a block with invalid name.

    Verifies that empty or invalid block names are properly rejected
    with appropriate error response.
    """
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(
            f"/rename_block/{block.id}", data={"new_block_name": ""}, follow_redirects=True
        )  # Empty name
        # Form validation should return 200 with error message for good UX
        assert response.status_code == 200
        assert b"error" in response.data.lower() or b"cannot be empty" in response.data.lower()


def test_rename_block_with_duplicate_name(app_with_db):
    """
    Test renaming a block with duplicate name.

    Verifies that renaming to an existing block name is properly rejected
    and appropriate error message is returned.
    """
    # Create two blocks
    block1 = NetworkBlock(name="Block 1", position=1)
    block2 = NetworkBlock(name="Block 2", position=2)
    db.session.add_all([block1, block2])
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(
            f"/rename_block/{block1.id}", data={"new_block_name": "Block 2"}, follow_redirects=True
        )  # Duplicate name
        # Form validation should return 200 with error message for good UX
        assert response.status_code == 200
        assert b"already exists" in response.data.lower() or b"error" in response.data.lower()


def test_rename_nonexistent_block(app_with_db):
    """
    Test renaming a block that doesn't exist.

    Verifies that attempting to rename a non-existent block
    returns appropriate error response.
    """
    with app_with_db.test_client() as client:
        response = client.post("/rename_block/999", data={"new_block_name": "New Name"}, follow_redirects=True)
        # Non-existent resource should return 200 with appropriate error message
        assert response.status_code == 200
        assert b"error" in response.data.lower() or b"not found" in response.data.lower()
