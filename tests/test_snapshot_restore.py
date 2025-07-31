import json

from app import db
from app.models import ChangeLog, NetworkBlock, Subnet

# Use the app_with_db fixture from conftest.py instead of defining our own


# Route Testing
def test_restore_snapshot_route_exists(app_with_db):
    """Test that the restore snapshot route exists and is accessible"""
    # This should return 404 for non-existent snapshot, but route should exist
    with app_with_db.test_client() as client:
        response = client.post("/restore_snapshot/999")
        assert response.status_code in [404, 400, 500]  # Either snapshot not found or error


def test_restore_confirmation_route_exists(app_with_db):
    """Test that the restore confirmation route exists"""
    with app_with_db.test_client() as client:
        response = client.get("/restore_confirmation/999")
        assert response.status_code in [404, 500]  # Either snapshot not found or error


# Core Restore Functionality
def test_restore_snapshot_with_valid_data(app_with_db):
    """Test restoring a snapshot with valid data"""
    from app.utils import DatabaseService

    # Create test data
    block = NetworkBlock(name="Test Block", position=1)
    db.session.add(block)
    db.session.commit()

    subnet = Subnet(block_id=block.id, name="Test Subnet", cidr="192.168.1.0/24", vlan_id=100)
    db.session.add(subnet)
    db.session.commit()

    # Create a snapshot
    snapshot_data = DatabaseService.export_all_data()
    snapshot = ChangeLog(
        action="SNAPSHOT", block="Test Block", details="Test snapshot", content=json.dumps(snapshot_data)
    )
    db.session.add(snapshot)
    db.session.commit()

    # Test restore functionality
    with app_with_db.test_client() as client:
        response = client.post(f"/restore_snapshot/{snapshot.id}")
        assert response.status_code == 302  # Redirect to confirmation page


def test_restore_snapshot_with_invalid_id(app_with_db):
    """Test restoring a snapshot with invalid ID"""
    with app_with_db.test_client() as client:
        response = client.post("/restore_snapshot/999")
        assert response.status_code == 404


def test_restore_snapshot_with_missing_content(app_with_db):
    """Test restoring a snapshot with missing content"""
    # Create snapshot without content
    snapshot = ChangeLog(action="SNAPSHOT", block="Test Block", details="Test snapshot", content=None)
    db.session.add(snapshot)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(f"/restore_snapshot/{snapshot.id}")
        assert response.status_code == 404  # Snapshot not found because it has no content


def test_restore_snapshot_with_corrupted_data(app_with_db):
    """Test restoring a snapshot with corrupted JSON data"""
    # Create snapshot with invalid JSON
    snapshot = ChangeLog(action="SNAPSHOT", block="Test Block", details="Test snapshot", content="invalid json data")
    db.session.add(snapshot)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.post(f"/restore_snapshot/{snapshot.id}")
        assert response.status_code == 500


# Confirmation Page Testing
def test_restore_confirmation_page_loads(app_with_db):
    """Test that the restore confirmation page loads correctly"""
    # Create a snapshot
    snapshot = ChangeLog(
        action="SNAPSHOT",
        block="Test Block",
        details="Test snapshot",
        content=json.dumps({"blocks": [], "subnets": []}),
    )
    db.session.add(snapshot)
    db.session.commit()

    with app_with_db.test_client() as client:
        response = client.get(f"/restore_confirmation/{snapshot.id}")
        assert response.status_code == 200
        assert b"Snapshot Restored" in response.data
        assert str(snapshot.id).encode() in response.data


def test_restore_confirmation_with_invalid_id(app_with_db):
    """Test restore confirmation page with invalid snapshot ID"""
    with app_with_db.test_client() as client:
        response = client.get("/restore_confirmation/999")
        assert response.status_code == 404


# Database Service Testing
def test_database_service_export_import_functionality(app_with_db):
    """Test the DatabaseService export and import functionality"""
    from app.utils import DatabaseService

    # Create test data
    block1 = NetworkBlock(name="Block 1", position=1)
    block2 = NetworkBlock(name="Block 2", position=2)
    db.session.add_all([block1, block2])
    db.session.commit()

    subnet1 = Subnet(block_id=block1.id, name="Subnet 1", cidr="192.168.1.0/24", vlan_id=100)
    subnet2 = Subnet(block_id=block2.id, name="Subnet 2", cidr="10.0.0.0/16", vlan_id=200)
    db.session.add_all([subnet1, subnet2])
    db.session.commit()

    # Test export functionality
    exported_data = DatabaseService.export_all_data()
    assert "blocks" in exported_data
    assert "subnets" in exported_data
    assert len(exported_data["blocks"]) == 2
    assert len(exported_data["subnets"]) == 2

    # Test import functionality
    # First, clear the database
    Subnet.query.delete()
    NetworkBlock.query.delete()
    db.session.commit()

    # Import the exported data
    success = DatabaseService.import_data(exported_data)
    assert success is True

    # Verify the data was imported correctly
    blocks = NetworkBlock.query.all()
    subnets = Subnet.query.all()
    assert len(blocks) == 2
    assert len(subnets) == 2

    # Check specific data
    block_names = [block.name for block in blocks]
    assert "Block 1" in block_names
    assert "Block 2" in block_names

    subnet_cidrs = [subnet.cidr for subnet in subnets]
    assert "192.168.1.0/24" in subnet_cidrs
    assert "10.0.0.0/16" in subnet_cidrs


