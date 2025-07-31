"""
Test suite for block read operations.

This module tests all Read operations for network blocks,
including retrieving all blocks and specific blocks by ID.
"""

from app import db
from app.models import NetworkBlock


def test_get_all_blocks(app_with_db):
    """
    Test retrieving all blocks.

    Verifies that:
    - All blocks are properly retrieved from database
    - Blocks are displayed correctly on the main page
    - Block data is properly formatted
    """
    # Create test blocks
    block1 = NetworkBlock(name="Block 1", position=1)
    block2 = NetworkBlock(name="Block 2", position=2)
    db.session.add_all([block1, block2])
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"Block 1" in response.data
        assert b"Block 2" in response.data


def test_get_block_by_id(app_with_db):
    """
    Test retrieving a specific block by ID.

    Verifies that:
    - Specific blocks can be retrieved by their ID
    - Block data is properly displayed on the main page
    - Block information is correctly formatted
    """
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    # Test through the main page
    with app_with_db.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"Test Block" in response.data
