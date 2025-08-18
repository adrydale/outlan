"""
Container operations for IPAM.

This module handles container creation, deletion, and management operations.
"""

import json
import logging

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.utils import DatabaseService
from app.utils.validation import check_overlapping_container_networks

from .helpers import _get_attempted_container_data, _render_validation_error, _validate_container_basic_input

logger = logging.getLogger(__name__)


containers_bp = Blueprint("ipam_containers", __name__)


@containers_bp.route("/add_container", methods=["POST"])
def add_container_route():
    try:
        name_raw = request.form.get("container_name", "")
        base_network_raw = request.form.get("base_network", "")
        block_id_raw = request.form.get("block_id", "")

        # Validate block ID first
        if not block_id_raw:
            flash("Block ID is required", "error")
            return redirect(url_for("main.index"))

        try:
            block_id = int(block_id_raw)
        except ValueError:
            flash("Invalid block ID", "error")
            return redirect(url_for("main.index"))

        # Validate container inputs using helper function
        is_valid, error_message, validated_data = _validate_container_basic_input(name_raw, base_network_raw)
        if not is_valid:
            return _render_validation_error(error_message, _get_attempted_container_data(request.form))

        name = validated_data["name"]
        base_network = validated_data["base_network"]

        # Check for overlapping container networks
        is_overlapping, existing_container = check_overlapping_container_networks(base_network, block_id)
        if is_overlapping:
            # Get the current block name for the attempted add
            block = DatabaseService.get_block_by_id(block_id)
            current_block_name = block.name if block else "Unknown Block"

            return (
                render_template(
                    "error.html",
                    message=(
                        f"Container network overlap detected. {base_network} overlaps with existing "
                        f"container '{existing_container['name']}' ({existing_container['base_network']}) "
                        f"in block '{existing_container['block_name']}'."
                    ),
                    attempted={
                        "cidr": base_network_raw,
                        "vlan": None,
                        "name": name_raw,
                        "block_name": current_block_name,
                    },
                    overlapping=existing_container,
                    version=current_app.version,
                ),
                400,
            )

        # Create container using service
        success, container, error_msg = DatabaseService.create_container(block_id, name, base_network)
        if not success:
            flash(f"Error creating container: {error_msg}", "error")
            return redirect(url_for("main.index"))

        # Log the action
        block = DatabaseService.get_block_by_id(block_id)
        block_name = block.name if block else "Unknown"
        content = json.dumps(DatabaseService.export_all_data())
        DatabaseService.add_change_log(
            action="ADD_CONTAINER",
            block=block_name,
            details=f"Added container '{name}' with base network '{base_network}'",
            content=content,
        )

        flash(f"Container '{name}' added successfully", "success")
        return redirect(url_for("main.index"))

    except Exception as e:
        logger.error(f"Unexpected error in add_container_route: {str(e)}", exc_info=True)
        flash("An unexpected error occurred while adding container", "error")
        return redirect(url_for("main.index"))


@containers_bp.route("/delete_container/<int:container_id>", methods=["POST"])
def delete_container_route(container_id):
    try:
        # Get container info before deletion
        container = DatabaseService.get_container_by_id(container_id)
        if not container:
            flash("Container not found", "error")
            return redirect(url_for("main.index"))

        container_name = container.name
        block_name = container.block.name if container.block else "Unknown"

        # Delete container
        success, error_msg = DatabaseService.delete_container(container_id)
        if not success:
            flash(f"Error deleting container: {error_msg}", "error")
            return redirect(url_for("main.index"))

        # Log the action
        content = json.dumps(DatabaseService.export_all_data())
        DatabaseService.add_change_log(
            action="DELETE_CONTAINER",
            block=block_name,
            details=f"Deleted container '{container_name}'",
            content=content,
        )

        flash(f"Container '{container_name}' deleted successfully", "success")
        return redirect(url_for("main.index"))

    except Exception as e:
        logger.error(f"Unexpected error in delete_container_route: {str(e)}", exc_info=True)
        flash("An unexpected error occurred while deleting container", "error")
        return redirect(url_for("main.index"))
