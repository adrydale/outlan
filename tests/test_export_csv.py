"""
Test suite for CSV export functionality.

This module tests CSV export operations including:
- Export page functionality
- CSV template downloads
- Block-specific exports
- Export validation and error handling
"""

import csv
import io


def test_import_export_page_loads(client):
    """
    Test that the import/export page loads successfully.

    Verifies that:
    - Page loads without error
    - Contains expected form elements
    - Has proper navigation
    """
    response = client.get("/import_export")
    assert response.status_code == 200
    assert b"Import/Export Networks" in response.data
    assert b"Export Networks" in response.data
    assert b"Import Networks" in response.data
    assert b"Download Example CSV" in response.data


def test_download_example_csv(client):
    """
    Test downloading the example CSV template.

    Verifies that:
    - Example CSV can be downloaded
    - Has correct headers
    - Contains example data
    - Is properly formatted
    """
    response = client.get("/download_example_csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["Content-Type"]
    assert "example_import_template.csv" in response.headers["Content-Disposition"]

    # Parse CSV content
    csv_data = response.data.decode("utf-8")
    csv_reader = csv.reader(io.StringIO(csv_data))
    rows = list(csv_reader)

    # Check structure
    assert len(rows) >= 2  # Header + example data
    expected_headers = ["Block", "Network", "VLAN", "Subnet Name"]
    assert rows[0] == expected_headers

    # Check example data
    data_rows = rows[1:]
    assert len(data_rows) >= 1
    assert "Production" in data_rows[0][0]  # First example block


def test_export_all_csv_no_block(app_with_db):
    """
    Test exporting all data to CSV without specific block.

    Verifies that:
    - Export returns all network data
    - CSV format is correct
    - Headers are included
    - All blocks are represented
    """
    # Create test data in the same app context
    from app import db
    from app.models import NetworkBlock, Subnet

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

    # Test the export
    with app_with_db.test_client() as client:
        response = client.get("/export_all_csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers["Content-Type"]
        assert "all_networks_export" in response.headers["Content-Disposition"]

        # Parse CSV content
        csv_data = response.data.decode("utf-8")
        csv_reader = csv.reader(io.StringIO(csv_data))
        rows = list(csv_reader)

        # Check structure
        assert len(rows) > 1  # Header + data rows
        expected_headers = ["Block", "Network", "VLAN", "Subnet Name"]
        assert rows[0] == expected_headers

        # Check data content
        data_rows = rows[1:]
        assert len(data_rows) >= 4  # At least 4 subnets from test_data

        # Verify test_data content is present
        block_names = [row[0] for row in data_rows]
        assert "Production" in block_names
        assert "Development" in block_names


def test_export_specific_block_csv(app_with_db):
    """
    Test exporting specific block data to CSV.

    Verifies that:
    - Block-specific export works
    - Only requested block data is returned
    - CSV format is maintained
    - Proper filename is generated
    """
    # Create test data in the same app context
    from app import db
    from app.models import NetworkBlock, Subnet

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
    ]
    db.session.add_all(subnets)
    db.session.commit()

    # Test the export
    with app_with_db.test_client() as client:
        response = client.get(f"/export_csv/{block1.id}")
        assert response.status_code == 200
        assert "text/csv" in response.headers["Content-Type"]
        assert f"{block1.name}_subnets.csv" in response.headers["Content-Disposition"]

        # Parse CSV content
        csv_data = response.data.decode("utf-8")
        csv_reader = csv.reader(io.StringIO(csv_data))
        rows = list(csv_reader)

        # Check structure
        assert len(rows) > 1  # Header + data rows
        expected_headers = ["Block", "Network", "VLAN", "Subnet Name"]
        assert rows[0] == expected_headers

        # Check that only the requested block is present
        data_rows = rows[1:]
        assert len(data_rows) == 2  # Only 2 subnets for Production block
        for row in data_rows:
            assert row[0] == "Production"  # All rows should be from this block


def test_export_invalid_block_id(client):
    """
    Test exporting with invalid block ID.

    Verifies that:
    - Invalid block ID returns appropriate error
    - Error message is clear
    - HTTP status code is correct
    """
    response = client.get("/export_csv/999999")  # Non-existent block ID
    assert response.status_code == 404  # Block not found returns 404
    assert b"error" in response.data.lower() or b"not found" in response.data.lower()
