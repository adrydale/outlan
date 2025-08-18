"""
Subnet operations for IPAM.

This module handles subnet creation, editing, deletion, and management operations.
"""

import json
import logging

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.utils import DatabaseService

from .helpers import (
    _check_subnet_conflicts,
    _check_subnet_update_conflicts,
    _create_subnet_from_validated_data,
    _get_attempted_subnet_data,
    _render_validation_error,
    _update_subnet_from_validated_data,
    _validate_subnet_basic_input,
)

logger = logging.getLogger(__name__)


subnets_bp = Blueprint("ipam_subnets", __name__)


@subnets_bp.route("/add_subnet", methods=["POST"])
def add_subnet():
    try:
        block_id_raw = request.form.get("block_id", "")
        name_raw = request.form.get("name", "")  # Changed from "subnet_name" to "name"
        vlan_id_raw = request.form.get("vlan_id", "")
        cidr_raw = request.form.get("cidr", "")

        # Debug logging
        logger.info(
            f"Add subnet form data: block_id={block_id_raw}, name={name_raw}, vlan_id={vlan_id_raw}, cidr={cidr_raw}"
        )

        # Validate inputs
        if not block_id_raw:
            return _render_validation_error(
                "Block ID is required", {"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw}
            )

        try:
            block_id = int(block_id_raw)
        except ValueError:
            return _render_validation_error(
                "Invalid block ID", {"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw}
            )

        # Validate block exists
        block = DatabaseService.get_block_by_id(block_id)
        if not block:
            return _render_validation_error("Block not found", _get_attempted_subnet_data(request.form))

        # Validate basic inputs using helper function
        is_valid, error_message, validated_data = _validate_subnet_basic_input(name_raw, cidr_raw, vlan_id_raw)
        if not is_valid:
            if "name" in error_message:
                logger.warning(f"Subnet name validation failed: {error_message} for input '{name_raw}'")
            return _render_validation_error(error_message, _get_attempted_subnet_data(request.form))

        name = validated_data["name"]
        cidr = validated_data["cidr"]
        vlan_id = validated_data["vlan_id"]

        # Check for conflicts using helper function
        has_conflict, conflict_response = _check_subnet_conflicts(cidr, vlan_id, block_id, block.name)
        if has_conflict:
            return conflict_response

        # Create subnet using helper function
        success, response = _create_subnet_from_validated_data(block_id, name, vlan_id, cidr, block.name)
        return response

    except Exception as e:
        logger.error(f"Unexpected error in add_subnet: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="An unexpected error occurred",
                attempted={
                    "cidr": cidr_raw if "cidr_raw" in locals() else "",
                    "vlan": vlan_id_raw if "vlan_id_raw" in locals() else "",
                    "name": name_raw if "name_raw" in locals() else "",
                },
                version=current_app.version,
            ),
            500,
        )


@subnets_bp.route("/edit_subnet/<int:subnet_id>", methods=["POST"])
def edit_subnet(subnet_id):
    try:
        name_raw = request.form.get("name", "")  # Changed from "subnet_name" to "name"
        vlan_id_raw = request.form.get("vlan_id", "")
        cidr_raw = request.form.get("cidr", "")

        # Get existing subnet
        subnet = DatabaseService.get_subnet_by_id(subnet_id)
        if not subnet:
            return _render_validation_error("Subnet not found", _get_attempted_subnet_data(request.form))

        # Validate basic inputs using helper function
        is_valid, error_message, validated_data = _validate_subnet_basic_input(name_raw, cidr_raw, vlan_id_raw)
        if not is_valid:
            return _render_validation_error(error_message, _get_attempted_subnet_data(request.form))

        name = validated_data["name"]
        cidr = validated_data["cidr"]
        vlan_id = validated_data["vlan_id"]

        # Check for conflicts using helper function
        has_conflict, conflict_response = _check_subnet_update_conflicts(
            cidr, vlan_id, subnet.block_id, subnet.block.name, subnet_id
        )
        if has_conflict:
            return conflict_response

        # Update subnet using helper function
        success, response = _update_subnet_from_validated_data(subnet_id, name, vlan_id, cidr, subnet.block.name)
        return response

    except Exception as e:
        logger.error(f"Unexpected error in edit_subnet: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="An unexpected error occurred",
                attempted={
                    "cidr": cidr_raw if "cidr_raw" in locals() else "",
                    "vlan": vlan_id_raw if "vlan_id_raw" in locals() else "",
                    "name": name_raw if "name_raw" in locals() else "",
                },
                version=current_app.version,
            ),
            500,
        )


@subnets_bp.route("/delete_subnet/<int:subnet_id>", methods=["POST"])
def delete_subnet(subnet_id):
    try:
        # Get subnet for logging
        subnet = DatabaseService.get_subnet_by_id(subnet_id)
        if not subnet:
            return _render_validation_error("Subnet not found", {"cidr": None, "vlan": None, "name": None})

        block_name = subnet.block.name
        subnet_name = subnet.name
        subnet_cidr = subnet.cidr
        subnet_vlan = subnet.vlan_id

        # Delete subnet using service
        success, error_msg = DatabaseService.delete_subnet(subnet_id)
        if not success:
            return _render_validation_error(error_msg, {"cidr": None, "vlan": None, "name": None})

        # Log the action
        content = json.dumps(DatabaseService.export_all_data())
        vlan_info = f" VLAN {subnet_vlan}" if subnet_vlan else ""
        DatabaseService.add_change_log(
            action="DELETE_SUBNET",
            block=block_name,
            details=f"Deleted subnet '{subnet_name}' ({subnet_cidr}){vlan_info} from block '{block_name}'",
            content=content,
        )

        flash(f"Subnet '{subnet_name}' ({subnet_cidr}) deleted successfully", "success")
        return redirect(url_for("main.index"))

    except Exception as e:
        logger.error(f"Unexpected error in delete_subnet: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="An unexpected error occurred",
                attempted={"cidr": None, "vlan": None, "name": None},
                version=current_app.version,
            ),
            500,
        )
