"""
Critical error scenario testing for application stability.

This module tests critical error conditions that must not cause 500 errors:
- Form validation failures
- Database constraint violations
- File operation errors
- Network timeout simulations
- Memory pressure scenarios
"""

import io
from unittest.mock import patch

from app import db
from app.models import NetworkBlock


class TestCriticalFormValidationErrors:
    """Test that form validation errors never cause 500 errors."""

    def test_all_form_fields_empty_or_invalid(self, client):
        """Test submitting completely invalid form data."""
        # Form validation errors (should return 200 with error message)
        form_validation_errors = [
            ("/add_block", {"block_name": ""}),
            ("/add_block", {"block_name": None}),
            ("/add_block", {}),  # No data at all
        ]

        for endpoint, data in form_validation_errors:
            response = client.post(endpoint, data=data, follow_redirects=True)
            # Form validation errors should return 200 with error message
            assert response.status_code == 200, f"Failed for {endpoint} with data {data}"
            assert (
                b"error" in response.data.lower()
                or b"invalid" in response.data.lower()
                or b"cannot be empty" in response.data.lower()
            )

        # Resource not found errors (should return 400/404)
        resource_errors = [
            ("/add_subnet", {"name": "", "cidr": "", "vlan_id": "", "block_id": ""}),  # Empty block_id
            (
                "/add_subnet",
                {"name": "Test", "cidr": "invalid", "vlan_id": "abc", "block_id": "xyz"},
            ),  # Invalid block_id
            ("/add_subnet", {}),  # No data at all
        ]

        for endpoint, data in resource_errors:
            response = client.post(endpoint, data=data, follow_redirects=True)
            # Resource errors should return 400 (client error) but not 500
            assert response.status_code in [
                200,
                400,
                404,
            ], f"Failed for {endpoint} with data {data} - got {response.status_code}"
            assert response.status_code != 500  # Must never return server error

    def test_concurrent_form_submissions(self, app_with_db):
        """Test rapid concurrent form submissions don't cause crashes."""
        # Create test block first
        from app import db
        from app.models import NetworkBlock

        block = NetworkBlock(name="ConcurrentTest", position=1)
        db.session.add(block)
        db.session.commit()
        block_id = block.id

        # Simulate rapid submissions
        with app_with_db.test_client() as client:
            responses = []
            for i in range(10):
                response = client.post(
                    "/add_subnet",
                    data={
                        "block_id": block_id,
                        "name": f"ConcurrentSubnet{i}",
                        "cidr": f"192.168.{i}.0/24",
                        "vlan_id": str(100 + i),
                    },
                    follow_redirects=True,
                )
                responses.append(response)

            # All should return 200 (success or handled error)
            for i, response in enumerate(responses):
                assert response.status_code == 200, f"Request {i} failed with status {response.status_code}"

    def test_form_submission_with_special_characters(self, client):
        """Test form submissions with special characters and unicode."""
        special_character_tests = [
            "Block\x00WithNull",  # Null bytes
            "Block\r\nWithNewlines",  # Control characters
            "Block'WithQuotes\"",  # Quote characters
            "Block<script>alert(1)</script>",  # HTML/JS
            "测试块名称",  # Unicode characters
            "🌟🚀💻",  # Emojis
            "Block\t\t\tWithTabs",  # Tabs
        ]

        for special_name in special_character_tests:
            response = client.post("/add_block", data={"block_name": special_name}, follow_redirects=True)
            # Must handle gracefully, no crashes
            assert response.status_code == 200, f"Failed for special name: {special_name}"


