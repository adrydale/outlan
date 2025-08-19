"""
Swagger/OpenAPI documentation testing.

This module tests the Swagger documentation endpoints and functionality.
"""


class TestSwaggerDocumentation:
    """Test Swagger documentation functionality."""

    def test_swagger_json_endpoint(self, client):
        """Test that the swagger.json endpoint is accessible."""
        response = client.get("/api/swagger.json")
        assert response.status_code == 200

        # Verify it returns valid JSON
        swagger_data = response.get_json()
        assert swagger_data is not None
        assert "swagger" in swagger_data or "openapi" in swagger_data
        assert "info" in swagger_data
        assert "paths" in swagger_data

    def test_swagger_ui_endpoint(self, client):
        """Test that the Swagger UI endpoint is accessible."""
        response = client.get("/swagger/")
        assert response.status_code == 200

        # Should contain HTML for Swagger UI
        html_content = response.get_data(as_text=True)
        assert "swagger-ui" in html_content.lower() or "openapi" in html_content.lower()

    def test_swagger_includes_all_endpoints(self, client):
        """Test that swagger documentation includes all our API endpoints."""
        response = client.get("/api/swagger.json")
        swagger_data = response.get_json()

        paths = swagger_data.get("paths", {})

        # Check that major endpoint categories are documented
        expected_paths = [
            "/health",
            "/version",
            "/blocks",
            "/blocks/{block_id}",
            "/networks",
            "/networks/{network_id}",
            "/containers",
            "/containers/{container_id}",
            "/toggle_collapse/{block_id}",
            "/update_block_order",
        ]

        for expected_path in expected_paths:
            assert any(expected_path in path for path in paths.keys()), f"Missing documented path: {expected_path}"

    def test_swagger_includes_proper_methods(self, client):
        """Test that swagger documentation includes proper HTTP methods."""
        response = client.get("/api/swagger.json")
        swagger_data = response.get_json()

        paths = swagger_data.get("paths", {})

        # Check blocks endpoint has GET and POST
        blocks_path = "/blocks"
        assert blocks_path in paths, "Blocks endpoint not found in swagger"
        assert "get" in paths[blocks_path], "GET method missing for blocks endpoint"
        assert "post" in paths[blocks_path], "POST method missing for blocks endpoint"

        # Check individual block endpoint has GET, PUT, DELETE
        block_by_id_path = "/blocks/{block_id}"
        assert block_by_id_path in paths, "Block by ID endpoint not found in swagger"
        assert "get" in paths[block_by_id_path], "GET method missing for block by ID endpoint"
        assert "put" in paths[block_by_id_path], "PUT method missing for block by ID endpoint"
        assert "delete" in paths[block_by_id_path], "DELETE method missing for block by ID endpoint"

    def test_swagger_includes_models(self, client):
        """Test that swagger documentation includes data models."""
        response = client.get("/api/swagger.json")
        swagger_data = response.get_json()

        # Check for definitions/components section
        definitions = swagger_data.get("definitions", {})
        components = swagger_data.get("components", {})

        # Should have model definitions
        has_models = len(definitions) > 0 or (components and len(components.get("schemas", {})) > 0)
        assert has_models, "No data models found in swagger documentation"

        # Check for some key models
        all_models = (
            list(definitions.keys()) + list(components.get("schemas", {}).keys())
            if components
            else list(definitions.keys())
        )

        expected_models = ["Block", "Network", "Container", "Health", "Version", "Error", "Success"]
        for model in expected_models:
            assert any(model in model_name for model_name in all_models), f"Missing model: {model}"

    def test_swagger_info_section(self, client):
        """Test that swagger documentation has proper info section."""
        response = client.get("/api/swagger.json")
        swagger_data = response.get_json()

        info = swagger_data.get("info", {})
        assert "title" in info
        assert "version" in info
        assert "description" in info

        # Check that it's about our API
        assert "outlan" in info["title"].lower() or "ipam" in info["title"].lower()

    def test_swagger_redirect_routes(self, client):
        """Test that all redirect routes properly redirect to /swagger/."""
        redirect_routes = ["/docs", "/api/", "/api/swagger"]

        for route in redirect_routes:
            response = client.get(route)
            assert response.status_code == 302, f"Route {route} should return 302 redirect"
            assert response.location == "/swagger/", f"Route {route} should redirect to /swagger/"

    def test_canonical_swagger_route(self, client):
        """Test that the canonical /swagger/ route works correctly."""
        response = client.get("/swagger/")
        assert response.status_code == 200

        # Should contain Swagger UI HTML
        html_content = response.get_data(as_text=True)
        assert "swagger-ui" in html_content.lower()
        assert "Outlan IPAM API" in html_content


class TestSwaggerValidation:
    """Test Swagger schema validation and accuracy."""

    def test_health_endpoint_documented(self, client):
        """Test that health endpoint is properly documented and works."""
        # Test actual endpoint
        response = client.get("/api/health")
        assert response.status_code == 200

        health_data = response.get_json()
        assert "status" in health_data
        assert "timestamp" in health_data

        # Verify swagger documents this
        swagger_response = client.get("/api/swagger.json")
        swagger_data = swagger_response.get_json()

        paths = swagger_data.get("paths", {})
        health_path = None
        for path in paths.keys():
            if "health" in path and "{" not in path:
                health_path = path
                break

        assert health_path is not None, "Health endpoint not documented in swagger"
