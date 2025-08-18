import json
import logging
import os
from datetime import datetime

from flask import Blueprint, current_app, request
from flask_restx import Api, Namespace, Resource, fields

from app.config import get_db_path
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

# Initialize Flask-RESTX API
api = Api(
    api_bp,
    version="1.0",
    title="Outlan IPAM API",
    description="REST API for Outlan IP Address Management System",
    doc="/swagger/",
    prefix="/api",
)

# Define API models for request/response documentation
health_model = api.model(
    "Health",
    {
        "status": fields.String(description="Health status", example="healthy"),
        "message": fields.String(description="Health message", required=False),
        "timestamp": fields.String(description="ISO timestamp", example="2024-01-01T00:00:00.000000"),
    },
)

version_model = api.model(
    "Version",
    {
        "version": fields.String(description="Application version", example="1.0.0"),
        "name": fields.String(description="Application name", example="Outlan IPAM"),
        "status": fields.String(description="Application status", example="alpha"),
    },
)

error_model = api.model(
    "Error",
    {
        "success": fields.Boolean(description="Success status", example=False),
        "error": fields.String(description="Error message", example="Block not found"),
    },
)

success_model = api.model("Success", {"success": fields.Boolean(description="Success status", example=True)})

# Block models
block_model = api.model(
    "Block",
    {
        "id": fields.Integer(description="Block ID", example=1),
        "name": fields.String(description="Block name", example="Production"),
        "position": fields.Integer(description="Display position", example=0),
        "collapsed": fields.Boolean(description="Collapsed state", example=False),
    },
)

block_create_request = api.model(
    "BlockCreateRequest", {"name": fields.String(required=True, description="Block name", example="Production")}
)

block_update_request = api.model(
    "BlockUpdateRequest",
    {
        "name": fields.String(description="Block name", example="Production"),
        "position": fields.Integer(description="Display position", example=0),
        "collapsed": fields.Boolean(description="Collapsed state", example=False),
    },
)

blocks_response = api.model(
    "BlocksResponse",
    {
        "success": fields.Boolean(description="Success status", example=True),
        "blocks": fields.List(fields.Nested(block_model)),
    },
)

block_response = api.model(
    "BlockResponse",
    {"success": fields.Boolean(description="Success status", example=True), "block": fields.Nested(block_model)},
)

# Block order update model
block_order_item = api.model(
    "BlockOrderItem",
    {
        "id": fields.Integer(required=True, description="Block ID", example=1),
        "position": fields.Integer(required=True, description="New position", example=0),
    },
)

block_order_request = api.model(
    "BlockOrderRequest",
    {
        "blocks": fields.List(
            fields.Nested(block_order_item), required=True, description="List of blocks with new positions"
        )
    },
)

# Network models (formerly subnet models)
network_model = api.model(
    "Network",
    {
        "id": fields.Integer(description="Network ID", example=1),
        "block_id": fields.Integer(description="Parent block ID", example=1),
        "name": fields.String(description="Network name", example="Web Servers"),
        "cidr": fields.String(description="CIDR notation", example="192.168.1.0/24"),
        "vlan_id": fields.Integer(description="VLAN ID", example=100, required=False),
    },
)

network_create_request = api.model(
    "NetworkCreateRequest",
    {
        "block_id": fields.Integer(required=True, description="Parent block ID", example=1),
        "name": fields.String(required=True, description="Network name", example="Web Servers"),
        "cidr": fields.String(required=True, description="CIDR notation", example="192.168.1.0/24"),
        "vlan_id": fields.Integer(description="VLAN ID", example=100, required=False),
    },
)

network_update_request = api.model(
    "NetworkUpdateRequest",
    {
        "name": fields.String(description="Network name", example="Web Servers"),
        "cidr": fields.String(description="CIDR notation", example="192.168.1.0/24"),
        "vlan_id": fields.Integer(description="VLAN ID", example=100, required=False),
    },
)

networks_response = api.model(
    "NetworksResponse",
    {
        "success": fields.Boolean(description="Success status", example=True),
        "networks": fields.List(fields.Nested(network_model)),
    },
)

