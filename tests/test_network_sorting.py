import ipaddress


class MockSubnet:
    """Simple mock subnet object for testing"""

    def __init__(self, block_id: int, cidr: str, vlan_id=None, name=None):
        self.block_id = block_id
        self.cidr = cidr
        self.vlan_id = vlan_id
        self.name = name or f"Subnet {cidr}"


def sort_networks_by_ip(subnets):
    """Sort subnets by IP network address properly"""

    def get_network_key(subnet):
        """Get sorting key for network: (block_id, network_address, prefix_length)"""
        try:
            network = ipaddress.IPv4Network(subnet.cidr, strict=False)
            return (subnet.block_id, int(network.network_address), network.prefixlen)
        except ValueError:
            # If CIDR is invalid, sort it to the end
            return (subnet.block_id, float("inf"), 0)

    return sorted(subnets, key=get_network_key)


def sort_networks_by_vlan_with_network(subnets):
    """Sort subnets by VLAN ID first, then by IP network address"""

    def get_vlan_network_key(subnet):
        """Get sorting key for VLAN + network: (block_id, vlan_id, network_address, prefix_length)"""
        try:
            network = ipaddress.IPv4Network(subnet.cidr, strict=False)
            # Use a large number for null VLAN IDs to sort them last
            vlan_id = subnet.vlan_id if subnet.vlan_id is not None else float("inf")
            return (subnet.block_id, vlan_id, int(network.network_address), network.prefixlen)
        except ValueError:
            # If CIDR is invalid, sort it to the end
            return (subnet.block_id, subnet.vlan_id or float("inf"), float("inf"), 0)

    return sorted(subnets, key=get_vlan_network_key)


def sort_networks_by_name_with_network(subnets):
    """Sort subnets by name first, then by IP network address"""

    def get_name_network_key(subnet):
        """Get sorting key for name + network: (block_id, name, network_address, prefix_length)"""
        try:
            network = ipaddress.IPv4Network(subnet.cidr, strict=False)
            return (subnet.block_id, subnet.name.lower(), int(network.network_address), network.prefixlen)
        except ValueError:
            # If CIDR is invalid, sort it to the end
            return (subnet.block_id, subnet.name.lower(), float("inf"), 0)

    return sorted(subnets, key=get_name_network_key)


def test_network_sorting():
    """Test that networks are sorted by IP address properly"""

    # Create mock subnets with different CIDR ranges
    subnets = [
        MockSubnet(block_id=1, cidr="10.0.10.0/24"),
        MockSubnet(block_id=1, cidr="10.0.1.0/24"),
        MockSubnet(block_id=1, cidr="10.0.2.0/24"),
        MockSubnet(block_id=1, cidr="192.168.1.0/24"),
        MockSubnet(block_id=1, cidr="172.16.0.0/16"),
        MockSubnet(block_id=2, cidr="10.0.0.0/8"),
    ]

    # Sort the networks
    sorted_subnets = sort_networks_by_ip(subnets)

    # Extract CIDR strings in order
    sorted_cidrs = [subnet.cidr for subnet in sorted_subnets]

    # Expected order: sorted by block_id first, then by network address within each block
    expected_order = [
        "10.0.1.0/24",  # 10.0.1.0/24 (block 1)
        "10.0.2.0/24",  # 10.0.2.0/24 (block 1)
        "10.0.10.0/24",  # 10.0.10.0/24 (block 1)
        "172.16.0.0/16",  # 172.16.0.0/16 (block 1)
        "192.168.1.0/24",  # 192.168.1.0/24 (block 1)
        "10.0.0.0/8",  # 10.0.0.0/8 (block 2)
    ]

    assert sorted_cidrs == expected_order


def test_network_sorting_with_invalid_cidr():
    """Test that invalid CIDR networks are sorted to the end"""

    subnets = [
        MockSubnet(block_id=1, cidr="10.0.1.0/24"),
        MockSubnet(block_id=1, cidr="invalid-cidr"),
        MockSubnet(block_id=1, cidr="10.0.2.0/24"),
    ]

    sorted_subnets = sort_networks_by_ip(subnets)
    sorted_cidrs = [subnet.cidr for subnet in sorted_subnets]

    # Invalid CIDR should be at the end
    expected_order = ["10.0.1.0/24", "10.0.2.0/24", "invalid-cidr"]

    assert sorted_cidrs == expected_order


def test_network_sorting_different_blocks():
    """Test that networks are sorted by block_id first, then by IP"""

    subnets = [
        MockSubnet(block_id=2, cidr="10.0.1.0/24"),
        MockSubnet(block_id=1, cidr="10.0.2.0/24"),
        MockSubnet(block_id=1, cidr="10.0.1.0/24"),
        MockSubnet(block_id=2, cidr="10.0.2.0/24"),
    ]

    sorted_subnets = sort_networks_by_ip(subnets)
    sorted_cidrs = [subnet.cidr for subnet in sorted_subnets]

    # Should be sorted by block_id first, then by IP within each block
    expected_order = [
        "10.0.1.0/24",  # block 1
        "10.0.2.0/24",  # block 1
        "10.0.1.0/24",  # block 2
        "10.0.2.0/24",  # block 2
    ]

    assert sorted_cidrs == expected_order


