import logging
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from app.models import db
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
api_bp = Blueprint("api", __name__)


@api_bp.route("/api/health")
def health():
    try:
        # Check if database file exists
        import os

        from app.config import get_db_path

        db_path = get_db_path()
        if not os.path.exists(db_path):
            return (
                jsonify(
                    {
                        "status": "initializing",
                        "message": "Database not initialized yet",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                200,
            )

        # Test database connection by trying to get blocks
        DatabaseService.get_all_blocks()
        return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        # If it's a database table error, the database exists but isn't initialized
        if "no such table" in str(e).lower():
            return (
                jsonify(
                    {
                        "status": "initializing",
                        "message": "Database exists but tables not initialized",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                200,
            )
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@api_bp.route("/api/version")
def version():
    return jsonify({"version": current_app.version, "name": "Outlan IPAM", "status": "alpha"})


@api_bp.route("/api/blocks", methods=["POST"])
def create_block():
    """Create a new network block via REST API"""
    try:
        data = request.get_json()
        if not data or "name" not in data:
            return jsonify({"success": False, "error": "Block name is required"}), 400

        name_raw = data["name"]
        name = sanitize_input(name_raw)

        # Validate block name
        name_valid, name_error = validate_block_name(name)
        if not name_valid:
            return jsonify({"success": False, "error": f"Block name validation error: {name_error}"}), 400

        # Check for duplicate block name
        is_duplicate, existing_block = check_duplicate_block_name(name)
        if is_duplicate:
            return jsonify({"success": False, "error": f"A block with the name '{name}' already exists"}), 400

        # Create block using service
        success, block, error_msg = DatabaseService.create_block(name)
        if not success:
            return jsonify({"success": False, "error": error_msg}), 400

        # Log the action
        content = DatabaseService.export_all_data()
        DatabaseService.add_change_log(
            action="ADD_BLOCK", block=block.name, details=f"Added block '{block.name}' via API", content=content
        )

        return jsonify(
            {
                "success": True,
                "block": {"id": block.id, "name": block.name, "position": block.position, "collapsed": block.collapsed},
            }
        )

    except Exception as e:
        logger.error(f"Error creating block via API: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/api/subnets", methods=["POST"])
def create_subnet():
    """Create a new subnet via REST API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request data is required"}), 400

        required_fields = ["block_id", "name", "cidr"]
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Field '{field}' is required"}), 400

        block_id_raw = data["block_id"]
        name_raw = data["name"]
        cidr_raw = data["cidr"]
        vlan_id_raw = data.get("vlan_id", "")

        # Validate block_id
        try:
            block_id = int(block_id_raw)
        except ValueError:
            return jsonify({"success": False, "error": "Invalid block ID"}), 400

        # Validate block exists
        block = DatabaseService.get_block_by_id(block_id)
        if not block:
            return jsonify({"success": False, "error": "Block not found"}), 404

        # Sanitize and validate inputs
        name = sanitize_input(name_raw)
        cidr = sanitize_input(cidr_raw)

        name_valid, name_error = validate_subnet_name(name)
        if not name_valid:
            return jsonify({"success": False, "error": f"Subnet name validation error: {name_error}"}), 400

        cidr_valid, cidr_error = validate_cidr_format(cidr)
        if not cidr_valid:
            return jsonify({"success": False, "error": f"CIDR validation error: {cidr_error}"}), 400

        # Handle VLAN ID
        vlan_id = None
        if vlan_id_raw:
            vlan_valid, vlan_error = validate_vlan_id(vlan_id_raw)
            if not vlan_valid:
                return jsonify({"success": False, "error": f"VLAN validation error: {vlan_error}"}), 400
            vlan_id = int(vlan_id_raw)

        # Check for duplicate VLAN in the same block
        if vlan_id:
            is_duplicate_vlan, existing_subnet = check_duplicate_vlan_in_block(vlan_id, block_id)
            if is_duplicate_vlan:
                return (
                    jsonify({"success": False, "error": f"VLAN {vlan_id} already exists in block '{block.name}'"}),
                    400,
                )

        # Check for overlapping CIDR in the same block
        is_overlapping, existing_subnet = check_overlapping_cidr_in_block(cidr, block_id)
        if is_overlapping:
            return (
                jsonify(
                    {"success": False, "error": f"Network {cidr} overlaps with existing subnet in block '{block.name}'"}
                ),
                400,
            )

        # Create subnet using service
        success, subnet, error_msg = DatabaseService.create_subnet(block_id, name, vlan_id, cidr)
        if not success:
            return jsonify({"success": False, "error": error_msg}), 400

        # Log the action
        content = DatabaseService.export_all_data()
        vlan_info = f" VLAN {vlan_id}" if vlan_id else ""
        DatabaseService.add_change_log(
            action="ADD_SUBNET",
            block=block.name,
            details=f"Added subnet '{name}' ({cidr}){vlan_info} to block '{block.name}' via API",
            content=content,
        )

        return jsonify(
            {
                "success": True,
                "subnet": {
                    "id": subnet.id,
                    "block_id": subnet.block_id,
                    "name": subnet.name,
                    "cidr": subnet.cidr,
                    "vlan_id": subnet.vlan_id,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error creating subnet via API: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/api/toggle_collapse/<int:block_id>", methods=["POST"])
def toggle_collapse(block_id):
    try:
        block = DatabaseService.get_block_by_id(block_id)
        if not block:
            return jsonify({"success": False, "error": "Block not found"}), 404

        block.collapsed = not block.collapsed
        db.session.commit()

        return jsonify({"success": True, "collapsed": block.collapsed})
    except Exception as e:
        logger.error(f"Error toggling collapse: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/api/update_block_order", methods=["POST"])
def update_block_order():
    try:
        data = request.get_json()
        if not data or "blocks" not in data:
            return jsonify({"success": False, "error": "Invalid data format"}), 400

        for block_data in data["blocks"]:
            block_id = block_data.get("id")
            position = block_data.get("position")
            if block_id and position is not None:
                block = DatabaseService.get_block_by_id(block_id)
                if block:
                    block.position = position

        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating block order: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