network_response = api.model(
    "NetworkResponse",
    {"success": fields.Boolean(description="Success status", example=True), "network": fields.Nested(network_model)},
)

# Container models
container_model = api.model(
    "Container",
    {
        "id": fields.Integer(description="Container ID", example=1),
        "block_id": fields.Integer(description="Parent block ID", example=1),
        "name": fields.String(description="Container name", example="Docker Network"),
        "base_network": fields.String(description="Base network CIDR", example="172.16.0.0/16"),
        "position": fields.Integer(description="Display position", example=0),
    },
)

container_create_request = api.model(
    "ContainerCreateRequest",
    {
        "block_id": fields.Integer(required=True, description="Parent block ID", example=1),
        "name": fields.String(required=True, description="Container name", example="Docker Network"),
        "base_network": fields.String(required=True, description="Base network CIDR", example="172.16.0.0/16"),
    },
)

container_update_request = api.model(
    "ContainerUpdateRequest",
    {
        "name": fields.String(description="Container name", example="Docker Network"),
        "base_network": fields.String(description="Base network CIDR", example="172.16.0.0/16"),
        "position": fields.Integer(description="Display position", example=0),
    },
)

containers_response = api.model(
    "ContainersResponse",
    {
        "success": fields.Boolean(description="Success status", example=True),
        "containers": fields.List(fields.Nested(container_model)),
    },
)

container_response = api.model(
    "ContainerResponse",
    {
        "success": fields.Boolean(description="Success status", example=True),
        "container": fields.Nested(container_model),
    },
)

# Create namespaces
health_ns = Namespace("health", description="Health and version endpoints")
blocks_ns = Namespace("blocks", description="Block management operations")
networks_ns = Namespace("networks", description="Network management operations")
containers_ns = Namespace("containers", description="Container management operations")

api.add_namespace(health_ns, path="/")
api.add_namespace(blocks_ns, path="/")
api.add_namespace(containers_ns, path="/")
api.add_namespace(networks_ns, path="/")


@health_ns.route("health")
class Health(Resource):
    @health_ns.doc("get_health")
    @health_ns.marshal_with(health_model)
    def get(self):
        """Check API health status"""
        try:
            # Check if database file exists
            db_path = get_db_path()
            if not os.path.exists(db_path):
                return {
                    "status": "initializing",
                    "message": "Database not initialized yet",
                    "timestamp": datetime.now().isoformat(),
                }, 200

            # Test database connection by trying to get blocks
            DatabaseService.get_all_blocks()
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            # If it's a database table error, the database exists but isn't initialized
            if "no such table" in str(e).lower():
                return {
                    "status": "initializing",
                    "message": "Database exists but tables not initialized",
                    "timestamp": datetime.now().isoformat(),
                }, 200
            return {"status": "unhealthy", "error": str(e)}, 500


@health_ns.route("version")
class Version(Resource):
    @health_ns.doc("get_version")
    @health_ns.marshal_with(version_model)
    def get(self):
        """Get API version information"""
        return {"version": current_app.version, "name": "Outlan IPAM", "status": "alpha"}