def test_network_sorting_prefix_length():
    """Test that networks with same network address are sorted by prefix length"""

    subnets = [
        MockSubnet(block_id=1, cidr="10.0.0.0/16"),
        MockSubnet(block_id=1, cidr="10.0.0.0/24"),
        MockSubnet(block_id=1, cidr="10.0.0.0/8"),
    ]

    sorted_subnets = sort_networks_by_ip(subnets)
    sorted_cidrs = [subnet.cidr for subnet in sorted_subnets]

    # Should be sorted by prefix length (smaller prefix = larger network)
    expected_order = [
        "10.0.0.0/8",  # /8 (largest network)
        "10.0.0.0/16",  # /16
        "10.0.0.0/24",  # /24 (smallest network)
    ]

    assert sorted_cidrs == expected_order


def test_vlan_sorting_with_network():
    """Test that networks are sorted by VLAN first, then by IP network"""

    subnets = [
        MockSubnet(block_id=1, cidr="10.0.10.0/24", vlan_id=100),
        MockSubnet(block_id=1, cidr="10.0.1.0/24", vlan_id=100),
        MockSubnet(block_id=1, cidr="10.0.2.0/24", vlan_id=200),
        MockSubnet(block_id=1, cidr="192.168.1.0/24", vlan_id=100),
        MockSubnet(block_id=1, cidr="172.16.0.0/16", vlan_id=None),
        MockSubnet(block_id=2, cidr="10.0.0.0/8", vlan_id=50),
    ]

    sorted_subnets = sort_networks_by_vlan_with_network(subnets)
    sorted_cidrs = [subnet.cidr for subnet in sorted_subnets]

    # Expected order: sorted by block_id first, then VLAN ID, then by network address
    # Block 1: VLAN 100, VLAN 200, VLAN None
    # Block 2: VLAN 50
    expected_order = [
        "10.0.1.0/24",  # VLAN 100 (block 1)
        "10.0.10.0/24",  # VLAN 100 (block 1)
        "192.168.1.0/24",  # VLAN 100 (block 1)
        "10.0.2.0/24",  # VLAN 200 (block 1)
        "172.16.0.0/16",  # VLAN None (block 1)
        "10.0.0.0/8",  # VLAN 50 (block 2)
    ]

    assert sorted_cidrs == expected_order


def test_name_sorting_with_network():
    """Test that networks are sorted by name first, then by IP network"""

    subnets = [
        MockSubnet(block_id=1, cidr="10.0.10.0/24", name="Office Network"),
        MockSubnet(block_id=1, cidr="10.0.1.0/24", name="Office Network"),
        MockSubnet(block_id=1, cidr="10.0.2.0/24", name="Guest Network"),
        MockSubnet(block_id=1, cidr="192.168.1.0/24", name="Office Network"),
        MockSubnet(block_id=1, cidr="172.16.0.0/16", name="Admin Network"),
        MockSubnet(block_id=2, cidr="10.0.0.0/8", name="Backbone"),
    ]

    sorted_subnets = sort_networks_by_name_with_network(subnets)
    sorted_cidrs = [subnet.cidr for subnet in sorted_subnets]

    # Expected order: sorted by block_id first, then by name (case insensitive), then by network address
    # Block 1: Admin Network, Guest Network, Office Network
    # Block 2: Backbone
    expected_order = [
        "172.16.0.0/16",  # Admin Network (block 1)
        "10.0.2.0/24",  # Guest Network (block 1)
        "10.0.1.0/24",  # Office Network (block 1)
        "10.0.10.0/24",  # Office Network (block 1)
        "192.168.1.0/24",  # Office Network (block 1)
        "10.0.0.0/8",  # Backbone (block 2)
    ]

    assert sorted_cidrs == expected_order


def test_vlan_sorting_with_null_vlans():
    """Test that null VLAN IDs are sorted last"""

    subnets = [
        MockSubnet(block_id=1, cidr="10.0.1.0/24", vlan_id=100),
        MockSubnet(block_id=1, cidr="10.0.2.0/24", vlan_id=None),
        MockSubnet(block_id=1, cidr="10.0.3.0/24", vlan_id=50),
        MockSubnet(block_id=1, cidr="10.0.4.0/24", vlan_id=None),
    ]

    sorted_subnets = sort_networks_by_vlan_with_network(subnets)
    sorted_cidrs = [subnet.cidr for subnet in sorted_subnets]

    # Expected order: VLAN 50, VLAN 100, then null VLANs
    expected_order = [
        "10.0.3.0/24",  # VLAN 50
        "10.0.1.0/24",  # VLAN 100
        "10.0.2.0/24",  # VLAN None
        "10.0.4.0/24",  # VLAN None
    ]

    assert sorted_cidrs == expected_order
