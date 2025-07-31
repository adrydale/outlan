"""
Test suite for audit page UI functionality.

This module tests all UI elements and functionality on the audit page
including collapsible snapshots, JavaScript functionality, and page loading.
"""


def test_audit_page_has_collapsible_snapshot_summary(app_with_db):
    """
    Test that the audit page has the collapsible snapshot summary elements.

    Verifies that:
    - Collapsible snapshot structure is present
    - Toggle functionality elements exist
    - Content areas are properly defined
    - Accessibility attributes are included
    """
    with app_with_db.test_client() as client:
        response = client.get("/audit")
        assert response.status_code == 200

        # Check for the collapsible structure
        assert b'id="snapshot-summary"' in response.data
        assert b'id="snapshot-toggle"' in response.data
        assert b'id="snapshot-content"' in response.data
        assert b'id="snapshot-toggle-icon"' in response.data
        assert b'aria-expanded="true"' in response.data
        assert b'class="snapshot-toggle"' in response.data
        assert b'class="snapshot-content"' in response.data


def test_base_template_has_collapsible_javascript(client):
    """
    Test that the base template includes the collapsible JavaScript functionality.

    Verifies that:
    - JavaScript functions for collapsible functionality are present
    - Local storage integration is included
    - Collapsible state management is implemented
    """
    response = client.get("/")
    assert response.status_code == 200

    # Check for the JavaScript function
    assert b"initSnapshotCollapsible" in response.data
    assert b"snapshot-summary-collapsed" in response.data
    assert b"localStorage.setItem" in response.data
    assert b"localStorage.getItem" in response.data


def test_collapsible_css_classes_present(client):
    """
    Test that the CSS classes for collapsible functionality are present.

    Verifies that:
    - CSS classes for collapsible states are defined
    - Mobile-specific collapsible classes exist
    - Dynamic class application is supported
    """
    response = client.get("/audit")
    assert response.status_code == 200

    # Check for CSS classes that should be applied by JavaScript
    # These are the classes that will be added/removed dynamically
    assert b"collapsed" in response.data  # This class will be added by JS
    assert b"mobile-collapsed" in response.data  # This class will be added by JS on mobile


def test_audit_page_loads_successfully(client):
    """
    Test that the audit page loads without errors.

    Verifies that:
    - Audit page loads successfully
    - Expected content is present
    - No errors occur during page load
    """
    response = client.get("/audit")
    assert response.status_code == 200

    # Check that the page contains expected content
    assert b"Audit and Snapshots" in response.data
    assert b"About Snapshots" in response.data


def test_audit_mobile_layout_elements_present(app_with_db):
    """
    Test that the audit page has mobile layout elements.

    Verifies that:
    - Mobile audit container is present
    - Desktop table is present (for desktop view)
    - Both mobile and desktop layouts are available
    - Audit entries are properly displayed in both layouts
    """
    from app.utils import DatabaseService

    with app_with_db.test_client() as client:
        # Create some audit entries in the temporary database
        DatabaseService.add_change_log(
            action="ADD_BLOCK", block="Test Block 1", details="Added test block for mobile layout test"
        )
        DatabaseService.add_change_log(action="ADD_SUBNET", block="Test Block 1", details="Added subnet 192.168.1.0/24")
        DatabaseService.add_change_log(
            action="EDIT_SUBNET", block="Test Block 1", details="Updated subnet name to 'Test Subnet'"
        )

        response = client.get("/audit")
        assert response.status_code == 200

        # Check for mobile audit container layout
        assert b'class="mobile-audit"' in response.data

        # Check for desktop table layout
        assert b'class="audit-table"' in response.data
        assert b"<table" in response.data
        assert b"<th>" in response.data
        assert b"<td>" in response.data  # Now we should have table data

        # Check that audit entries are present in the response
        assert b"Test Block 1" in response.data
        assert b"ADD_BLOCK" in response.data
        assert b"ADD_SUBNET" in response.data
        assert b"EDIT_SUBNET" in response.data
