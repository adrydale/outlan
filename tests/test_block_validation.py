"""
Test suite for block validation operations.

This module tests all validation operations for network blocks,
including name validation, position assignment, and collapse functionality.
"""

from app import db
from app.models import NetworkBlock


def test_block_name_validation(app_with_db):
    """
    Test block name validation rules.

    Verifies that:
    - Block names are properly validated
    - Invalid names are rejected
    - Valid names are accepted
    """
    with app_with_db.test_client() as client:
        # Test valid name
        response = client.post("/add_block", data={"block_name": "Valid Block Name"})
        assert response.status_code == 302  # Success

        # Test invalid name (empty)
        response = client.post("/add_block", data={"block_name": ""}, follow_redirects=True)
        # Form validation should return 200 with error message for good UX
        assert response.status_code == 200
        assert b"error" in response.data.lower() or b"cannot be empty" in response.data.lower()

        # Test invalid name (special characters)
        response = client.post(
            "/add_block", data={"block_name": 'Block<script>alert("xss")</script>'}, follow_redirects=True
        )
        # Form validation should return 200 with error message for good UX
        assert response.status_code == 200
        # XSS should be blocked with validation error, not processed
        assert b"invalid characters" in response.data.lower() or b"error" in response.data.lower()


def test_block_position_auto_assignment(app_with_db):
    """
    Test automatic position assignment for blocks.

    Verifies that:
    - New blocks get auto-assigned positions
    - Positions are sequential
    - Position assignment works correctly
    """
    with app_with_db.test_client() as client:
        # Create first block
        response = client.post("/add_block", data={"block_name": "Block 1"})
        assert response.status_code == 302

        # Create second block
        response = client.post("/add_block", data={"block_name": "Block 2"})
        assert response.status_code == 302

        # Verify positions were assigned correctly
        blocks = NetworkBlock.query.order_by(NetworkBlock.position).all()
        assert len(blocks) == 2
        assert blocks[0].position == 1
        assert blocks[1].position == 2


def test_toggle_block_collapse(app_with_db):
    """
    Test toggling block collapse state.

    Verifies that:
    - Block collapse state can be toggled
    - State is properly saved to database
    - API returns success response
    """
    block = NetworkBlock(name="Test Block", position=1, collapsed=False)
    db.session.add(block)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(f"/api/toggle_collapse/{block.id}")
        assert response.status_code == 200

        # Verify collapse state was toggled
        updated_block = db.session.get(NetworkBlock, block.id)
        assert updated_block.collapsed is True
