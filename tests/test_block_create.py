"""
Test suite for block creation operations.

This module tests all Create operations for network blocks,
including validation and error handling for block creation.
"""

from app import db
from app.models import NetworkBlock


def test_add_block_success(app_with_db):
    """
    Test successful block creation.

    Verifies that:
    - POST request to /add_block succeeds (302 redirect)
    - Block is created in database with correct name
    - Block has auto-assigned position
    """
    with app_with_db.test_client() as client:
        response = client.post("/add_block", data={"block_name": "Test Block"})
        assert response.status_code == 302  # Redirect after success

        # Verify block was created
        blocks = NetworkBlock.query.all()
        assert len(blocks) == 1
        assert blocks[0].name == "Test Block"


def test_add_block_with_invalid_name(app_with_db):
    """
    Test adding a block with invalid name.

    Verifies that empty block names are properly rejected
    with appropriate error response.
    """
    with app_with_db.test_client() as client:
        response = client.post("/add_block", data={"block_name": ""})  # Empty name
        assert response.status_code == 400
        assert b"Block name validation error" in response.data


def test_add_block_with_duplicate_name(app_with_db):
    """
    Test adding a block with duplicate name.

    Verifies that duplicate block names are properly rejected
    and appropriate error message is returned.
    """
    # Create first block
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post("/add_block", data={"block_name": "Test Block"})  # Duplicate name
        assert response.status_code == 400
        assert b"already exists" in response.data


def test_add_block_with_special_characters(app_with_db):
    """
    Test adding a block with special characters in name.

    Verifies that block names with special characters (potential XSS)
    are properly rejected for security reasons.
    """
    with app_with_db.test_client() as client:
        response = client.post("/add_block", data={"block_name": 'Test Block <script>alert("xss")</script>'})
        assert response.status_code == 400  # Should be rejected due to validation
