"""
Test suite for segment view functionality.

This module tests the segment view page and IP range calculation functionality.
"""

from app import db
from app.models import NetworkBlock, NetworkContainer


def test_segment_view_page_loads_with_ip_range(app_with_db):
    """
    Test that the segment view page loads and displays IP range correctly.

    Verifies that:
    - Segment view page loads successfully
    - IP range is calculated and displayed correctly
    - Network information is present
    """
    # Create a block
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    # Create a container with a known network
    container = NetworkContainer(block_id=block.id, name="Test Container", base_network="192.168.64.0/18")
    db.session.add(container)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get(f"/segment/container/{container.id}")
        assert response.status_code == 200

        # Check that the page contains the network information
        assert b"Network:" in response.data
        assert b"192.168.64.0/18" in response.data

        # Check that the IP range is displayed
        assert b"Range:" in response.data
        assert b"192.168.64.0 - 192.168.127.255" in response.data

        # Check that usage information is present
        assert b"Usage:" in response.data
        assert b"addresses" in response.data


def test_segment_view_with_different_network_sizes(app_with_db):
    """
    Test segment view with different network sizes to verify IP range calculation.
    """
    # Create a block
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    # Test cases: network and expected range
    test_cases = [
        ("10.0.0.0/24", "10.0.0.0 - 10.0.0.255"),
        ("172.16.0.0/16", "172.16.0.0 - 172.16.255.255"),
        ("192.168.1.0/28", "192.168.1.0 - 192.168.1.15"),
        ("10.10.10.0/30", "10.10.10.0 - 10.10.10.3"),
    ]

    for network, expected_range in test_cases:
        # Create container with test network
        container = NetworkContainer(block_id=block.id, name=f"Container for {network}", base_network=network)
        db.session.add(container)
        db.session.commit()

        with app_with_db.test_client() as client:
            response = client.get(f"/segment/container/{container.id}")
            assert response.status_code == 200

            # Check that the correct IP range is displayed
            assert expected_range.encode() in response.data

        # Clean up for next iteration
        db.session.delete(container)
        db.session.commit()


def test_segment_view_nonexistent_container(app_with_db):
    """
    Test segment view with nonexistent container ID.

    Verifies that:
    - Proper error handling for invalid container IDs
    - User is redirected appropriately
    """
    with app_with_db.test_client() as client:
        response = client.get("/segment/container/999", follow_redirects=True)
        assert response.status_code == 200
        # Should be redirected to main page with error message
        assert b"Container with ID 999 not found" in response.data or b"Error" in response.data


def test_segment_view_page_structure(app_with_db):
    """
    Test that the segment view page has proper structure and elements.
    """
    # Create test data
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    container = NetworkContainer(block_id=block.id, name="Test Container", base_network="10.0.0.0/8")
    db.session.add(container)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get(f"/segment/container/{container.id}")
        assert response.status_code == 200

        # Check for key page elements
        assert b"Segment View" in response.data
        assert b"Network Visualization" in response.data
        assert b"Test Block - Test Container" in response.data

        # Check for back button
        assert b"Back to IPAM" in response.data

        # Check that all three info items are present
        assert b"Network:" in response.data
        assert b"Range:" in response.data
        assert b"Usage:" in response.data
