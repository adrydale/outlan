"""
Network-specific edge case and error scenario testing.

This module tests network-related edge cases including:
- Complex network overlaps
- VLAN boundary conditions
- IP address edge cases
- Subnet calculation errors
- Container network validation
"""

import pytest

from app import db
from app.models import NetworkBlock, NetworkContainer, Subnet
from app.utils.validation import (
    check_duplicate_vlan_in_block,
    check_overlapping_cidr_in_block,
    check_overlapping_container_networks,
)


class TestComplexNetworkOverlaps:
    """Test complex network overlap scenarios."""

    def test_multiple_subnet_overlaps(self, app_with_db):
        """Test detection of overlaps with multiple existing subnets."""
        # Create test block
        block = NetworkBlock(name="OverlapTest", position=1)
        db.session.add(block)
        db.session.commit()

        # Create multiple existing subnets
        existing_subnets = [
            ("192.168.1.0/24", 100),
            ("192.168.2.0/24", 200),
            ("192.168.3.0/24", 300),
            ("10.0.0.0/16", 400),
        ]

        for cidr, vlan in existing_subnets:
            subnet = Subnet(block_id=block.id, name=f"Subnet-{vlan}", cidr=cidr, vlan_id=vlan)
            db.session.add(subnet)
        db.session.commit()

        # Test various overlapping scenarios
        overlap_tests = [
            ("192.168.0.0/16", True),  # Supernet overlap
            ("192.168.1.128/25", True),  # Subnet overlap
            ("192.168.1.0/24", True),  # Exact match
            ("192.168.4.0/24", False),  # No overlap
            ("172.16.0.0/16", False),  # Different range
            ("10.0.1.0/24", True),  # Overlap with 10.0.0.0/16
        ]

        for test_cidr, should_overlap in overlap_tests:
            has_overlap, _ = check_overlapping_cidr_in_block(test_cidr, block.id)
            assert has_overlap == should_overlap, f"Failed for {test_cidr}"

    def test_adjacent_networks_no_overlap(self, app_with_db):
        """Test that adjacent networks don't trigger false overlaps."""
        block = NetworkBlock(name="AdjacentTest", position=1)
        db.session.add(block)
        db.session.commit()

        # Create base subnet
        subnet = Subnet(block_id=block.id, name="BaseSubnet", cidr="192.168.1.0/24", vlan_id=100)
        db.session.add(subnet)
        db.session.commit()

        # Test adjacent networks (should not overlap)
        adjacent_networks = [
            "192.168.0.0/24",  # Previous subnet
            "192.168.2.0/24",  # Next subnet
            "192.168.1.0/25",  # First half (overlaps)
            "192.168.1.128/25",  # Second half (overlaps)
        ]

        expected_overlaps = [False, False, True, True]

        for cidr, should_overlap in zip(adjacent_networks, expected_overlaps):
            has_overlap, _ = check_overlapping_cidr_in_block(cidr, block.id)
            assert has_overlap == should_overlap, f"Failed for {cidr}"

    def test_cross_block_overlap_handling(self, app_with_db):
        """Test that overlaps are properly scoped to blocks."""
        # Create two blocks
        block1 = NetworkBlock(name="Block1", position=1)
        block2 = NetworkBlock(name="Block2", position=2)
        db.session.add_all([block1, block2])
        db.session.commit()

        # Add same network to both blocks (should be allowed)
        subnet1 = Subnet(block_id=block1.id, name="Subnet1", cidr="192.168.1.0/24", vlan_id=100)
        subnet2 = Subnet(block_id=block2.id, name="Subnet2", cidr="192.168.1.0/24", vlan_id=100)
        db.session.add_all([subnet1, subnet2])
        db.session.commit()

        # Test overlap detection within each block
        has_overlap_block1, _ = check_overlapping_cidr_in_block("192.168.1.0/24", block1.id)
        has_overlap_block2, _ = check_overlapping_cidr_in_block("192.168.1.0/24", block2.id)

        assert has_overlap_block1  # Should detect overlap in block1
        assert has_overlap_block2  # Should detect overlap in block2

        # Test adding to different block (should work)
        has_overlap_cross, _ = check_overlapping_cidr_in_block("192.168.1.0/24", block1.id, exclude_id=subnet2.id)
        assert has_overlap_cross  # Still overlaps within block1


