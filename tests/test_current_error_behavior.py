"""
Test to understand current error handling behavior.

This tests documents the current error handling patterns
to determine what needs improvement.
"""

import io


def test_current_form_validation_behavior(client):
    """Document current form validation error behavior."""

    # Test empty block name
    response = client.post("/add_block", data={"block_name": ""}, follow_redirects=True)
    print(f"Empty block name: Status {response.status_code}")
    print(f"Response data: {response.data[:200]}")

    # Test missing block name
    response = client.post("/add_block", data={}, follow_redirects=True)
    print(f"Missing block name: Status {response.status_code}")
    print(f"Response data: {response.data[:200]}")

    # Test invalid subnet data
    response = client.post(
        "/add_subnet",
        data={"name": "Test", "cidr": "invalid-cidr", "vlan_id": "abc", "block_id": "xyz"},
        follow_redirects=True,
    )
    print(f"Invalid subnet: Status {response.status_code}")
    print(f"Response data: {response.data[:200]}")


def test_current_csv_import_behavior(client):
    """Document current CSV import error behavior."""

    # Test empty CSV import
    response = client.post("/import_csv", data={"import_mode": "merge"}, follow_redirects=True)
    print(f"Missing CSV file: Status {response.status_code}")
    print(f"Response data: {response.data[:200]}")

    # Test invalid CSV data
    csv_content = "Invalid,Headers\nBad,Data"
    csv_file = io.BytesIO(csv_content.encode("utf-8"))
    response = client.post(
        "/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")}, follow_redirects=True
    )
    print(f"Invalid CSV headers: Status {response.status_code}")
    print(f"Response data: {response.data[:200]}")


def test_current_api_behavior(client):
    """Document current API error behavior."""

    # Test API with invalid data
    response = client.post("/api/blocks", json={"name": ""})
    print(f"API empty name: Status {response.status_code}")
    print(f"Response data: {response.data[:200]}")

    # Test API with missing data
    response = client.post("/api/blocks", json={})
    print(f"API missing data: Status {response.status_code}")
    print(f"Response data: {response.data[:200]}")


def test_current_route_error_behavior(client):
    """Document current route error behavior."""

    # Test invalid block ID
    response = client.get("/export_csv/invalid_id")
    print(f"Invalid block ID: Status {response.status_code}")
    print(f"Response data: {response.data[:200]}")

    # Test non-existent block ID
    response = client.get("/export_csv/99999")
    print(f"Non-existent block ID: Status {response.status_code}")
    print(f"Response data: {response.data[:200]}")
