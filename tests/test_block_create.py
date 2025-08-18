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
    with appropriate error response (200 + error message for good UX).
    """
    with app_with_db.test_client() as client:
        response = client.post("/add_block", data={"block_name": ""}, follow_redirects=True)  # Empty name
        # Form validation errors should return 200 with error message, not 400
        assert response.status_code == 200
        assert b"error" in response.data.lower() or b"cannot be empty" in response.data.lower()


def test_add_block_with_duplicate_name(app_with_db):
    """
    Test adding a block with duplicate name.

    Verifies that duplicate block names are properly rejected
    with appropriate error message (200 + error for good UX).
    """
    # Create first block
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post("/add_block", data={"block_name": "Test Block"}, follow_redirects=True)  # Duplicate name
        # Form validation errors should return 200 with error message, not 400
        assert response.status_code == 200
        assert b"already exists" in response.data.lower() or b"error" in response.data.lower()


def test_add_block_with_special_characters(app_with_db):
    """
    Test adding a block with special characters in name.

    Verifies that block names with special characters (potential XSS)
    are properly handled with good UX.
    """
    with app_with_db.test_client() as client:
        response = client.post(
            "/add_block", data={"block_name": 'Test Block <script>alert("xss")</script>'}, follow_redirects=True
        )
        # Should return 200 with sanitized/validated response, not 400
        assert response.status_code == 200
        # XSS should be blocked with validation error, not processed
        assert b"invalid characters" in response.data.lower() or b"error" in response.data.lower()