@blocks_ns.route("blocks")
class BlockList(Resource):
    @blocks_ns.doc("list_blocks")
    @blocks_ns.marshal_with(blocks_response)
    @blocks_ns.param("search", "Search term to filter blocks", type="string", required=False)
    def get(self):
        """Get all blocks with optional filtering"""
        try:
            search = request.args.get("search", "")
            blocks = DatabaseService.get_all_blocks()

            if search:
                search_lower = search.lower()
                blocks = [block for block in blocks if search_lower in block.name.lower()]

            return {"success": True, "blocks": [block.to_dict() for block in blocks]}
        except Exception as e:
            logger.error(f"Error getting blocks: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500

    @blocks_ns.doc("create_block")
    @blocks_ns.expect(block_create_request)
    def post(self):
        """Create a new network block"""
        try:
            # Handle JSON parsing errors gracefully
            try:
                data = request.get_json()
            except Exception as json_error:
                logger.warning(f"Invalid JSON in create_block: {str(json_error)}")
                return {"success": False, "error": "Invalid JSON format"}, 400
            if not data or "name" not in data:
                return {"success": False, "error": "Block name is required"}, 400

            # Validate parameter types
            name_raw = data["name"]
            if not isinstance(name_raw, str):
                return {"success": False, "error": "Block name must be a string"}, 400
            name = sanitize_input(name_raw)

            # Validate block name
            name_valid, name_error = validate_block_name(name)
            if not name_valid:
                return {"success": False, "error": f"Block name validation error: {name_error}"}, 400

            # Check for duplicate block name
            is_duplicate, existing_block = check_duplicate_block_name(name)
            if is_duplicate:
                return {"success": False, "error": f"A block with the name '{name}' already exists"}, 400

            # Create block using service
            success, block, error_msg = DatabaseService.create_block(name)
            if not success:
                return {"success": False, "error": error_msg}, 400

            # Log the action
            content = json.dumps(DatabaseService.export_all_data())
            DatabaseService.add_change_log(
                action="ADD_BLOCK", block=block.name, details=f"Added block '{block.name}' via API", content=content
            )

            return {"success": True, "block": block.to_dict()}, 201

        except Exception as e:
            logger.error(f"Error creating block via API: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500


@blocks_ns.route("blocks/<int:block_id>")
@blocks_ns.param("block_id", "Block identifier")
class Block(Resource):
    @blocks_ns.doc("get_block")
    def get(self, block_id):
        """Get a specific block by ID"""
        try:
            block = DatabaseService.get_block_by_id(block_id)
            if not block:
                return {"success": False, "error": "Block not found"}, 404

            return {"success": True, "block": block.to_dict()}
        except Exception as e:
            logger.error(f"Error getting block {block_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500

    @blocks_ns.doc("update_block")
    @blocks_ns.expect(block_update_request)
    def put(self, block_id):
        """Update a block"""
        try:
            block = DatabaseService.get_block_by_id(block_id)
            if not block:
                return {"success": False, "error": "Block not found"}, 404

            try:
                data = request.get_json()
            except Exception as json_error:
                logger.warning(f"Invalid JSON in update_block: {str(json_error)}")
                return {"success": False, "error": "Invalid JSON format"}, 400

            if not data:
                return {"success": False, "error": "Request data is required"}, 400

            # Update name if provided
            if "name" in data:
                name_raw = data["name"]
                if not isinstance(name_raw, str):
                    return {"success": False, "error": "Block name must be a string"}, 400

                name = sanitize_input(name_raw)
                name_valid, name_error = validate_block_name(name)
                if not name_valid:
                    return {"success": False, "error": f"Block name validation error: {name_error}"}, 400

                # Check for duplicate name (excluding current block)
                is_duplicate, existing_block = check_duplicate_block_name(name)
                if is_duplicate and existing_block.id != block_id:
                    return {"success": False, "error": f"A block with the name '{name}' already exists"}, 400

                old_name = block.name
                block.name = name

            # Update position if provided
            if "position" in data:
                try:
                    block.position = int(data["position"])
                except (ValueError, TypeError):
                    return {"success": False, "error": "Position must be a valid integer"}, 400

            # Update collapsed state if provided
            if "collapsed" in data:
                block.collapsed = bool(data["collapsed"])

            db.session.commit()

            # Log the action if name changed
            if "name" in data:
                content = json.dumps(DatabaseService.export_all_data())
                DatabaseService.add_change_log(
                    action="UPDATE_BLOCK",
                    block=block.name,
                    details=f"Updated block name from '{old_name}' to '{block.name}' via API",
                    content=content,
                )

            return {"success": True, "block": block.to_dict()}
        except Exception as e:
            logger.error(f"Error updating block {block_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500

    @blocks_ns.doc("delete_block")
    def delete(self, block_id):
        """Delete a block"""
        try:
            block = DatabaseService.get_block_by_id(block_id)
            if not block:
                return {"success": False, "error": "Block not found"}, 404

            block_name = block.name
            success, error_msg = DatabaseService.delete_block(block_id)
            if not success:
                return {"success": False, "error": error_msg}, 400

            # Log the action
            content = json.dumps(DatabaseService.export_all_data())
            DatabaseService.add_change_log(
                action="DELETE_BLOCK",
                block=block_name,
                details=f"Deleted block '{block_name}' via API",
                content=content,
            )

            return {"success": True}
        except Exception as e:
            logger.error(f"Error deleting block {block_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500


@blocks_ns.route("toggle_collapse/<int:block_id>")
@blocks_ns.param("block_id", "Block identifier")
class ToggleCollapse(Resource):
    @blocks_ns.doc("toggle_collapse")
    @blocks_ns.marshal_with(success_model)
    @blocks_ns.marshal_with(error_model, code=404)
    def post(self, block_id):
        """Toggle block collapse state"""
        try:
            block = DatabaseService.get_block_by_id(block_id)
            if not block:
                return {"success": False, "error": "Block not found"}, 404

            block.collapsed = not block.collapsed
            db.session.commit()

            return {"success": True, "collapsed": block.collapsed}
        except Exception as e:
            logger.error(f"Error toggling collapse: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500


@blocks_ns.route("update_block_order")
class BlockOrder(Resource):
    @blocks_ns.doc("update_block_order")
    @blocks_ns.expect(block_order_request)
    @blocks_ns.marshal_with(success_model)
    @blocks_ns.marshal_with(error_model, code=400)
    def post(self):
        """Update the display order of blocks"""
        try:
            # Handle JSON parsing errors gracefully
            try:
                data = request.get_json()
            except Exception as json_error:
                logger.warning(f"Invalid JSON in update_block_order: {str(json_error)}")
                return {"success": False, "error": "Invalid JSON format"}, 400
            if not data or "blocks" not in data:
                return {"success": False, "error": "Invalid data format"}, 400

            for block_data in data["blocks"]:
                block_id = block_data.get("id")
                position = block_data.get("position")
                if block_id and position is not None:
                    block = DatabaseService.get_block_by_id(block_id)
                    if block:
                        block.position = position

            db.session.commit()
            return {"success": True}
        except Exception as e:
            logger.error(f"Error updating block order: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500


# Network endpoints (formerly subnet endpoints)
@networks_ns.route("networks")
class NetworkList(Resource):
    @networks_ns.doc("list_networks")
    @networks_ns.param("block_id", "Filter by block ID", type="integer", required=False)
    @networks_ns.param("search", "Search term to filter networks", type="string", required=False)
    @networks_ns.param("vlan_id", "Filter by VLAN ID", type="integer", required=False)
    def get(self):
        """Get all networks with optional filtering"""
        try:
            # Filter parameters
            block_id = request.args.get("block_id")
            search = request.args.get("search", "")
            vlan_id = request.args.get("vlan_id")

            subnets = DatabaseService.get_all_subnets()  # Note: Still using subnet backend service

            # Apply filters
            if block_id:
                try:
                    block_id_int = int(block_id)
                    subnets = [s for s in subnets if s.block_id == block_id_int]
                except ValueError:
                    return {"success": False, "error": "Block ID must be a valid integer"}, 400

            if search:
                search_lower = search.lower()
                subnets = [
                    s
                    for s in subnets
                    if (
                        search_lower in s.name.lower()
                        or search_lower in s.cidr.lower()
                        or (s.block and search_lower in s.block.name.lower())
                    )
                ]

            if vlan_id:
                try:
                    vlan_id_int = int(vlan_id)
                    subnets = [s for s in subnets if s.vlan_id == vlan_id_int]
                except ValueError:
                    return {"success": False, "error": "VLAN ID must be a valid integer"}, 400

            return {"success": True, "networks": [subnet.to_dict() for subnet in subnets]}  # Return as "networks"
        except Exception as e:
            logger.error(f"Error getting networks: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500

    @networks_ns.doc("create_network")
    @networks_ns.expect(network_create_request)
    def post(self):
        """Create a new network"""
        try:
            # Handle JSON parsing errors gracefully
            try:
                data = request.get_json()
            except Exception as json_error:
                logger.warning(f"Invalid JSON in create_network: {str(json_error)}")
                return {"success": False, "error": "Invalid JSON format"}, 400
            if not data:
                return {"success": False, "error": "Request data is required"}, 400

            required_fields = ["block_id", "name", "cidr"]
            for field in required_fields:
                if field not in data:
                    return {"success": False, "error": f"Field '{field}' is required"}, 400

            block_id_raw = data["block_id"]
            name_raw = data["name"]
            cidr_raw = data["cidr"]
            vlan_id_raw = data.get("vlan_id", "")

            # Validate parameter types
            if not isinstance(name_raw, str):
                return {"success": False, "error": "Network name must be a string"}, 400
            if not isinstance(cidr_raw, str):
                return {"success": False, "error": "CIDR must be a string"}, 400

            # Validate block_id
            try:
                block_id = int(block_id_raw)
            except (ValueError, TypeError):
                return {"success": False, "error": "Block ID must be a valid integer"}, 400

            # Validate block exists
            block = DatabaseService.get_block_by_id(block_id)
            if not block:
                return {"success": False, "error": "Block not found"}, 404

            # Sanitize and validate inputs
            name = sanitize_input(name_raw)
            cidr = sanitize_input(cidr_raw)

            name_valid, name_error = validate_subnet_name(name)  # Note: Still using subnet validation
            if not name_valid:
                return {"success": False, "error": f"Network name validation error: {name_error}"}, 400

            cidr_valid, cidr_error = validate_cidr_format(cidr)
            if not cidr_valid:
                return {"success": False, "error": f"CIDR validation error: {cidr_error}"}, 400

            # Handle VLAN ID
            vlan_id = None
            if vlan_id_raw:
                vlan_valid, vlan_error, vlan_id = validate_vlan_id(str(vlan_id_raw))
                if not vlan_valid:
                    return {"success": False, "error": f"VLAN validation error: {vlan_error}"}, 400

            # Check for duplicate VLAN in the same block
            if vlan_id:
                is_duplicate_vlan, existing_subnet = check_duplicate_vlan_in_block(vlan_id, block_id)
                if is_duplicate_vlan:
                    return {"success": False, "error": f"VLAN {vlan_id} already exists in block '{block.name}'"}, 400

            # Check for overlapping CIDR in the same block
            is_overlapping, existing_subnet = check_overlapping_cidr_in_block(cidr, block_id)
            if is_overlapping:
                return {
                    "success": False,
                    "error": f"Network {cidr} overlaps with existing network in block '{block.name}'",
                }, 400

            # Create subnet using service (backend still uses subnet terminology)
            success, subnet, error_msg = DatabaseService.create_subnet(block_id, name, vlan_id, cidr)
            if not success:
                return {"success": False, "error": error_msg}, 400

            # Log the action
            content = json.dumps(DatabaseService.export_all_data())
            vlan_info = f" VLAN {vlan_id}" if vlan_id else ""
            DatabaseService.add_change_log(
                action="ADD_SUBNET",  # Note: Still using subnet terminology in logs
                block=block.name,
                details=f"Added network '{name}' ({cidr}){vlan_info} to block '{block.name}' via API",
                content=content,
            )

            return {"success": True, "network": subnet.to_dict()}, 201

        except Exception as e:
            logger.error(f"Error creating network via API: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500


@networks_ns.route("networks/<int:network_id>")
@networks_ns.param("network_id", "Network identifier")
class Network(Resource):
    @networks_ns.doc("get_network")
    def get(self, network_id):
        """Get a specific network by ID"""
        try:
            subnet = DatabaseService.get_subnet_by_id(network_id)  # Backend still uses subnet
            if not subnet:
                return {"success": False, "error": "Network not found"}, 404

            return {"success": True, "network": subnet.to_dict()}  # Return as "network"
        except Exception as e:
            logger.error(f"Error getting network {network_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500

    @networks_ns.doc("update_network")
    @networks_ns.expect(network_update_request)
    def put(self, network_id):
        """Update a network"""
        try:
            subnet = DatabaseService.get_subnet_by_id(network_id)  # Backend still uses subnet
            if not subnet:
                return {"success": False, "error": "Network not found"}, 404

            try:
                data = request.get_json()
            except Exception as json_error:
                logger.warning(f"Invalid JSON in update_network: {str(json_error)}")
                return {"success": False, "error": "Invalid JSON format"}, 400

            if not data:
                return {"success": False, "error": "Request data is required"}, 400

            old_data = {"name": subnet.name, "cidr": subnet.cidr, "vlan_id": subnet.vlan_id}

            # Update name if provided
            if "name" in data:
                name_raw = data["name"]
                if not isinstance(name_raw, str):
                    return {"success": False, "error": "Network name must be a string"}, 400

                name = sanitize_input(name_raw)
                name_valid, name_error = validate_subnet_name(name)  # Still using subnet validation
                if not name_valid:
                    return {"success": False, "error": f"Network name validation error: {name_error}"}, 400

                subnet.name = name

            # Update CIDR if provided
            if "cidr" in data:
                cidr_raw = data["cidr"]
                if not isinstance(cidr_raw, str):
                    return {"success": False, "error": "CIDR must be a string"}, 400

                cidr = sanitize_input(cidr_raw)
                cidr_valid, cidr_error = validate_cidr_format(cidr)
                if not cidr_valid:
                    return {"success": False, "error": f"CIDR validation error: {cidr_error}"}, 400

                # Check for overlapping CIDR in the same block (excluding current network)
                is_overlapping, existing_subnet = check_overlapping_cidr_in_block(cidr, subnet.block_id, network_id)
                if is_overlapping:
                    return {
                        "success": False,
                        "error": f"Network {cidr} overlaps with existing network in block '{subnet.block.name}'",
                    }, 400

                subnet.cidr = cidr

            # Update VLAN ID if provided
            if "vlan_id" in data:
                vlan_id_raw = data["vlan_id"]
                if vlan_id_raw is None or vlan_id_raw == "":
                    subnet.vlan_id = None
                else:
                    vlan_valid, vlan_error, vlan_id = validate_vlan_id(str(vlan_id_raw))
                    if not vlan_valid:
                        return {"success": False, "error": f"VLAN validation error: {vlan_error}"}, 400

                    # Check for duplicate VLAN in the same block (excluding current network)
                    is_duplicate_vlan, existing_subnet = check_duplicate_vlan_in_block(
                        vlan_id, subnet.block_id, network_id
                    )
                    if is_duplicate_vlan:
                        return {
                            "success": False,
                            "error": f"VLAN {vlan_id} already exists in block '{subnet.block.name}'",
                        }, 400

                    subnet.vlan_id = vlan_id

            db.session.commit()

            # Log the action
            content = json.dumps(DatabaseService.export_all_data())
            changes = []
            if old_data["name"] != subnet.name:
                changes.append(f"name: '{old_data['name']}' → '{subnet.name}'")
            if old_data["cidr"] != subnet.cidr:
                changes.append(f"CIDR: '{old_data['cidr']}' → '{subnet.cidr}'")
            if old_data["vlan_id"] != subnet.vlan_id:
                changes.append(f"VLAN: {old_data['vlan_id']} → {subnet.vlan_id}")

            if changes:
                DatabaseService.add_change_log(
                    action="UPDATE_SUBNET",  # Still using subnet terminology in logs
                    block=subnet.block.name,
                    details=f"Updated network: {', '.join(changes)} via API",
                    content=content,
                )

            return {"success": True, "network": subnet.to_dict()}  # Return as "network"
        except Exception as e:
            logger.error(f"Error updating network {network_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500

    @networks_ns.doc("delete_network")
    def delete(self, network_id):
        """Delete a network"""
        try:
            subnet = DatabaseService.get_subnet_by_id(network_id)  # Backend still uses subnet
            if not subnet:
                return {"success": False, "error": "Network not found"}, 404

            subnet_name = subnet.name
            block_name = subnet.block.name
            cidr = subnet.cidr
            vlan_info = f" VLAN {subnet.vlan_id}" if subnet.vlan_id else ""

            success, error_msg = DatabaseService.delete_subnet(network_id)  # Backend still uses subnet
            if not success:
                return {"success": False, "error": error_msg}, 400

            # Log the action
            content = json.dumps(DatabaseService.export_all_data())
            DatabaseService.add_change_log(
                action="DELETE_SUBNET",  # Still using subnet terminology in logs
                block=block_name,
                details=f"Deleted network '{subnet_name}' ({cidr}){vlan_info} from block '{block_name}' via API",
                content=content,
            )

            return {"success": True}
        except Exception as e:
            logger.error(f"Error deleting network {network_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500


# Container endpoints (Flask-RESTX version)
@containers_ns.route("containers")
class ContainerList(Resource):
    @containers_ns.doc("list_containers")
    @containers_ns.marshal_with(containers_response)
    @containers_ns.param("block_id", "Filter by block ID", type="integer", required=False)
    @containers_ns.param("search", "Search term to filter containers", type="string", required=False)
    def get(self):
        """Get all containers with optional filtering"""
        try:
            # Filter parameters
            block_id = request.args.get("block_id")
            search = request.args.get("search", "")

            containers = DatabaseService.get_all_containers()

            # Apply filters
            if block_id:
                try:
                    block_id_int = int(block_id)
                    containers = [c for c in containers if c.block_id == block_id_int]
                except ValueError:
                    return {"success": False, "error": "Block ID must be a valid integer"}, 400

            if search:
                search_lower = search.lower()
                containers = [
                    c
                    for c in containers
                    if (
                        search_lower in c.name.lower()
                        or search_lower in c.base_network.lower()
                        or (c.block and search_lower in c.block.name.lower())
                    )
                ]

            return {"success": True, "containers": [container.to_dict() for container in containers]}
        except Exception as e:
            logger.error(f"Error getting containers: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500

    @containers_ns.doc("create_container")
    @containers_ns.expect(container_create_request)
    def post(self):
        """Create a new container"""
        try:
            # Handle JSON parsing errors gracefully
            try:
                data = request.get_json()
            except Exception as json_error:
                logger.warning(f"Invalid JSON in create_container: {str(json_error)}")
                return {"success": False, "error": "Invalid JSON format"}, 400
            if not data:
                return {"success": False, "error": "Request data is required"}, 400

            required_fields = ["block_id", "name", "base_network"]
            for field in required_fields:
                if field not in data:
                    return {"success": False, "error": f"Field '{field}' is required"}, 400

            block_id_raw = data["block_id"]
            name_raw = data["name"]
            base_network_raw = data["base_network"]

            # Validate parameter types
            if not isinstance(name_raw, str):
                return {"success": False, "error": "Container name must be a string"}, 400
            if not isinstance(base_network_raw, str):
                return {"success": False, "error": "Base network must be a string"}, 400

            # Validate block_id
            try:
                block_id = int(block_id_raw)
            except (ValueError, TypeError):
                return {"success": False, "error": "Block ID must be a valid integer"}, 400

            # Validate block exists
            block = DatabaseService.get_block_by_id(block_id)
            if not block:
                return {"success": False, "error": "Block not found"}, 404

            # Sanitize and validate inputs
            name = sanitize_input(name_raw)
            base_network = sanitize_input(base_network_raw)

            # Validate container name is not empty after sanitization
            if not name or len(name.strip()) == 0:
                return {"success": False, "error": "Container name cannot be empty"}, 400

            # Validate base network format (should be CIDR)
            cidr_valid, cidr_error = validate_cidr_format(base_network)
            if not cidr_valid:
                return {"success": False, "error": f"Base network validation error: {cidr_error}"}, 400

            # Create container using service
            success, container, error_msg = DatabaseService.create_container(block_id, name, base_network)
            if not success:
                return {"success": False, "error": error_msg}, 400

            # Log the action
            content = json.dumps(DatabaseService.export_all_data())
            DatabaseService.add_change_log(
                action="ADD_CONTAINER",
                block=block.name,
                details=f"Added container '{name}' ({base_network}) to block '{block.name}' via API",
                content=content,
            )

            return {"success": True, "container": container.to_dict()}, 201

        except Exception as e:
            logger.error(f"Error creating container via API: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500


@containers_ns.route("containers/<int:container_id>")
@containers_ns.param("container_id", "Container identifier")
class Container(Resource):
    @containers_ns.doc("get_container")
    def get(self, container_id):
        """Get a specific container by ID"""
        try:
            container = DatabaseService.get_container_by_id(container_id)
            if not container:
                return {"success": False, "error": "Container not found"}, 404

            return {"success": True, "container": container.to_dict()}
        except Exception as e:
            logger.error(f"Error getting container {container_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500

    @containers_ns.doc("update_container")
    @containers_ns.expect(container_update_request)
    def put(self, container_id):
        """Update a container"""
        try:
            container = DatabaseService.get_container_by_id(container_id)
            if not container:
                return {"success": False, "error": "Container not found"}, 404

            try:
                data = request.get_json()
            except Exception as json_error:
                logger.warning(f"Invalid JSON in update_container: {str(json_error)}")
                return {"success": False, "error": "Invalid JSON format"}, 400

            if not data:
                return {"success": False, "error": "Request data is required"}, 400

            old_data = {"name": container.name, "base_network": container.base_network, "position": container.position}

            # Update name if provided
            if "name" in data:
                name_raw = data["name"]
                if not isinstance(name_raw, str):
                    return {"success": False, "error": "Container name must be a string"}, 400

                name = sanitize_input(name_raw)
                container.name = name

            # Update base_network if provided
            if "base_network" in data:
                base_network_raw = data["base_network"]
                if not isinstance(base_network_raw, str):
                    return {"success": False, "error": "Base network must be a string"}, 400

                base_network = sanitize_input(base_network_raw)
                cidr_valid, cidr_error = validate_cidr_format(base_network)
                if not cidr_valid:
                    return {"success": False, "error": f"Base network validation error: {cidr_error}"}, 400

                container.base_network = base_network

            # Update position if provided
            if "position" in data:
                try:
                    container.position = int(data["position"])
                except (ValueError, TypeError):
                    return {"success": False, "error": "Position must be a valid integer"}, 400

            db.session.commit()

            # Log the action
            content = json.dumps(DatabaseService.export_all_data())
            changes = []
            if old_data["name"] != container.name:
                changes.append(f"name: '{old_data['name']}' → '{container.name}'")
            if old_data["base_network"] != container.base_network:
                changes.append(f"base network: '{old_data['base_network']}' → '{container.base_network}'")
            if old_data["position"] != container.position:
                changes.append(f"position: {old_data['position']} → {container.position}")

            if changes:
                DatabaseService.add_change_log(
                    action="UPDATE_CONTAINER",
                    block=container.block.name,
                    details=f"Updated container: {', '.join(changes)} via API",
                    content=content,
                )

            return {"success": True, "container": container.to_dict()}
        except Exception as e:
            logger.error(f"Error updating container {container_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500

    @containers_ns.doc("delete_container")
    def delete(self, container_id):
        """Delete a container"""
        try:
            container = DatabaseService.get_container_by_id(container_id)
            if not container:
                return {"success": False, "error": "Container not found"}, 404

            container_name = container.name
            block_name = container.block.name
            base_network = container.base_network

            success, error_msg = DatabaseService.delete_container(container_id)
            if not success:
                return {"success": False, "error": error_msg}, 400

            # Log the action
            content = json.dumps(DatabaseService.export_all_data())
            DatabaseService.add_change_log(
                action="DELETE_CONTAINER",
                block=block_name,
                details=f"Deleted container '{container_name}' ({base_network}) from block '{block_name}' via API",
                content=content,
            )

            return {"success": True}
        except Exception as e:
            logger.error(f"Error deleting container {container_id}: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500
