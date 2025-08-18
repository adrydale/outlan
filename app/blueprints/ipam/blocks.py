"""
Block operations for IPAM.

This module handles network block creation, deletion, renaming, and management operations.
"""

import json
import logging

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.utils import DatabaseService
from app.utils.validation import check_duplicate_block_name

from .helpers import _get_attempted_block_data, _render_validation_error, _validate_block_basic_input

logger = logging.getLogger(__name__)


blocks_bp = Blueprint("ipam_blocks", __name__)


@blocks_bp.route("/add_block", methods=["POST"])
def add_block_route():
    try:
        name_raw = request.form.get("block_name", "")

        # Validate basic inputs using helper function
        is_valid, error_message, validated_data = _validate_block_basic_input(name_raw)
        if not is_valid:
            return _render_validation_error(error_message, _get_attempted_block_data(request.form))

        name = validated_data["name"]

        # Check for duplicate block name
        is_duplicate, existing_block = check_duplicate_block_name(name)
        if is_duplicate:
            return _render_validation_error(
                f"A block with the name '{name}' already exists. Please choose a different name.",
                _get_attempted_block_data(request.form),
            )

        # Create block using service
        success, block, error_msg = DatabaseService.create_block(name)
        if not success:
            return _render_validation_error(error_msg, _get_attempted_block_data(request.form))

        # Log the action
        content = json.dumps(DatabaseService.export_all_data())
        DatabaseService.add_change_log(action="ADD_BLOCK", block=name, details=f"Added block '{name}'", content=content)

        flash(f"Block '{name}' added successfully", "success")
        return redirect(url_for("main.index"))

    except Exception as e:
        logger.error(f"Unexpected error in add_block_route: {str(e)}", exc_info=True)
        return _render_validation_error(
            "An unexpected error occurred",
            {"cidr": None, "vlan": None, "name": name_raw if "name_raw" in locals() else ""},
            500,
        )


@blocks_bp.route("/rename_block/<int:block_id>", methods=["POST"])
def rename_block(block_id):
    try:
        new_name_raw = request.form.get("new_block_name", "")

        # Validate basic inputs using helper function
        is_valid, error_message, validated_data = _validate_block_basic_input(new_name_raw)
        if not is_valid:
            return _render_validation_error(error_message, _get_attempted_block_data(request.form))

        new_name = validated_data["name"]

        # Check for duplicate block name (excluding current block)
        is_duplicate, existing_block = check_duplicate_block_name(new_name, exclude_id=block_id)
        if is_duplicate:
            return _render_validation_error(
                f"A block with the name '<b>{new_name}</b>' already exists. Please choose a different name.",
                _get_attempted_block_data(request.form),
            )

        # Update block using service
        success, old_name, error_msg = DatabaseService.update_block_name(block_id, new_name)
        if not success:
            return _render_validation_error(error_msg, _get_attempted_block_data(request.form))

        # Log the action
        content = json.dumps(DatabaseService.export_all_data())
        DatabaseService.add_change_log(
            action="RENAME_BLOCK",
            block=old_name,
            details=f"Renamed block from '{old_name}' to '{new_name}'",
            content=content,
        )

        flash(f"Block renamed to '{new_name}' successfully", "success")
        return redirect(url_for("main.index"))

    except Exception as e:
        logger.error(f"Unexpected error in rename_block: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="An unexpected error occurred",
                attempted={"cidr": None, "vlan": None, "name": new_name_raw if "new_name_raw" in locals() else ""},
                version=current_app.version,
            ),
            500,
        )


@blocks_bp.route("/delete_block/<int:block_id>", methods=["POST"])
def delete_block(block_id):
    try:
        # Delete block using service
        success, block_name = DatabaseService.delete_block(block_id)
        if not success:
            return _render_validation_error(block_name, {"cidr": None, "vlan": None, "name": None})  # error message

        # Log the action
        content = json.dumps(DatabaseService.export_all_data())
        DatabaseService.add_change_log(
            action="DELETE_BLOCK", block=block_name, details=f"Deleted block '{block_name}'", content=content
        )

        flash(f"Block '{block_name}' deleted successfully", "success")
        return redirect(url_for("main.index"))

    except Exception as e:
        logger.error(f"Unexpected error in delete_block: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="An unexpected error occurred",
                attempted={"cidr": None, "vlan": None, "name": None},
                version=current_app.version,
            ),
            500,
        )
