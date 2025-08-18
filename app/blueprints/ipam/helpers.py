"""
Shared utility functions for IPAM operations.

This module contains reusable helper functions used across all IPAM domains:
- Error handling helpers
- Data extraction helpers
- Validation helpers
- Decomposition helpers for complex operations
"""

import json
import logging

from flask import current_app, flash, redirect, render_template, url_for

from app.utils import DatabaseService
from app.utils.validation import (
    check_duplicate_vlan_in_block,
    check_overlapping_cidr_in_block,
    sanitize_input,
    validate_block_name,
    validate_cidr_format,
    validate_subnet_name,
    validate_vlan_id,
)

logger = logging.getLogger(__name__)


# Error handling helper functions
def _render_validation_error(message, attempted_data, status_code=200):
    """Helper to render consistent validation errors.

    Args:
        message: Error message to display
        attempted_data: Form data that was attempted
        status_code: HTTP status code (200 for validation errors, 400/404 for not found)

    Note:
        Web forms should return 200 with error messages for better UX.
        Only use 400+ for actual client errors (not found, etc.)
    """
    return (
        render_template("error.html", message=message, attempted=attempted_data, version=current_app.version),
        status_code,
    )


def _get_attempted_subnet_data(form):
    """Extract attempted form data for subnet operations."""
    return {
        "cidr": sanitize_input(form.get("cidr", "")),
        "vlan": sanitize_input(form.get("vlan_id", "")),
        "name": sanitize_input(form.get("name", "")),
    }


def _get_attempted_block_data(form):
    """Extract attempted form data for block operations."""
    raw_name = form.get("block_name", "") or form.get("new_block_name", "")
    # Sanitize the name to prevent XSS
    sanitized_name = sanitize_input(raw_name) if raw_name else ""
    return {"cidr": None, "vlan": None, "name": sanitized_name}


def _get_attempted_container_data(form):
    """Extract attempted form data for container operations."""
    return {"cidr": form.get("base_network", ""), "vlan": None, "name": form.get("container_name", "")}


# Validation helper functions
def _validate_subnet_basic_input(name_raw, cidr_raw, vlan_id_raw):
    """
    Validate basic subnet inputs (name, CIDR, VLAN).

    Returns:
        tuple: (is_valid, error_message, validated_data)
            - is_valid: bool indicating if all validations passed
            - error_message: str with error details if validation failed
            - validated_data: dict with sanitized values if successful
    """
    # Sanitize inputs
    name = sanitize_input(name_raw)
    cidr = sanitize_input(cidr_raw)

    # Validate name
    name_valid, name_error = validate_subnet_name(name)
    if not name_valid:
        return False, f"Subnet name validation error: {name_error}", None

    # Validate CIDR
    cidr_valid, cidr_error = validate_cidr_format(cidr)
    if not cidr_valid:
        return False, f"CIDR validation error: {cidr_error}", None

    # Validate VLAN ID
    vlan_id = None
    if vlan_id_raw:
        vlan_valid, vlan_error, cleaned_vlan = validate_vlan_id(vlan_id_raw)
        if not vlan_valid:
            return False, f"VLAN validation error: {vlan_error}", None
        vlan_id = cleaned_vlan

    return True, None, {"name": name, "cidr": cidr, "vlan_id": vlan_id}


def _validate_block_basic_input(name_raw):
    """
    Validate basic block inputs (name).

    Returns:
        tuple: (is_valid, error_message, validated_data)
            - is_valid: bool indicating if all validations passed
            - error_message: str with error details if validation failed
            - validated_data: dict with sanitized values if successful
    """
    # Sanitize input
    name = sanitize_input(name_raw)

    # Validate name
    name_valid, name_error = validate_block_name(name)
    if not name_valid:
        return False, f"Block name validation error: {name_error}", None

    return True, None, {"name": name}


def _validate_container_basic_input(name_raw, base_network_raw):
    """
    Validate basic container inputs (name, base network).

    Returns:
        tuple: (is_valid, error_message, validated_data)
            - is_valid: bool indicating if all validations passed
            - error_message: str with error details if validation failed
            - validated_data: dict with sanitized values if successful
    """
    # Sanitize inputs
    name = sanitize_input(name_raw)
    base_network = sanitize_input(base_network_raw)

    # Validate name
    if not name:
        return False, "Container name is required", None

    # Validate base network
    if not base_network:
        return False, "Base network is required", None

    # Validate base network CIDR format
    cidr_valid, cidr_error = validate_cidr_format(base_network)
    if not cidr_valid:
        return False, f"Container network CIDR validation error: {cidr_error}", None

    return True, None, {"name": name, "base_network": base_network}


