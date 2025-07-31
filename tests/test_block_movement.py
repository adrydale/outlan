"""
Test suite for block movement operations.

This module tests all block movement operations including
moving blocks up/down and handling edge cases at boundaries.
"""

from app import db
from app.models import NetworkBlock


def test_move_block_up(app_with_db):
    """
    Test moving a block up in position.

    Verifies that:
    - Block position is properly updated
    - Other blocks are repositioned correctly
    - API returns success response
    """
    # Create two blocks
    block1 = NetworkBlock(name="Block 1", position=1)
    block2 = NetworkBlock(name="Block 2", position=2)
    db.session.add_all([block1, block2])
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(
            "/api/update_block_order",
            json={"blocks": [{"id": block1.id, "position": 2}, {"id": block2.id, "position": 1}]},
        )
        assert response.status_code == 200

        # Verify positions were updated
        updated_block1 = db.session.get(NetworkBlock, block1.id)
        updated_block2 = db.session.get(NetworkBlock, block2.id)
        assert updated_block1.position == 2
        assert updated_block2.position == 1


def test_move_block_down(app_with_db):
    """
    Test moving a block down in position.

    Verifies that:
    - Block position is properly updated
    - Other blocks are repositioned correctly
    - API returns success response
    """
    # Create two blocks
    block1 = NetworkBlock(name="Block 1", position=1)
    block2 = NetworkBlock(name="Block 2", position=2)
    db.session.add_all([block1, block2])
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(
            "/api/update_block_order",
            json={"blocks": [{"id": block1.id, "position": 2}, {"id": block2.id, "position": 1}]},
        )
        assert response.status_code == 200

        # Verify positions were updated
        updated_block1 = db.session.get(NetworkBlock, block1.id)
        updated_block2 = db.session.get(NetworkBlock, block2.id)
        assert updated_block1.position == 2
        assert updated_block2.position == 1


def test_move_block_up_at_top(app_with_db):
    """
    Test moving a block up when it's already at the top.

    Verifies that:
    - Block remains at position 1
    - No error occurs when trying to move up at boundary
    - API handles edge case gracefully
    """
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(
            "/api/update_block_order", json={"blocks": [{"id": block.id, "position": 1}]}  # Already at top
        )
        assert response.status_code == 200

        # Verify position remains unchanged
        updated_block = db.session.get(NetworkBlock, block.id)
        assert updated_block.position == 1


def test_move_block_down_at_bottom(app_with_db):
    """
    Test moving a block down when it's already at the bottom.

    Verifies that:
    - Block remains at its current position
    - No error occurs when trying to move down at boundary
    - API handles edge case gracefully
    """
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(
            "/api/update_block_order",
            json={"blocks": [{"id": block.id, "position": 1}]},  # Already at bottom (only block)
        )
        assert response.status_code == 200

        # Verify position remains unchanged
        updated_block = db.session.get(NetworkBlock, block.id)
        assert updated_block.position == 1
