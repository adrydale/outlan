import json
import logging

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.utils import DatabaseService
from app.utils.validation import (
    check_duplicate_block_name,
    check_duplicate_vlan_in_block,
    check_overlapping_cidr_in_block,
    sanitize_input,
    validate_block_name,
    validate_cidr_format,
    validate_subnet_name,
    validate_vlan_id,
)

logger = logging.getLogger(__name__)
ipam_bp = Blueprint("ipam", __name__)


@ipam_bp.route("/add_block", methods=["POST"])
def add_block_route():
    try:
        name_raw = request.form.get("block_name", "")
        name = sanitize_input(name_raw)
        name_valid, name_error = validate_block_name(name)
        if not name_valid:
            return (
                render_template(
                    "error.html",
                    message=f"Block name validation error: {name_error}",
                    attempted={"cidr": None, "vlan": None, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        # Check for duplicate block name
        is_duplicate, existing_block = check_duplicate_block_name(name)
        if is_duplicate:
            return (
                render_template(
                    "error.html",
                    message=f"A block with the name '<b>{name}</b>' already exists. Please choose a different name.",
                    attempted={"cidr": None, "vlan": None, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        # Create block using service
        success, block, error_msg = DatabaseService.create_block(name)
        if not success:
            return (
                render_template(
                    "error.html",
                    message=error_msg,
                    attempted={"cidr": None, "vlan": None, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        # Log the action
        content = json.dumps(DatabaseService.export_all_data())
        DatabaseService.add_change_log(action="ADD_BLOCK", block=name, details=f"Added block '{name}'", content=content)

        flash(f"Block '{name}' added successfully", "success")
        return redirect(url_for("main.index"))

    except Exception as e:
        logger.error(f"Unexpected error in add_block_route: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="An unexpected error occurred",
                attempted={"cidr": None, "vlan": None, "name": name_raw if "name_raw" in locals() else ""},
                version=current_app.version,
            ),
            500,
        )


@ipam_bp.route("/rename_block/<int:block_id>", methods=["POST"])
def rename_block(block_id):
    try:
        new_name_raw = request.form.get("new_block_name", "")
        new_name = sanitize_input(new_name_raw)
        name_valid, name_error = validate_block_name(new_name)
        if not name_valid:
            return (
                render_template(
                    "error.html",
                    message=f"Block name validation error: {name_error}",
                    attempted={"cidr": None, "vlan": None, "name": new_name_raw},
                    version=current_app.version,
                ),
                400,
            )

        # Check for duplicate block name (excluding current block)
        is_duplicate, existing_block = check_duplicate_block_name(new_name, exclude_id=block_id)
        if is_duplicate:
            return (
                render_template(
                    "error.html",
                    message=f"A block with the name '<b>{new_name}</b>' already exists. "
                    "Please choose a different name.",
                    attempted={"cidr": None, "vlan": None, "name": new_name_raw},
                    version=current_app.version,
                ),
                400,
            )

        # Update block using service
        success, old_name, error_msg = DatabaseService.update_block_name(block_id, new_name)
        if not success:
            return (
                render_template(
                    "error.html",
                    message=error_msg,
                    attempted={"cidr": None, "vlan": None, "name": new_name_raw},
                    version=current_app.version,
                ),
                400,
            )

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


@ipam_bp.route("/delete_block/<int:block_id>", methods=["POST"])
def delete_block(block_id):
    try:
        # Delete block using service
        success, block_name = DatabaseService.delete_block(block_id)
        if not success:
            return (
                render_template(
                    "error.html",
                    message=block_name,  # error message
                    attempted={"cidr": None, "vlan": None, "name": None},
                    version=current_app.version,
                ),
                400,
            )

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


@ipam_bp.route("/add_subnet", methods=["POST"])
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
            return (
                render_template(
                    "error.html",
                    message="Block ID is required",
                    attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        try:
            block_id = int(block_id_raw)
        except ValueError:
            return (
                render_template(
                    "error.html",
                    message="Invalid block ID",
                    attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        # Validate block exists
        block = DatabaseService.get_block_by_id(block_id)
        if not block:
            return (
                render_template(
                    "error.html",
                    message="Block not found",
                    attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        # Sanitize and validate inputs
        name = sanitize_input(name_raw)
        cidr = sanitize_input(cidr_raw)

        name_valid, name_error = validate_subnet_name(name)
        if not name_valid:
            logger.warning(f"Subnet name validation failed: {name_error} for input '{name_raw}'")
            return (
                render_template(
                    "error.html",
                    message=f"Subnet name validation error: {name_error}",
                    attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        cidr_valid, cidr_error = validate_cidr_format(cidr)
        if not cidr_valid:
            return (
                render_template(
                    "error.html",
                    message=f"CIDR validation error: {cidr_error}",
                    attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        # Validate VLAN ID
        vlan_id = None
        if vlan_id_raw:
            vlan_valid, vlan_error, cleaned_vlan = validate_vlan_id(vlan_id_raw)
            if not vlan_valid:
                return (
                    render_template(
                        "error.html",
                        message=f"VLAN validation error: {vlan_error}",
                        attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                        version=current_app.version,
                    ),
                    400,
                )
            vlan_id = cleaned_vlan

        # Check for duplicate VLAN in the same block
        if vlan_id:
            is_duplicate_vlan, existing_subnet = check_duplicate_vlan_in_block(vlan_id, block_id)
            if is_duplicate_vlan:
                return (
                    render_template(
                        "error.html",
                        message=f"VLAN conflict detected in <b>{block.name}</b>. VLAN {vlan_id} already exists.",
                        attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                        conflict=existing_subnet,
                        version=current_app.version,
                    ),
                    400,
                )

        # Check for overlapping CIDR in the same block
        is_overlapping, existing_subnet = check_overlapping_cidr_in_block(cidr, block_id)
        if is_overlapping:
            return (
                render_template(
                    "error.html",
                    message=f"Network overlap detected in <b>{block.name}</b>. {cidr} overlaps with existing subnet.",
                    attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                    overlapping=existing_subnet,
                    version=current_app.version,
                ),
                400,
            )

        # Create subnet using service
        success, subnet, error_msg = DatabaseService.create_subnet(block_id, name, vlan_id, cidr)
        if not success:
            return (
                render_template(
                    "error.html",
                    message=error_msg,
                    attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        # Log the action
        content = json.dumps(DatabaseService.export_all_data())
        vlan_info = f" VLAN {vlan_id}" if vlan_id else ""
        DatabaseService.add_change_log(
            action="ADD_SUBNET",
            block=block.name,
            details=f"Added subnet '{name}' ({cidr}){vlan_info} to block '{block.name}'",
            content=content,
        )

        flash(f"Subnet '{name}' ({cidr}) added successfully", "success")
        return redirect(url_for("main.index"))

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


@ipam_bp.route("/edit_subnet/<int:subnet_id>", methods=["POST"])
def edit_subnet(subnet_id):
    try:
        name_raw = request.form.get("name", "")  # Changed from "subnet_name" to "name"
        vlan_id_raw = request.form.get("vlan_id", "")
        cidr_raw = request.form.get("cidr", "")

        # Get existing subnet
        subnet = DatabaseService.get_subnet_by_id(subnet_id)
        if not subnet:
            return (
                render_template(
                    "error.html",
                    message="Subnet not found",
                    attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        # Sanitize and validate inputs
        name = sanitize_input(name_raw)
        cidr = sanitize_input(cidr_raw)

        name_valid, name_error = validate_subnet_name(name)
        if not name_valid:
            return (
                render_template(
                    "error.html",
                    message=f"Subnet name validation error: {name_error}",
                    attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        cidr_valid, cidr_error = validate_cidr_format(cidr)
        if not cidr_valid:
            return (
                render_template(
                    "error.html",
                    message=f"CIDR validation error: {cidr_error}",
                    attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        # Validate VLAN ID
        vlan_id = None
        if vlan_id_raw:
            vlan_valid, vlan_error, cleaned_vlan = validate_vlan_id(vlan_id_raw)
            if not vlan_valid:
                return (
                    render_template(
                        "error.html",
                        message=f"VLAN validation error: {vlan_error}",
                        attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                        version=current_app.version,
                    ),
                    400,
                )
            vlan_id = cleaned_vlan

        # Check for duplicate VLAN in the same block (excluding current subnet)
        if vlan_id:
            is_duplicate_vlan, existing_subnet = check_duplicate_vlan_in_block(
                vlan_id, subnet.block_id, exclude_id=subnet_id
            )
            if is_duplicate_vlan:
                return (
                    render_template(
                        "error.html",
                        message=f"VLAN conflict detected in <b>{subnet.block.name}</b>. VLAN {vlan_id} already exists.",
                        attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                        conflict=existing_subnet,
                        version=current_app.version,
                    ),
                    400,
                )

        # Check for overlapping CIDR in the same block (excluding current subnet)
        is_overlapping, existing_subnet = check_overlapping_cidr_in_block(cidr, subnet.block_id, exclude_id=subnet_id)
        if is_overlapping:
            return (
                render_template(
                    "error.html",
                    message=f"Network overlap detected in <b>{subnet.block.name}</b>. "
                    f"{cidr} overlaps with existing subnet.",
                    attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                    overlapping=existing_subnet,
                    version=current_app.version,
                ),
                400,
            )

        # Update subnet using service
        success, error_msg = DatabaseService.update_subnet(subnet_id, name, vlan_id, cidr)
        if not success:
            return (
                render_template(
                    "error.html",
                    message=error_msg,
                    attempted={"cidr": cidr_raw, "vlan": vlan_id_raw, "name": name_raw},
                    version=current_app.version,
                ),
                400,
            )

        # Log the action
        content = json.dumps(DatabaseService.export_all_data())
        vlan_info = f" VLAN {vlan_id}" if vlan_id else ""
        DatabaseService.add_change_log(
            action="EDIT_SUBNET",
            block=subnet.block.name,
            details=f"Edited subnet '{name}' ({cidr}){vlan_info} in block '{subnet.block.name}'",
            content=content,
        )

        flash(f"Subnet '{name}' ({cidr}) updated successfully", "success")
        return redirect(url_for("main.index"))

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


@ipam_bp.route("/delete_subnet/<int:subnet_id>", methods=["POST"])
def delete_subnet(subnet_id):
    try:
        # Get subnet for logging
        subnet = DatabaseService.get_subnet_by_id(subnet_id)
        if not subnet:
            return (
                render_template(
                    "error.html",
                    message="Subnet not found",
                    attempted={"cidr": None, "vlan": None, "name": None},
                    version=current_app.version,
                ),
                400,
            )

        block_name = subnet.block.name
        subnet_name = subnet.name
        subnet_cidr = subnet.cidr
        subnet_vlan = subnet.vlan_id

        # Delete subnet using service
        success, error_msg = DatabaseService.delete_subnet(subnet_id)
        if not success:
            return (
                render_template(
                    "error.html",
                    message=error_msg,
                    attempted={"cidr": None, "vlan": None, "name": None},
                    version=current_app.version,
                ),
                400,
            )

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


@ipam_bp.route("/export_csv/<int:block_id>")
def export_csv(block_id):
    try:
        # Get block
        block = DatabaseService.get_block_by_id(block_id)
        if not block:
            return (
                render_template(
                    "error.html",
                    message="Block not found",
                    attempted={"cidr": None, "vlan": None, "name": None},
                    version=current_app.version,
                ),
                400,
            )

        # Get subnets for this block
        subnets = [s for s in DatabaseService.get_all_subnets() if s.block_id == block_id]

        # Generate CSV
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Block", "Subnet Name", "VLAN ID", "CIDR"])

        for subnet in subnets:
            writer.writerow([block.name, subnet.name, subnet.vlan_id or "", subnet.cidr])

        output.seek(0)

        from flask import Response

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{block.name}_subnets.csv"'},
        )

    except Exception as e:
        logger.error(f"Error exporting CSV: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="Error exporting CSV",
                attempted={"cidr": None, "vlan": None, "name": None},
                version=current_app.version,
            ),
            500,
        )
