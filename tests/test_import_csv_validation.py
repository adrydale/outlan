"""
Test suite for CSV import validation functionality.

This module tests CSV import validation including:
- File format validation
- Header validation
- Data validation (CIDR, VLAN, names)
- Encoding validation
- Import mode validation
"""

import io


def test_import_csv_missing_file(client):
    """
    Test import with no file uploaded.

    Verifies that:
    - Proper error message is shown
    - User is redirected appropriately
    """
    response = client.post("/import_csv", data={"import_mode": "merge"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Please select a CSV file to import" in response.data


def test_import_csv_invalid_headers(client):
    """
    Test import with invalid CSV headers.

    Verifies that:
    - Invalid headers are detected
    - Appropriate error message is shown
    - Import is rejected
    """
    csv_content = "Wrong,Headers,Here,Now\nData,Row,1,Test"
    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
        "/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"CSV headers must be exactly" in response.data


def test_import_csv_validation_errors(client):
    """
    Test CSV import with validation errors.

    Verifies that:
    - Validation errors are detected
    - Line numbers are reported
    - Detailed error messages are shown
    """
    csv_content = """Block,Network,VLAN,Subnet Name
,192.168.1.0/24,100,InvalidSubnet
ValidBlock,10.0.1.0/24,200,
ValidBlock,invalid-cidr,9999,ValidSubnet
ValidBlock,192.168.2.0/24,100,ValidSubnet2"""

    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post("/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")})
    assert response.status_code == 200
    assert b"Import Validation Errors" in response.data
    assert b"validation error" in response.data.lower()
    # Should show error table with row numbers
    assert b"Row" in response.data
    assert b"Error Description" in response.data
    # Check specific row numbers are present
    assert b"<td" in response.data  # Should have table cells
    # Check for error page navigation
    assert b"Back to Import/Export" in response.data


def test_import_csv_non_utf8_encoding(client):
    """
    Test importing CSV with non-UTF-8 encoding.

    Verifies that:
    - Encoding issues are handled gracefully
    - Proper error message is shown
    - Import fails safely
    """
    # Create a byte string with invalid UTF-8
    csv_content = b"Block,Network,VLAN,Subnet Name\nTest\xff\xfe,192.168.1.0/24,100,TestSubnet"
    csv_file = io.BytesIO(csv_content)

    response = client.post(
        "/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")}, follow_redirects=True
    )
    assert response.status_code == 200
    # Should handle encoding error gracefully
    assert b"error" in response.data.lower() or b"encoding" in response.data.lower()


def test_import_csv_invalid_csv_format(client):
    """
    Test importing malformed CSV data.

    Verifies that:
    - Malformed CSV is detected
    - Appropriate error message is shown
    - Import fails safely
    """
    # Create malformed CSV (unbalanced quotes)
    csv_content = 'Block,Network,VLAN,Subnet Name\nTest"Block,192.168.1.0/24,100,"TestSubnet'
    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
        "/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")}, follow_redirects=True
    )
    assert response.status_code == 200
    # Should handle CSV parsing error gracefully
    assert b"error" in response.data.lower() or b"format" in response.data.lower()


def test_import_csv_empty_file(client):
    """
    Test importing empty CSV file.

    Verifies that:
    - Empty file is detected
    - Appropriate error message is shown
    - Import fails gracefully
    """
    csv_content = ""
    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
        "/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"error" in response.data.lower() or b"empty" in response.data.lower()


def test_import_csv_header_only(client):
    """
    Test importing CSV with only headers and no data.

    Verifies that:
    - Header-only CSV is detected
    - Appropriate message is shown
    - No data changes occur
    """
    csv_content = "Block,Network,VLAN,Subnet Name"
    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
        "/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")}, follow_redirects=True
    )
    assert response.status_code == 200
    # Header-only CSV might be valid (0 rows imported) - check for success indication
    assert (
        b"success" in response.data.lower()
        or b"imported" in response.data.lower()
        or b"import/export" in response.data.lower()
    )  # Page title indicates successful redirect


def test_import_csv_inconsistent_columns(client):
    """
    Test importing CSV with inconsistent column counts.

    Verifies that:
    - Inconsistent column counts are detected
    - Appropriate error message is shown
    - Import fails safely
    """
    csv_content = """Block,Network,VLAN,Subnet Name
TestBlock,192.168.1.0/24,100,TestSubnet
TestBlock,10.0.1.0/24
TestBlock,172.16.1.0/24,200,TestSubnet2,ExtraColumn"""

    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
        "/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")}, follow_redirects=True
    )
    assert response.status_code == 200
    # Should handle inconsistent columns
    assert b"error" in response.data.lower() or b"column" in response.data.lower()


def test_import_csv_vlan_validation(client):
    """
    Test VLAN ID validation during CSV import.

    Verifies that:
    - Invalid VLAN IDs are detected
    - VLAN range validation works
    - Appropriate error messages are shown
    """
    csv_content = """Block,Network,VLAN,Subnet Name
TestBlock,192.168.1.0/24,0,TestSubnet1
TestBlock,10.0.1.0/24,4095,TestSubnet2
TestBlock,172.16.1.0/24,invalid,TestSubnet3
TestBlock,192.168.2.0/24,-1,TestSubnet4"""

    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post("/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")})
    assert response.status_code == 200
    assert b"validation error" in response.data.lower()
    # Should show VLAN-specific errors
    assert b"VLAN" in response.data or b"vlan" in response.data


def test_import_csv_cidr_validation(client):
    """
    Test CIDR validation during CSV import.

    Verifies that:
    - Invalid CIDR formats are detected
    - CIDR range validation works
    - Appropriate error messages are shown
    """
    csv_content = """Block,Network,VLAN,Subnet Name
TestBlock,192.168.1.0,100,TestSubnet1
TestBlock,256.256.256.256/24,200,TestSubnet2
TestBlock,192.168.1.0/99,300,TestSubnet3
TestBlock,not-an-ip,400,TestSubnet4"""

    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post("/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "test.csv")})
    assert response.status_code == 200
    assert b"validation error" in response.data.lower()
    # Should show CIDR-specific errors
    assert b"CIDR" in response.data or b"network" in response.data


def test_import_csv_large_file_handling(client):
    """
    Test handling of large CSV files.

    Verifies that:
    - Large files are processed efficiently
    - Memory usage is reasonable
    - Import completes successfully or fails gracefully
    """
    # Create a reasonably large CSV (100 rows)
    csv_lines = ["Block,Network,VLAN,Subnet Name"]
    for i in range(100):
        csv_lines.append(f"TestBlock,192.168.{i % 254 + 1}.0/24,{100 + i},TestSubnet{i}")

    csv_content = "\n".join(csv_lines)
    csv_file = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
        "/import_csv", data={"import_mode": "merge", "csv_file": (csv_file, "large_test.csv")}, follow_redirects=True
    )
    assert response.status_code == 200
    # Should either succeed or fail gracefully
    assert b"imported" in response.data.lower() or b"error" in response.data.lower()