class TestVLANBoundaryConditions:
    """Test VLAN ID boundary conditions and edge cases."""

    def test_vlan_boundary_values(self, app_with_db):
        """Test VLAN IDs at boundary values."""
        block = NetworkBlock(name="VLANTest", position=1)
        db.session.add(block)
        db.session.commit()

        # Test boundary VLAN values
        boundary_vlans = [1, 4094, None]  # Min, Max, None (no VLAN)

        for i, vlan in enumerate(boundary_vlans):
            subnet = Subnet(block_id=block.id, name=f"BoundarySubnet{i}", cidr=f"192.168.{i+1}.0/24", vlan_id=vlan)
            db.session.add(subnet)
        db.session.commit()

        # Verify all were created successfully
        subnets = Subnet.query.filter_by(block_id=block.id).all()
        assert len(subnets) == 3

    def test_multiple_null_vlan_handling(self, app_with_db):
        """Test handling of multiple subnets with NULL VLAN IDs."""
        block = NetworkBlock(name="NullVLANTest", position=1)
        db.session.add(block)
        db.session.commit()

        # Create multiple subnets with NULL VLAN (should be allowed)
        null_vlan_subnets = [
            ("192.168.1.0/24", "NullSubnet1"),
            ("192.168.2.0/24", "NullSubnet2"),
            ("192.168.3.0/24", "NullSubnet3"),
        ]

        for cidr, name in null_vlan_subnets:
            subnet = Subnet(block_id=block.id, name=name, cidr=cidr, vlan_id=None)
            db.session.add(subnet)
        db.session.commit()

        # Verify all null VLAN subnets exist
        null_subnets = Subnet.query.filter_by(block_id=block.id, vlan_id=None).all()
        assert len(null_subnets) == 3

        # Test duplicate check for null VLANs (should allow multiple)
        has_duplicate, _ = check_duplicate_vlan_in_block(None, block.id)
        assert not has_duplicate  # Multiple null VLANs should be allowed

    def test_vlan_duplicate_detection_edge_cases(self, app_with_db):
        """Test VLAN duplicate detection in edge cases."""
        block = NetworkBlock(name="VLANDupeTest", position=1)
        db.session.add(block)
        db.session.commit()

        # Create subnet with VLAN 100
        subnet1 = Subnet(block_id=block.id, name="Subnet1", cidr="192.168.1.0/24", vlan_id=100)
        db.session.add(subnet1)
        db.session.commit()

        # Test duplicate detection
        has_duplicate, conflict = check_duplicate_vlan_in_block(100, block.id)
        assert has_duplicate
        assert conflict["vlan_id"] == 100

        # Test exclude_id functionality
        has_duplicate_excluded, _ = check_duplicate_vlan_in_block(100, block.id, exclude_id=subnet1.id)
        assert not has_duplicate_excluded


class TestIPAddressEdgeCases:
    """Test IP address and CIDR edge cases."""

    def test_special_ip_ranges(self, app_with_db):
        """Test handling of special IP address ranges."""
        block = NetworkBlock(name="SpecialIPTest", position=1)
        db.session.add(block)
        db.session.commit()

        # Special IP ranges that should be valid
        special_ranges = [
            "127.0.0.0/8",  # Loopback
            "169.254.0.0/16",  # Link-local
            "224.0.0.0/4",  # Multicast
            "0.0.0.0/0",  # Default route
            "255.255.255.255/32",  # Broadcast
        ]

        for i, cidr in enumerate(special_ranges):
            subnet = Subnet(block_id=block.id, name=f"SpecialRange{i}", cidr=cidr, vlan_id=100 + i)
            db.session.add(subnet)

        # Should handle all special ranges without errors
        db.session.commit()
        subnets = Subnet.query.filter_by(block_id=block.id).all()
        assert len(subnets) == len(special_ranges)

    def test_maximum_prefix_lengths(self, app_with_db):
        """Test handling of maximum and minimum prefix lengths."""
        block = NetworkBlock(name="PrefixTest", position=1)
        db.session.add(block)
        db.session.commit()

        # Test various prefix lengths
        prefix_tests = [
            ("192.168.1.0/32", "Host"),  # Single host
            ("192.168.0.0/16", "Large"),  # Large network
            ("10.0.0.0/8", "VeryLarge"),  # Very large network
            ("192.168.1.0/30", "TinySubnet"),  # Tiny subnet (4 IPs)
        ]

        for cidr, name in prefix_tests:
            subnet = Subnet(block_id=block.id, name=name, cidr=cidr, vlan_id=200)
            db.session.add(subnet)
            db.session.commit()

            # Remove for next test to avoid overlaps
            db.session.delete(subnet)
            db.session.commit()

    def test_network_vs_host_addressing(self, app_with_db):
        """Test distinction between network and host addressing."""
        block = NetworkBlock(name="NetworkHostTest", position=1)
        db.session.add(block)
        db.session.commit()

        # These should be treated as network addresses
        network_addresses = ["192.168.1.0/24", "192.168.1.1/32"]  # Network address  # Host address as /32

        for i, cidr in enumerate(network_addresses):
            subnet = Subnet(block_id=block.id, name=f"Network{i}", cidr=cidr, vlan_id=300 + i)
            db.session.add(subnet)

        db.session.commit()
        subnets = Subnet.query.filter_by(block_id=block.id).all()
        assert len(subnets) == len(network_addresses)