# Advanced Restore Testing
def test_restore_creates_new_snapshot(app_with_db):
    """Test that restoring a snapshot creates a new snapshot of the restored state"""
    from app.utils import DatabaseService

    # Create initial data
    block = NetworkBlock(name="Original Block", position=1)
    db.session.add(block)
    db.session.commit()

    subnet = Subnet(block_id=block.id, name="Original Subnet", cidr="192.168.1.0/24")
    db.session.add(subnet)
    db.session.commit()

    # Create initial snapshot
    initial_data = DatabaseService.export_all_data()
    initial_snapshot = ChangeLog(
        action="SNAPSHOT", block="Original Block", details="Initial snapshot", content=json.dumps(initial_data)
    )
    db.session.add(initial_snapshot)
    db.session.commit()

    # Modify data
    block.name = "Modified Block"
    subnet.name = "Modified Subnet"
    db.session.commit()

    # Restore to initial snapshot
    with app_with_db.test_client() as client:
        response = client.post(f"/restore_snapshot/{initial_snapshot.id}")
        assert response.status_code == 302

    # Check that a new RESTORE snapshot was created
    restore_snapshots = ChangeLog.query.filter_by(action="RESTORE").all()
    assert len(restore_snapshots) == 1

    # Verify the restored data matches the original
    restored_data = json.loads(restore_snapshots[0].content)
    assert len(restored_data["blocks"]) == 1
    assert len(restored_data["subnets"]) == 1
    assert restored_data["blocks"][0]["name"] == "Original Block"
    assert restored_data["subnets"][0]["name"] == "Original Subnet"


def test_restore_with_complex_data_structure(app_with_db):
    """Test restore functionality with complex data structure including VLANs and positions"""
    from app.utils import DatabaseService

    # Create complex test data
    block1 = NetworkBlock(name="Production", position=1, collapsed=False)
    block2 = NetworkBlock(name="Development", position=2, collapsed=True)
    db.session.add_all([block1, block2])
    db.session.commit()

    subnets = [
        Subnet(block_id=block1.id, name="Prod Network", cidr="10.0.0.0/24", vlan_id=100),
        Subnet(block_id=block1.id, name="Prod DMZ", cidr="10.0.1.0/24", vlan_id=101),
        Subnet(block_id=block2.id, name="Dev Network", cidr="172.16.0.0/24", vlan_id=200),
        Subnet(block_id=block2.id, name="Dev Test", cidr="172.16.1.0/24", vlan_id=None),
    ]
    db.session.add_all(subnets)
    db.session.commit()

    # Create snapshot
    snapshot_data = DatabaseService.export_all_data()
    snapshot = ChangeLog(
        action="SNAPSHOT", block="Complex Data", details="Complex data snapshot", content=json.dumps(snapshot_data)
    )
    db.session.add(snapshot)
    db.session.commit()

    # Test restore
    with app_with_db.test_client() as client:
        response = client.post(f"/restore_snapshot/{snapshot.id}")
        assert response.status_code == 302

    # Verify restore created new snapshot
    restore_snapshots = ChangeLog.query.filter_by(action="RESTORE").all()
    assert len(restore_snapshots) == 1

    # Verify complex data was preserved
    restored_data = json.loads(restore_snapshots[0].content)
    assert len(restored_data["blocks"]) == 2
    assert len(restored_data["subnets"]) == 4

    # Check specific complex data
    block_names = [block["name"] for block in restored_data["blocks"]]
    assert "Production" in block_names
    assert "Development" in block_names

    # Check VLAN data
    vlan_ids = [subnet.get("vlan_id") for subnet in restored_data["subnets"]]
    assert 100 in vlan_ids
    assert 101 in vlan_ids
    assert 200 in vlan_ids
    assert None in vlan_ids  # Subnet without VLAN
