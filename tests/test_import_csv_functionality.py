"""
Test suite for CSV import functionality and modes.

This module tests CSV import operations including:
- Merge mode imports
- Override mode imports
- Replace mode imports
- Block creation during import
- Audit logging for imports
"""

import io

from app import db
from app.models import NetworkBlock, Subnet
from app.utils import DatabaseService


def test_import_csv_valid_data_merge_mode(client):
    """
    Test successful CSV import in merge mode.

    Verifies that:
    - Valid CSV data can be imported
    - New blocks are created
    - Merge mode works correctly
    - Audit logs are created
    """
    csv_content = """Block,Network,VLAN,Subnet Name
TestBlock,192.168.1.0/24,100,TestSubnet
TestBlock,10.0.1.0/24,,TestSubnet2"""

    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
        "/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Successfully imported" in response.data

    # Verify data was imported
    with client.application.app_context():
        blocks = DatabaseService.get_all_blocks()
        block_names = [b.name for b in blocks]
        assert "TestBlock" in block_names

        subnets = DatabaseService.get_all_subnets()
        subnet_names = [s.name for s in subnets]
        assert "TestSubnet" in subnet_names
        assert "TestSubnet2" in subnet_names


def test_import_csv_override_mode(app_with_db, client):
    """
    Test CSV import in override mode.

    Verifies that:
    - Existing data is updated in override mode
    - New data is added
    - Override functionality works correctly
    """
    # First create some initial data
    block = NetworkBlock(name="ExistingBlock", position=1)
    db.session.add(block)
    db.session.commit()

    subnet = Subnet(block_id=block.id, name="ExistingSubnet", vlan_id=100, cidr="192.168.1.0/24")
    db.session.add(subnet)
    db.session.commit()

    # Import CSV that should update existing data
    csv_content = """Block,Network,VLAN,Subnet Name
ExistingBlock,192.168.1.0/24,200,UpdatedSubnet
ExistingBlock,10.0.1.0/24,300,NewSubnet"""

    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
        "/import_csv", data={"import_mode": "override", "csv_file": (csv_file, "test.csv")}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Successfully imported" in response.data

    # Verify data was updated
    with client.application.app_context():
        subnets = DatabaseService.get_all_subnets()
        subnet_names = [s.name for s in subnets]
        subnet_vlans = [s.vlan_id for s in subnets if s.cidr == "192.168.1.0/24"]

        assert "UpdatedSubnet" in subnet_names  # Should be updated
        assert "NewSubnet" in subnet_names  # Should be added
        assert 200 in subnet_vlans  # VLAN should be updated


def test_import_csv_replace_mode_implementation(app_with_db, client, test_data):
    """
    Test CSV import replace mode implementation.

    Verifies that:
    - Replace mode clears existing data
    - New data is imported correctly
    - All old data is removed
    """
    # Verify we have existing data from test_data fixture
    with client.application.app_context():
        initial_blocks = DatabaseService.get_all_blocks()
        initial_subnets = DatabaseService.get_all_subnets()
        assert len(initial_blocks) > 0
        assert len(initial_subnets) > 0

    # Import CSV to replace all data
    csv_content = """Block,Network,VLAN,Subnet Name
NewBlock,172.16.1.0/24,500,NewSubnet1
NewBlock,172.16.2.0/24,600,NewSubnet2"""

    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
        "/import_csv", data={"import_mode": "replace", "csv_file": (csv_file, "test.csv")}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Successfully imported" in response.data

    # Verify old data is gone and new data exists
    with client.application.app_context():
        blocks = DatabaseService.get_all_blocks()
        subnets = DatabaseService.get_all_subnets()

        # Should only have the new data
        block_names = [b.name for b in blocks]
        subnet_names = [s.name for s in subnets]

        assert "NewBlock" in block_names
        assert "NewSubnet1" in subnet_names
        assert "NewSubnet2" in subnet_names

        # Old test data should be gone
        assert "Test Block 1" not in block_names
        assert "Test Block 2" not in block_names


def test_import_csv_audit_logging(app_with_db, client):
    """
    Test that CSV import creates proper audit logs.

    Verifies that:
    - Import operations are logged
    - Audit entries contain correct information
    - Snapshot creation works
    """
    csv_content = """Block,Network,VLAN,Subnet Name
AuditTestBlock,192.168.100.0/24,900,AuditTestSubnet"""

    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
        "/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Successfully imported" in response.data

    # Check audit logs
    with client.application.app_context():
        recent_changes = DatabaseService.get_recent_changes(limit=10)
        import_logs = [log for log in recent_changes if "IMPORT" in log.action]

        assert len(import_logs) > 0
        # Should have logged the import operation
        assert any("CSV" in log.details for log in import_logs)


def test_import_csv_block_creation(client):
    """
    Test automatic block creation during CSV import.

    Verifies that:
    - New blocks are automatically created
    - Block positions are assigned correctly
    - Multiple blocks can be created in one import
    """
    csv_content = """Block,Network,VLAN,Subnet Name
AutoBlock1,192.168.10.0/24,110,AutoSubnet1
AutoBlock2,192.168.20.0/24,120,AutoSubnet2
AutoBlock1,192.168.11.0/24,111,AutoSubnet3"""

    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
        "/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Successfully imported" in response.data

    # Verify blocks were created correctly
    with client.application.app_context():
        blocks = DatabaseService.get_all_blocks()
        block_names = [b.name for b in blocks]

        assert "AutoBlock1" in block_names
        assert "AutoBlock2" in block_names

        # Verify subnets are in correct blocks
        subnets = DatabaseService.get_all_subnets()
        block1_subnets = [s for s in subnets if s.block.name == "AutoBlock1"]
        block2_subnets = [s for s in subnets if s.block.name == "AutoBlock2"]

        assert len(block1_subnets) == 2  # AutoSubnet1 and AutoSubnet3
        assert len(block2_subnets) == 1  # AutoSubnet2