class TestContainerNetworkValidation:
    """Test container network validation edge cases."""

    def test_container_overlap_within_block(self, app_with_db):
        """Test container overlap detection within same block."""
        block = NetworkBlock(name="ContainerTest", position=1)
        db.session.add(block)
        db.session.commit()

        # Create base container
        container1 = NetworkContainer(block_id=block.id, name="Container1", base_network="192.168.0.0/16", position=1)
        db.session.add(container1)
        db.session.commit()

        # Test overlapping container networks
        overlap_tests = [
            ("192.168.1.0/24", True),  # Subset overlap
            ("192.168.0.0/16", True),  # Exact overlap
            ("192.0.0.0/8", True),  # Superset overlap
            ("172.16.0.0/16", False),  # No overlap
        ]

        for test_network, should_overlap in overlap_tests:
            has_overlap, _ = check_overlapping_container_networks(test_network, block.id)
            assert has_overlap == should_overlap, f"Failed for {test_network}"

    def test_container_overlap_across_blocks(self, app_with_db):
        """Test that container overlaps are scoped to blocks."""
        # Create two blocks
        block1 = NetworkBlock(name="Block1", position=1)
        block2 = NetworkBlock(name="Block2", position=2)
        db.session.add_all([block1, block2])
        db.session.commit()

        # Add same network to both blocks
        container1 = NetworkContainer(block_id=block1.id, name="Container1", base_network="192.168.0.0/16", position=1)
        container2 = NetworkContainer(block_id=block2.id, name="Container2", base_network="192.168.0.0/16", position=1)
        db.session.add_all([container1, container2])
        db.session.commit()

        # Test overlap detection (should be scoped to block)
        has_overlap_block1, _ = check_overlapping_container_networks("192.168.0.0/16", block1.id)
        has_overlap_block2, _ = check_overlapping_container_networks("192.168.0.0/16", block2.id)

        assert has_overlap_block1
        assert has_overlap_block2

    def test_container_exclude_self_during_update(self, app_with_db):
        """Test that containers can exclude themselves during updates."""
        block = NetworkBlock(name="UpdateTest", position=1)
        db.session.add(block)
        db.session.commit()

        container = NetworkContainer(
            block_id=block.id, name="UpdateContainer", base_network="192.168.0.0/16", position=1
        )
        db.session.add(container)
        db.session.commit()

        # Test updating to same network (should exclude self)
        has_overlap, _ = check_overlapping_container_networks("192.168.0.0/16", block.id, exclude_id=container.id)
        assert not has_overlap  # Should not overlap with itself

        # Test updating to overlapping network (should still detect others)
        # Create a truly separate, non-overlapping container
        container2 = NetworkContainer(
            block_id=block.id,
            name="SeparateContainer",
            base_network="10.0.0.0/16",  # Completely different network range
            position=2,
        )
        db.session.add(container2)
        db.session.commit()

        # Test overlap detection with one container excluded
        # This network should overlap with container1 (192.168.0.0/16) but not container2 (10.0.0.0/16)
        has_overlap, overlapping_container = check_overlapping_container_networks(
            "192.168.0.0/16",  # Exact same network as container1 - should overlap
            block.id,
            exclude_id=container2.id,  # Exclude the 10.x container (but not container1)
        )

        assert has_overlap  # Should detect overlap with container1
        assert overlapping_container is not None
        assert overlapping_container["id"] == container.id


class TestNetworkCalculationEdgeCases:
    """Test network calculation and sorting edge cases."""

    def test_invalid_cidr_in_sorting(self, app_with_db):
        """Test handling of invalid CIDR formats in sorting operations."""
        from app.utils import sort_networks_by_ip

        block = NetworkBlock(name="SortTest", position=1)
        db.session.add(block)
        db.session.commit()

        # Create subnets with both valid and invalid CIDRs
        test_subnets = []
        valid_cidrs = ["192.168.1.0/24", "10.0.0.0/8", "172.16.0.0/16"]
        invalid_cidrs = ["invalid-cidr", "192.168.1.0", "not.a.network/24"]

        for i, cidr in enumerate(valid_cidrs + invalid_cidrs):
            subnet = Subnet(block_id=block.id, name=f"Subnet{i}", cidr=cidr, vlan_id=100 + i)
            test_subnets.append(subnet)

        # Should handle invalid CIDRs gracefully in sorting
        try:
            sorted_subnets = sort_networks_by_ip(test_subnets)
            # Invalid CIDRs should be sorted to the end
            assert len(sorted_subnets) == len(test_subnets)
        except Exception as e:
            pytest.fail(f"Sorting failed with invalid CIDRs: {e}")

    def test_ipv6_handling(self, app_with_db):
        """Test that IPv6 addresses are handled appropriately."""
        # Note: Current system is IPv4-only, so IPv6 should be rejected
        block = NetworkBlock(name="IPv6Test", position=1)
        db.session.add(block)
        db.session.commit()

        ipv6_addresses = ["2001:db8::/32", "::1/128", "fe80::/10"]

        for ipv6_addr in ipv6_addresses:
            # Should detect as invalid CIDR format
            has_overlap, _ = check_overlapping_cidr_in_block(ipv6_addr, block.id)
            # Function should handle gracefully (return False for invalid format)
            assert not has_overlap
