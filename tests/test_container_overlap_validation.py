"""
Test suite for container network overlap validation.

This module tests the container network overlap checking functionality
to ensure containers can overlap between different blocks but not within the same block.
"""

from app import db
from app.models import NetworkBlock, NetworkContainer
from app.utils.validation import check_overlapping_container_networks


def test_container_overlap_allowed_between_different_blocks(app_with_db):
    """
    Test that container networks can overlap between different blocks.

    Verifies that:
    - Same network can exist in different blocks
    - No overlap error is returned for different blocks
    """
    # Create two blocks
    block1 = NetworkBlock(name="Block1", position=1)
    block2 = NetworkBlock(name="Block2", position=2)
    db.session.add_all([block1, block2])
    db.session.commit()

    # Create container in block1 with network 10.0.0.0/16
    container1 = NetworkContainer(block_id=block1.id, name="Container1", base_network="10.0.0.0/16")
    db.session.add(container1)
    db.session.commit()

    # Test adding the same network to block2 - should be allowed
    is_overlapping, existing_container = check_overlapping_container_networks("10.0.0.0/16", block2.id)

    assert not is_overlapping, "Container networks should be allowed to overlap between different blocks"
    assert existing_container is None


def test_container_overlap_prevented_within_same_block(app_with_db):
    """
    Test that container networks cannot overlap within the same block.

    Verifies that:
    - Overlapping networks within same block are detected
    - Proper error information is returned
    """
    # Create one block
    block1 = NetworkBlock(name="Block1", position=1)
    db.session.add(block1)
    db.session.commit()

    # Create container in block1 with network 10.0.0.0/16
    container1 = NetworkContainer(block_id=block1.id, name="Container1", base_network="10.0.0.0/16")
    db.session.add(container1)
    db.session.commit()

    # Test adding overlapping network to same block - should be prevented
    is_overlapping, existing_container = check_overlapping_container_networks(
        "10.0.1.0/24", block1.id  # This overlaps with 10.0.0.0/16
    )

    assert is_overlapping, "Overlapping container networks should be prevented within the same block"
    assert existing_container is not None
    assert existing_container["name"] == "Container1"
    assert existing_container["base_network"] == "10.0.0.0/16"
    assert existing_container["block_id"] == block1.id


def test_container_overlap_exact_same_network_within_block(app_with_db):
    """
    Test that exact same container network cannot be added within the same block.
    """
    # Create one block
    block1 = NetworkBlock(name="Block1", position=1)
    db.session.add(block1)
    db.session.commit()

    # Create container in block1 with network 192.168.1.0/24
    container1 = NetworkContainer(block_id=block1.id, name="Container1", base_network="192.168.1.0/24")
    db.session.add(container1)
    db.session.commit()

    # Test adding exact same network to same block - should be prevented
    is_overlapping, existing_container = check_overlapping_container_networks("192.168.1.0/24", block1.id)

    assert is_overlapping, "Exact same container network should be prevented within the same block"
    assert existing_container is not None
    assert existing_container["name"] == "Container1"


def test_container_overlap_non_overlapping_networks_same_block(app_with_db):
    """
    Test that non-overlapping container networks are allowed within the same block.
    """
    # Create one block
    block1 = NetworkBlock(name="Block1", position=1)
    db.session.add(block1)
    db.session.commit()

    # Create container in block1 with network 192.168.1.0/24
    container1 = NetworkContainer(block_id=block1.id, name="Container1", base_network="192.168.1.0/24")
    db.session.add(container1)
    db.session.commit()

    # Test adding non-overlapping network to same block - should be allowed
    is_overlapping, existing_container = check_overlapping_container_networks(
        "172.16.0.0/16", block1.id  # Does not overlap with 192.168.1.0/24
    )

    assert not is_overlapping, "Non-overlapping container networks should be allowed within the same block"
    assert existing_container is None


def test_container_overlap_exclude_self_when_updating(app_with_db):
    """
    Test that when updating a container, it excludes itself from overlap checking.
    """
    # Create one block
    block1 = NetworkBlock(name="Block1", position=1)
    db.session.add(block1)
    db.session.commit()

    # Create container in block1 with network 10.0.0.0/16
    container1 = NetworkContainer(block_id=block1.id, name="Container1", base_network="10.0.0.0/16")
    db.session.add(container1)
    db.session.commit()

    # Test updating container to overlapping network but excluding itself - should be allowed
    is_overlapping, existing_container = check_overlapping_container_networks(
        "10.0.1.0/24", block1.id, exclude_id=container1.id
    )

    assert not is_overlapping, "Container should be able to update to overlapping network when excluding itself"
    assert existing_container is None


def test_container_overlap_multiple_containers_different_blocks(app_with_db):
    """
    Test complex scenario with multiple containers across different blocks.
    """
    # Create three blocks
    block1 = NetworkBlock(name="Block1", position=1)
    block2 = NetworkBlock(name="Block2", position=2)
    block3 = NetworkBlock(name="Block3", position=3)
    db.session.add_all([block1, block2, block3])
    db.session.commit()

    # Create containers with same network in different blocks
    container1 = NetworkContainer(block_id=block1.id, name="Container1", base_network="10.0.0.0/8")
    container2 = NetworkContainer(block_id=block2.id, name="Container2", base_network="10.0.0.0/8")
    db.session.add_all([container1, container2])
    db.session.commit()

    # Test adding same network to third block - should be allowed
    is_overlapping, existing_container = check_overlapping_container_networks("10.0.0.0/8", block3.id)

    assert not is_overlapping, "Same network should be allowed across multiple different blocks"
    assert existing_container is None

    # Test adding overlapping network to block1 - should be prevented
    is_overlapping, existing_container = check_overlapping_container_networks(
        "10.1.0.0/16", block1.id  # Overlaps with existing 10.0.0.0/8 in block1
    )

    assert is_overlapping, "Overlapping network should be prevented within block1"
    assert existing_container is not None
    assert existing_container["block_id"] == block1.id
