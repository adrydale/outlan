"""
Comprehensive API CRUD operations testing.

This module tests all API endpoints for Create, Read, Update, Delete operations
including filtering and validation.
"""


class TestBlocksCRUD:
    """Test CRUD operations for blocks API."""

    def test_create_block_api(self, client):
        """Test creating a block via API."""
        response = client.post("/api/blocks", json={"name": "TestBlock"})
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "block" in data
        assert data["block"]["name"] == "TestBlock"

    def test_get_all_blocks_api(self, client):
        """Test getting all blocks via API."""
        # Create test blocks
        client.post("/api/blocks", json={"name": "Block1"})
        client.post("/api/blocks", json={"name": "Block2"})

        response = client.get("/api/blocks")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "blocks" in data
        assert len(data["blocks"]) >= 2

    def test_get_blocks_with_search_filter(self, client):
        """Test getting blocks with search filtering."""
        client.post("/api/blocks", json={"name": "Production"})
        client.post("/api/blocks", json={"name": "Development"})

        response = client.get("/api/blocks?search=prod")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Should find Production block
        block_names = [block["name"] for block in data["blocks"]]
        assert any("Production" in name for name in block_names)

    def test_get_single_block_api(self, client):
        """Test getting a single block by ID."""
        # Create block first
        response = client.post("/api/blocks", json={"name": "SingleBlock"})
        assert response.status_code == 201
        block_data = response.get_json()
        block_id = block_data["block"]["id"]

        # Get the block
        response = client.get(f"/api/blocks/{block_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["block"]["name"] == "SingleBlock"

    def test_get_nonexistent_block_api(self, client):
        """Test getting a nonexistent block."""
        response = client.get("/api/blocks/99999")
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    def test_update_block_api(self, client):
        """Test updating a block via API."""
        # Create block first
        response = client.post("/api/blocks", json={"name": "OriginalName"})
        assert response.status_code == 201
        block_data = response.get_json()
        block_id = block_data["block"]["id"]

        # Update the block
        response = client.put(f"/api/blocks/{block_id}", json={"name": "UpdatedName", "position": 5, "collapsed": True})
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["block"]["name"] == "UpdatedName"
        assert data["block"]["position"] == 5
        assert data["block"]["collapsed"] is True

    def test_update_nonexistent_block_api(self, client):
        """Test updating a nonexistent block."""
        response = client.put("/api/blocks/99999", json={"name": "NewName"})
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False

    def test_delete_block_api(self, client):
        """Test deleting a block via API."""
        # Create block first
        response = client.post("/api/blocks", json={"name": "ToDelete"})
        assert response.status_code == 201
        block_data = response.get_json()
        block_id = block_data["block"]["id"]

        # Delete the block
        response = client.delete(f"/api/blocks/{block_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Verify it's gone
        response = client.get(f"/api/blocks/{block_id}")
        assert response.status_code == 404

    def test_delete_nonexistent_block_api(self, client):
        """Test deleting a nonexistent block."""
        response = client.delete("/api/blocks/99999")
        assert response.status_code == 404


class TestSubnetsCRUD:
    """Test CRUD operations for subnets API."""

    def test_create_subnet_api(self, client):
        """Test creating a subnet via API."""
        # Create block first
        block_response = client.post("/api/blocks", json={"name": "SubnetBlock"})
        block_id = block_response.get_json()["block"]["id"]

        # Create subnet
        response = client.post(
            "/api/networks", json={"block_id": block_id, "name": "TestSubnet", "cidr": "192.168.1.0/24", "vlan_id": 100}
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["network"]["name"] == "TestSubnet"
        assert data["network"]["cidr"] == "192.168.1.0/24"
        assert data["network"]["vlan_id"] == 100

    def test_get_all_subnets_api(self, client):
        """Test getting all subnets via API."""
        # Create block and subnets
        block_response = client.post("/api/blocks", json={"name": "SubnetBlock"})
        block_id = block_response.get_json()["block"]["id"]

        client.post(
            "/api/networks", json={"block_id": block_id, "name": "Subnet1", "cidr": "10.0.1.0/24", "vlan_id": 101}
        )
        client.post(
            "/api/networks", json={"block_id": block_id, "name": "Subnet2", "cidr": "10.0.2.0/24", "vlan_id": 102}
        )

        response = client.get("/api/networks")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["networks"]) >= 2

    def test_get_subnets_with_filters(self, client):
        """Test getting subnets with various filters."""
        # Create block and subnets
        block_response = client.post("/api/blocks", json={"name": "FilterBlock"})
        block_id = block_response.get_json()["block"]["id"]

        client.post(
            "/api/networks",
            json={"block_id": block_id, "name": "Production-Web", "cidr": "10.1.1.0/24", "vlan_id": 200},
        )
        client.post(
            "/api/networks",
            json={"block_id": block_id, "name": "Development-DB", "cidr": "10.1.2.0/24", "vlan_id": 201},
        )

        # Test block filter
        response = client.get(f"/api/networks?block_id={block_id}")
        assert response.status_code == 200
        data = response.get_json()
        for network in data["networks"]:
            assert network["block_id"] == block_id

        # Test search filter
        response = client.get("/api/networks?search=production")
        assert response.status_code == 200
        data = response.get_json()
        assert any("Production" in network["name"] for network in data["networks"])

        # Test VLAN filter
        response = client.get("/api/networks?vlan_id=200")
        assert response.status_code == 200
        data = response.get_json()
        assert all(network["vlan_id"] == 200 for network in data["networks"])

    def test_get_single_subnet_api(self, client):
        """Test getting a single subnet by ID."""
        # Create block and subnet
        block_response = client.post("/api/blocks", json={"name": "SingleBlock"})
        block_id = block_response.get_json()["block"]["id"]

        network_response = client.post(
            "/api/networks", json={"block_id": block_id, "name": "SingleSubnet", "cidr": "172.16.1.0/24"}
        )
        network_id = network_response.get_json()["network"]["id"]

        # Get the subnet
        response = client.get(f"/api/networks/{network_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["network"]["name"] == "SingleSubnet"

    def test_update_subnet_api(self, client):
        """Test updating a subnet via API."""
        # Create block and subnet
        block_response = client.post("/api/blocks", json={"name": "UpdateBlock"})
        block_id = block_response.get_json()["block"]["id"]

        network_response = client.post(
            "/api/networks",
            json={"block_id": block_id, "name": "OriginalSubnet", "cidr": "10.0.1.0/24", "vlan_id": 100},
        )
        network_id = network_response.get_json()["network"]["id"]

        # Update the subnet
        response = client.put(
            f"/api/networks/{network_id}", json={"name": "UpdatedSubnet", "cidr": "10.0.2.0/24", "vlan_id": 200}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["network"]["name"] == "UpdatedSubnet"
        assert data["network"]["cidr"] == "10.0.2.0/24"
        assert data["network"]["vlan_id"] == 200

    def test_delete_subnet_api(self, client):
        """Test deleting a subnet via API."""
        # Create block and subnet
        block_response = client.post("/api/blocks", json={"name": "DeleteBlock"})
        block_id = block_response.get_json()["block"]["id"]

        network_response = client.post(
            "/api/networks", json={"block_id": block_id, "name": "ToDeleteSubnet", "cidr": "10.0.1.0/24"}
        )
        network_id = network_response.get_json()["network"]["id"]

        # Delete the subnet
        response = client.delete(f"/api/networks/{network_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Verify it's gone
        response = client.get(f"/api/networks/{network_id}")
        assert response.status_code == 404


class TestContainersCRUD:
    """Test CRUD operations for containers API."""

    def test_create_container_api(self, client):
        """Test creating a container via API."""
        # Create block first
        block_response = client.post("/api/blocks", json={"name": "ContainerBlock"})
        block_id = block_response.get_json()["block"]["id"]

        # Create container
        response = client.post(
            "/api/containers", json={"block_id": block_id, "name": "TestContainer", "base_network": "192.168.0.0/16"}
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["container"]["name"] == "TestContainer"
        assert data["container"]["base_network"] == "192.168.0.0/16"

    def test_get_all_containers_api(self, client):
        """Test getting all containers via API."""
        # Create block and containers
        block_response = client.post("/api/blocks", json={"name": "ContainerBlock"})
        block_id = block_response.get_json()["block"]["id"]

        client.post("/api/containers", json={"block_id": block_id, "name": "Container1", "base_network": "10.0.0.0/16"})
        client.post(
            "/api/containers", json={"block_id": block_id, "name": "Container2", "base_network": "172.16.0.0/12"}
        )

        response = client.get("/api/containers")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["containers"]) >= 2

    def test_get_containers_with_filters(self, client):
        """Test getting containers with filters."""
        # Create block and containers
        block_response = client.post("/api/blocks", json={"name": "FilterBlock"})
        block_id = block_response.get_json()["block"]["id"]

        client.post(
            "/api/containers", json={"block_id": block_id, "name": "Production-Segment", "base_network": "10.1.0.0/16"}
        )

        # Test block filter
        response = client.get(f"/api/containers?block_id={block_id}")
        assert response.status_code == 200
        data = response.get_json()
        for container in data["containers"]:
            assert container["block_id"] == block_id

        # Test search filter
        response = client.get("/api/containers?search=production")
        assert response.status_code == 200
        data = response.get_json()
        assert any("Production" in container["name"] for container in data["containers"])

    def test_get_single_container_api(self, client):
        """Test getting a single container by ID."""
        # Create block and container
        block_response = client.post("/api/blocks", json={"name": "SingleBlock"})
        block_id = block_response.get_json()["block"]["id"]

        container_response = client.post(
            "/api/containers", json={"block_id": block_id, "name": "SingleContainer", "base_network": "10.0.0.0/8"}
        )
        container_id = container_response.get_json()["container"]["id"]

        # Get the container
        response = client.get(f"/api/containers/{container_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["container"]["name"] == "SingleContainer"

    def test_update_container_api(self, client):
        """Test updating a container via API."""
        # Create block and container
        block_response = client.post("/api/blocks", json={"name": "UpdateBlock"})
        block_id = block_response.get_json()["block"]["id"]

        container_response = client.post(
            "/api/containers", json={"block_id": block_id, "name": "OriginalContainer", "base_network": "10.0.0.0/8"}
        )
        container_id = container_response.get_json()["container"]["id"]

        # Update the container
        response = client.put(
            f"/api/containers/{container_id}",
            json={"name": "UpdatedContainer", "base_network": "172.16.0.0/12", "position": 3},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["container"]["name"] == "UpdatedContainer"
        assert data["container"]["base_network"] == "172.16.0.0/12"
        assert data["container"]["position"] == 3

    def test_delete_container_api(self, client):
        """Test deleting a container via API."""
        # Create block and container
        block_response = client.post("/api/blocks", json={"name": "DeleteBlock"})
        block_id = block_response.get_json()["block"]["id"]

        container_response = client.post(
            "/api/containers", json={"block_id": block_id, "name": "ToDeleteContainer", "base_network": "10.0.0.0/8"}
        )
        container_id = container_response.get_json()["container"]["id"]

        # Delete the container
        response = client.delete(f"/api/containers/{container_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        # Verify it's gone
        response = client.get(f"/api/containers/{container_id}")
        assert response.status_code == 404


class TestAPIValidation:
    """Test API validation and error handling."""

    def test_block_validation_errors(self, client):
        """Test block validation errors."""
        # Test empty name
        response = client.post("/api/blocks", json={"name": ""})
        assert response.status_code == 400

        # Test duplicate name
        client.post("/api/blocks", json={"name": "DuplicateTest"})
        response = client.post("/api/blocks", json={"name": "DuplicateTest"})
        assert response.status_code == 400

        # Test invalid name type
        response = client.post("/api/blocks", json={"name": 123})
        assert response.status_code == 400

    def test_network_validation_errors(self, client):
        """Test network validation errors."""
        # Create block first
        block_response = client.post("/api/blocks", json={"name": "ValidationBlock"})
        block_id = block_response.get_json()["block"]["id"]

        # Test invalid CIDR
        response = client.post(
            "/api/networks", json={"block_id": block_id, "name": "InvalidSubnet", "cidr": "invalid-cidr"}
        )
        assert response.status_code == 400

        # Test invalid VLAN
        response = client.post(
            "/api/networks",
            json={"block_id": block_id, "name": "InvalidVLAN", "cidr": "10.0.1.0/24", "vlan_id": "not-a-number"},
        )
        assert response.status_code == 400

        # Test nonexistent block
        response = client.post("/api/networks", json={"block_id": 99999, "name": "TestSubnet", "cidr": "10.0.1.0/24"})
        assert response.status_code == 404

    def test_container_validation_errors(self, client):
        """Test container validation errors."""
        # Create block first
        block_response = client.post("/api/blocks", json={"name": "ValidationBlock"})
        block_id = block_response.get_json()["block"]["id"]

        # Test invalid base network
        response = client.post(
            "/api/containers",
            json={"block_id": block_id, "name": "InvalidContainer", "base_network": "invalid-network"},
        )
        assert response.status_code == 400

        # Test empty name
        response = client.post("/api/containers", json={"block_id": block_id, "name": "", "base_network": "10.0.0.0/8"})
        assert response.status_code == 400


class TestAPIFiltering:
    """Test advanced filtering capabilities."""

    def test_multiple_filter_combination(self, client):
        """Test combining multiple filters."""
        # Create test data
        block_response = client.post("/api/blocks", json={"name": "FilterTestBlock"})
        block_id = block_response.get_json()["block"]["id"]

        client.post(
            "/api/networks",
            json={"block_id": block_id, "name": "Production-Web-DMZ", "cidr": "10.1.1.0/24", "vlan_id": 100},
        )

        # Test search + VLAN filter combination
        response = client.get("/api/networks?search=production&vlan_id=100")
        assert response.status_code == 200
        data = response.get_json()

        # Should find the subnet that matches both criteria
        matching_networks = [s for s in data["networks"] if "Production" in s["name"] and s["vlan_id"] == 100]
        assert len(matching_networks) > 0

    def test_case_insensitive_search(self, client):
        """Test that search filters are case insensitive."""
        # Create test data
        client.post("/api/blocks", json={"name": "UPPERCASE-BLOCK"})

        # Search with lowercase
        response = client.get("/api/blocks?search=uppercase")
        assert response.status_code == 200
        data = response.get_json()

        # Should find the uppercase block
        assert any("UPPERCASE" in block["name"] for block in data["blocks"])