# Function decomposition helpers for add_subnet
def _check_subnet_conflicts(cidr, vlan_id, block_id, block_name):
    """
    Check for subnet conflicts (VLAN duplicates and CIDR overlaps) within a block.

    Returns:
        tuple: (has_conflict, error_response_or_none)
            - has_conflict: bool indicating if there's a conflict
            - error_response_or_none: rendered error response if conflict, None if no conflict
    """
    # Check for duplicate VLAN in the same block
    if vlan_id:
        is_duplicate_vlan, existing_subnet = check_duplicate_vlan_in_block(vlan_id, block_id)
        if is_duplicate_vlan:
            return True, (
                render_template(
                    "error.html",
                    message=f"VLAN conflict detected in <b>{block_name}</b>. VLAN {vlan_id} already exists.",
                    attempted={"cidr": cidr, "vlan": str(vlan_id), "name": existing_subnet.get("name", "")},
                    conflict=existing_subnet,
                    version=current_app.version,
                ),
                400,
            )

    # Check for overlapping CIDR in the same block
    is_overlapping, existing_subnet = check_overlapping_cidr_in_block(cidr, block_id)
    if is_overlapping:
        return True, (
            render_template(
                "error.html",
                message=f"Network overlap detected in <b>{block_name}</b>. {cidr} overlaps with existing subnet.",
                attempted={"cidr": cidr, "vlan": str(vlan_id) if vlan_id else "", "name": ""},
                overlapping=existing_subnet,
                version=current_app.version,
            ),
            400,
        )

    return False, None


def _create_subnet_from_validated_data(block_id, name, vlan_id, cidr, block_name):
    """
    Create a subnet using the validated data and handle logging.

    Returns:
        tuple: (success, response)
            - success: bool indicating if creation was successful
            - response: success redirect or error response
    """
    # Create subnet using service
    success, subnet, error_msg = DatabaseService.create_subnet(block_id, name, vlan_id, cidr)
    if not success:
        return False, _render_validation_error(
            error_msg, {"cidr": cidr, "vlan": str(vlan_id) if vlan_id else "", "name": name}
        )

    # Log the action
    content = json.dumps(DatabaseService.export_all_data())
    vlan_info = f" VLAN {vlan_id}" if vlan_id else ""
    DatabaseService.add_change_log(
        action="ADD_SUBNET",
        block=block_name,
        details=f"Added subnet '{name}' ({cidr}){vlan_info} to block '{block_name}'",
        content=content,
    )

    flash(f"Subnet '{name}' ({cidr}) added successfully", "success")
    return True, redirect(url_for("main.index"))


# Function decomposition helpers for edit_subnet
def _check_subnet_update_conflicts(cidr, vlan_id, block_id, block_name, exclude_subnet_id):
    """
    Check for subnet conflicts during update (VLAN duplicates and CIDR overlaps) within a block.
    Excludes the current subnet being updated from conflict checks.

    Returns:
        tuple: (has_conflict, error_response_or_none)
            - has_conflict: bool indicating if there's a conflict
            - error_response_or_none: rendered error response if conflict, None if no conflict
    """
    # Check for duplicate VLAN in the same block (excluding current subnet)
    if vlan_id:
        is_duplicate_vlan, existing_subnet = check_duplicate_vlan_in_block(
            vlan_id, block_id, exclude_id=exclude_subnet_id
        )
        if is_duplicate_vlan:
            return True, (
                render_template(
                    "error.html",
                    message=f"VLAN conflict detected in <b>{block_name}</b>. VLAN {vlan_id} already exists.",
                    attempted={"cidr": cidr, "vlan": str(vlan_id), "name": ""},
                    conflict=existing_subnet,
                    version=current_app.version,
                ),
                400,
            )

    # Check for overlapping CIDR in the same block (excluding current subnet)
    is_overlapping, existing_subnet = check_overlapping_cidr_in_block(cidr, block_id, exclude_id=exclude_subnet_id)
    if is_overlapping:
        return True, (
            render_template(
                "error.html",
                message=f"Network overlap detected in <b>{block_name}</b>. " f"{cidr} overlaps with existing subnet.",
                attempted={"cidr": cidr, "vlan": str(vlan_id) if vlan_id else "", "name": ""},
                overlapping=existing_subnet,
                version=current_app.version,
            ),
            400,
        )

    return False, None


def _update_subnet_from_validated_data(subnet_id, name, vlan_id, cidr, block_name):
    """
    Update a subnet using the validated data and handle logging.

    Returns:
        tuple: (success, response)
            - success: bool indicating if update was successful
            - response: success redirect or error response
    """
    # Update subnet using service
    success, error_msg = DatabaseService.update_subnet(subnet_id, name, vlan_id, cidr)
    if not success:
        return False, _render_validation_error(
            error_msg, {"cidr": cidr, "vlan": str(vlan_id) if vlan_id else "", "name": name}
        )

    # Log the action
    content = json.dumps(DatabaseService.export_all_data())
    vlan_info = f" VLAN {vlan_id}" if vlan_id else ""
    DatabaseService.add_change_log(
        action="EDIT_SUBNET",
        block=block_name,
        details=f"Edited subnet '{name}' ({cidr}){vlan_info} in block '{block_name}'",
        content=content,
    )

    flash(f"Subnet '{name}' ({cidr}) updated successfully", "success")
    return True, redirect(url_for("main.index"))