class TestDatabaseConstraintHandling:
    """Test database constraint violations are handled properly."""

    def test_duplicate_key_violations(self, app_with_db, client):
        """Test handling of duplicate key constraint violations."""
        # Create initial block
        response1 = client.post("/add_block", data={"block_name": "UniqueBlock"}, follow_redirects=True)
        assert response1.status_code == 200

        # Try to create duplicate
        response2 = client.post("/add_block", data={"block_name": "UniqueBlock"}, follow_redirects=True)
        assert response2.status_code == 200  # Should handle gracefully
        assert b"already exists" in response2.data.lower() or b"duplicate" in response2.data.lower()

    def test_foreign_key_constraint_violations(self, client):
        """Test handling of foreign key constraint violations."""
        # Try to create subnet with non-existent block
        response = client.post(
            "/add_subnet",
            data={
                "block_id": 99999,  # Non-existent block
                "name": "TestSubnet",
                "cidr": "192.168.1.0/24",
                "vlan_id": "100",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200  # Should handle gracefully
        assert b"error" in response.data.lower() or b"not found" in response.data.lower()

    def test_check_constraint_violations(self, app_with_db, client):
        """Test handling of check constraint violations."""
        # Create test block
        with app_with_db.app_context():
            block = NetworkBlock(name="ConstraintTest", position=1)
            db.session.add(block)
            db.session.commit()
            block_id = block.id

        # Try invalid VLAN IDs
        invalid_vlans = ["0", "4095", "-1", "99999"]
        for invalid_vlan in invalid_vlans:
            response = client.post(
                "/add_subnet",
                data={"block_id": block_id, "name": "TestSubnet", "cidr": "192.168.1.0/24", "vlan_id": invalid_vlan},
                follow_redirects=True,
            )

            assert response.status_code == 200, f"Failed for VLAN {invalid_vlan}"
            assert b"error" in response.data.lower() or b"invalid" in response.data.lower()


class TestFileOperationErrorHandling:
    """Test file operation error handling."""

    def test_csv_import_with_corrupted_files(self, client):
        """Test handling of corrupted CSV files."""
        corrupted_files = [
            b"\x00\x01\x02\x03",  # Binary data
            b"\xff\xfe\xfd",  # Invalid UTF-8
            b'Block,Network,VLAN,Name\n"Unclosed quote',  # Malformed CSV
            b"",  # Empty file
        ]

        for corrupted_data in corrupted_files:
            csv_file = io.BytesIO(corrupted_data)
            response = client.post(
                "/import_csv",
                data={"import_mode": "merge", "csv_file": (csv_file, "corrupted.csv")},
                follow_redirects=True,
            )

            assert response.status_code == 200  # Should handle gracefully
            assert b"error" in response.data.lower() or b"invalid" in response.data.lower()

    def test_file_upload_without_file(self, client):
        """Test file upload endpoints without actual files."""
        response = client.post(
            "/import_csv",
            data={
                "import_mode": "merge"
                # No file provided
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"file" in response.data.lower() or b"error" in response.data.lower()

    def test_file_upload_with_wrong_content_type(self, client):
        """Test file uploads with wrong content types."""
        # Upload text file as CSV
        text_file = io.BytesIO(b"This is not a CSV file")
        response = client.post(
            "/import_csv", data={"import_mode": "merge", "csv_file": (text_file, "notcsv.csv")}, follow_redirects=True
        )

        assert response.status_code == 200
        # Should handle gracefully


class TestNetworkValidationCriticalErrors:
    """Test critical network validation scenarios."""

    def test_cidr_overflow_conditions(self, app_with_db, client):
        """Test CIDR formats that could cause overflow or parsing errors."""
        # Create test block
        with app_with_db.app_context():
            block = NetworkBlock(name="CIDRTest", position=1)
            db.session.add(block)
            db.session.commit()
            block_id = block.id

        problematic_cidrs = [
            "999.999.999.999/24",  # Invalid IP ranges
            "192.168.1.0/999",  # Invalid subnet mask
            "192.168.1.0/-5",  # Negative subnet mask
            "192.168.1.0/abc",  # Non-numeric mask
            "192.168.1.0/24/extra",  # Extra components
            "192.168.1.0//24",  # Double slash
            "",  # Empty CIDR
            " ",  # Whitespace only
        ]

        for problematic_cidr in problematic_cidrs:
            response = client.post(
                "/add_subnet",
                data={
                    "block_id": block_id,
                    "name": f'Test_{problematic_cidr.replace("/", "_")}',
                    "cidr": problematic_cidr,
                    "vlan_id": "100",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200, f"Failed for CIDR: {problematic_cidr}"
            assert b"error" in response.data.lower() or b"invalid" in response.data.lower()

    def test_vlan_boundary_conditions(self, app_with_db, client):
        """Test VLAN ID boundary conditions."""
        # Create test block
        with app_with_db.app_context():
            block = NetworkBlock(name="VLANTest", position=1)
            db.session.add(block)
            db.session.commit()
            block_id = block.id

        boundary_vlans = [
            "0",  # Below minimum
            "4095",  # Above maximum
            "1.5",  # Decimal
            "1e10",  # Scientific notation
            "0x64",  # Hexadecimal
            "  100  ",  # Whitespace
            "+100",  # Plus sign
        ]

        for boundary_vlan in boundary_vlans:
            response = client.post(
                "/add_subnet",
                data={
                    "block_id": block_id,
                    "name": f"VLAN_Test_{boundary_vlan}",
                    "cidr": "192.168.1.0/24",
                    "vlan_id": boundary_vlan,
                },
                follow_redirects=True,
            )

            # Most should be invalid, but must not crash
            assert response.status_code == 200, f"Failed for VLAN: {boundary_vlan}"


class TestResourceExhaustionSimulation:
    """Test behavior under simulated resource exhaustion."""

    def test_memory_pressure_simulation(self, client):
        """Test behavior under memory pressure (simulated)."""
        # Create large form data to simulate memory pressure
        large_name = "A" * 10000  # Large but not extreme

        response = client.post("/add_block", data={"block_name": large_name}, follow_redirects=True)
        assert response.status_code == 200  # Should handle gracefully

    def test_database_timeout_simulation(self, app_with_db, client):
        """Test database timeout handling."""
        with patch("app.models.db.session.commit", side_effect=TimeoutError("Database timeout")):
            response = client.post("/add_block", data={"block_name": "TimeoutTest"}, follow_redirects=True)
            assert response.status_code == 200  # Should handle timeout gracefully
            assert b"error" in response.data.lower() or b"timeout" in response.data.lower()


class TestApplicationIntegrity:
    """Test overall application integrity under stress."""

    def test_mixed_valid_invalid_operations(self, app_with_db, client):
        """Test mixing valid and invalid operations."""
        operations = [
            ("POST", "/add_block", {"block_name": "ValidBlock"}),
            ("POST", "/add_block", {"block_name": ""}),  # Invalid
            ("POST", "/add_block", {"block_name": "AnotherValidBlock"}),
            ("GET", "/export_csv/999999", {}),  # Invalid block ID
            ("GET", "/", {}),  # Valid page
        ]

        for method, endpoint, data in operations:
            if method == "POST":
                response = client.post(endpoint, data=data, follow_redirects=True)
            else:
                response = client.get(endpoint, follow_redirects=True)

            # Should not return 500 (server error), but 404 is acceptable for missing resources
            assert response.status_code != 500, f"Server error for {method} {endpoint}"
            assert response.status_code in [
                200,
                404,
            ], f"Unexpected status {response.status_code} for {method} {endpoint}"

    def test_application_state_consistency(self, app_with_db):
        """Test that application state remains consistent after errors."""
        with app_with_db.test_client() as client:
            # Create valid block
            response1 = client.post("/add_block", data={"block_name": "ConsistencyTest"}, follow_redirects=True)
            assert response1.status_code == 200

            # Try invalid operation
            response2 = client.post("/add_block", data={"block_name": ""}, follow_redirects=True)
            assert response2.status_code == 200

            # Verify application is still functional
            response3 = client.get("/")
            assert response3.status_code == 200

        # Verify database consistency (in same app context)
        from app.models import NetworkBlock

        blocks = NetworkBlock.query.all()
        assert len(blocks) >= 1  # At least our valid block should exist
