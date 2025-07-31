"""
Shared test fixtures for the Outlan IPAM application.

This module provides common fixtures used across all test files,
ensuring consistent database setup and test data creation.
"""

import os

import pytest

from app import create_app, db
from app.models import NetworkBlock, Subnet


@pytest.fixture
def app_with_db():
    """Create Flask app with in-memory database for testing."""
    # Set environment variable for in-memory database
    os.environ["DB_PATH"] = ":memory:"

    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

    # Clean up environment variable
    if "DB_PATH" in os.environ:
        del os.environ["DB_PATH"]


@pytest.fixture
def client():
    """Create test client with in-memory database."""
    # Set environment variable for in-memory database
    os.environ["DB_PATH"] = ":memory:"

    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()

    # Clean up environment variable
    if "DB_PATH" in os.environ:
        del os.environ["DB_PATH"]


@pytest.fixture
def test_block(app_with_db):
    """Create a test block for subnet operations."""
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()
    return block


@pytest.fixture
def test_subnet(app_with_db, test_block):
    """Create a test subnet for testing."""
    subnet = Subnet(block_id=test_block.id, name="Test Subnet", cidr="192.168.1.0/24", vlan_id=100)
    db.session.add(subnet)
    db.session.commit()
    return subnet


@pytest.fixture
def test_data(app_with_db):
    """Create comprehensive test data for export and complex testing."""
    # Create blocks
    block1 = NetworkBlock(name="Production", position=1)
    block2 = NetworkBlock(name="Development", position=2)
    db.session.add_all([block1, block2])
    db.session.commit()

    # Create subnets
    subnets = [
        Subnet(block_id=block1.id, name="Prod Network", cidr="10.0.0.0/24", vlan_id=100),
        Subnet(block_id=block1.id, name="Prod DMZ", cidr="10.0.1.0/24", vlan_id=101),
        Subnet(block_id=block2.id, name="Dev Network", cidr="172.16.0.0/24", vlan_id=200),
        Subnet(block_id=block2.id, name="Dev Test", cidr="172.16.1.0/24", vlan_id=None),
    ]
    db.session.add_all(subnets)
    db.session.commit()

    return {"block1": block1, "block2": block2, "subnets": subnets}
