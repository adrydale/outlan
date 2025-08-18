import ipaddress
import logging
from datetime import datetime

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for

from app.config import get_theme
from app.utils import DatabaseService

logger = logging.getLogger(__name__)
segment_bp = Blueprint("segment", __name__, url_prefix="/segment")


def validate_cidr(cidr_str):
    """Validate CIDR format and return network object.

    Args:
        cidr_str: CIDR notation string to validate

    Returns:
        IPv4Network: Valid network object, or None if invalid
    """
    try:
        network = ipaddress.ip_network(cidr_str, strict=False)
        return network
    except ValueError:
        return None


def check_allocation_overlap(base_network, allocations, new_allocation, exclude_id=None):
    """Check if new allocation overlaps with existing ones.

    Args:
        base_network: Base network CIDR string
        allocations: List of existing allocation dictionaries
        new_allocation: New allocation CIDR string to check
        exclude_id: Optional allocation ID to exclude from overlap check

    Returns:
        str or None: Error message if overlap found, None if valid
    """
    try:
        base_net = ipaddress.ip_network(base_network, strict=False)
        new_net = ipaddress.ip_network(new_allocation, strict=False)

        # Check if new allocation is within base network
        if not new_net.subnet_of(base_net):
            return "Allocation must be within the base network"

        # Check for overlaps with existing allocations
        for alloc in allocations:
            # Skip the allocation we're updating
            if exclude_id and alloc.get("id") == exclude_id:
                continue

            existing_net = ipaddress.ip_network(alloc["cidr"], strict=False)
            if new_net.overlaps(existing_net):
                return f"Allocation overlaps with existing allocation: {alloc['cidr']}"

        return None
    except ValueError as e:
        return f"Invalid network format: {str(e)}"


def calculate_network_usage(base_network, allocations):
    """Calculate network usage statistics for a given network.

    Args:
        base_network: Base network CIDR string
        allocations: List of allocation dictionaries within the network

    Returns:
        dict: Usage statistics including total IPs, used IPs, and percentage
    """
    try:
        base_net = ipaddress.ip_network(base_network, strict=False)
        total_hosts = base_net.num_addresses
        used_hosts = 0

        for alloc in allocations:
            alloc_net = ipaddress.ip_network(alloc["cidr"], strict=False)
            used_hosts += alloc_net.num_addresses

        return {
            "total_hosts": total_hosts,
            "used_hosts": used_hosts,
            "free_hosts": total_hosts - used_hosts,
            "usage_percent": (used_hosts / total_hosts) * 100 if total_hosts > 0 else 0,
        }
    except ValueError:
        return {"total_hosts": 0, "used_hosts": 0, "free_hosts": 0, "usage_percent": 0}


@segment_bp.route("/container/<int:container_id>")
def view_container_segment(container_id):
    """View a container as a network segment with visualization"""
    try:
        # Get the container
        container = DatabaseService.get_container_by_id(container_id)
        if not container:
            flash(f"Container with ID {container_id} not found", "error")
            return redirect(url_for("main.index"))

        # Get all subnets for the block that this container belongs to
        # Note: This will show ALL subnets in the block, but only visualize those within the container's base_network
        subnets = DatabaseService.get_subnets_by_block_id(container.block_id)

        # Filter subnets that fall within the container's base network and convert to allocation format
        allocations = []
        try:
            container_net = ipaddress.ip_network(container.base_network, strict=False)
            for subnet in subnets:
                try:
                    subnet_net = ipaddress.ip_network(subnet.cidr, strict=False)
                    # Only include subnets that are within this container's network
                    if subnet_net.subnet_of(container_net):
                        allocations.append(
                            {
                                "id": subnet.id,
                                "network": subnet.cidr,
                                "description": subnet.name,
                                "vlan_tag": str(subnet.vlan_id) if subnet.vlan_id else "",
                                "created": datetime.now().isoformat(),
                            }
                        )
                except ValueError:
                    # Skip invalid subnet CIDRs
                    continue
        except ValueError:
            flash(f"Container has invalid base network: {container.base_network}", "error")
            return redirect(url_for("main.index"))

        # Sort allocations by IP network
        def sort_by_network(allocation):
            try:
                return ipaddress.ip_network(allocation["network"], strict=False)
            except ValueError:
                # Return a large network for invalid CIDRs to sort them last
                return ipaddress.ip_network("255.255.255.255/32")

        allocations.sort(key=sort_by_network)

        # Calculate usage
        usage = calculate_network_usage(container.base_network, [{"cidr": a["network"]} for a in allocations])

        # Calculate IP range for the container network
        try:
            container_net = ipaddress.ip_network(container.base_network, strict=False)
            network_address = str(container_net.network_address)
            broadcast_address = str(container_net.broadcast_address)
            ip_range = f"{network_address} - {broadcast_address}"
        except ValueError:
            ip_range = "Invalid network"

        # Convert container to segment format
        segment_data = {
            "id": container.id,
            "name": f"{container.block.name} - {container.name}",
            "network": container.base_network,
            "ip_range": ip_range,
            "allocations": allocations,
            "usage": usage,
        }

        return render_template(
            "segment_planner.html", segment=segment_data, version=current_app.version, theme=get_theme()
        )

    except Exception as e:
        logger.error(f"Error viewing container segment {container_id}: {str(e)}", exc_info=True)
        flash(f"Error viewing container segment: {str(e)}", "error")
        return redirect(url_for("main.index"))


@segment_bp.route("/api/block/<int:block_id>")
def api_get_block_segment(block_id):
    """API endpoint to get block segment data"""
    try:
        block = DatabaseService.get_block_by_id(block_id)
        if not block:
            return jsonify({"error": "Block not found"}), 404

        if not block.base_network:
            return jsonify({"error": "Block has no base network defined"}), 400

        subnets = DatabaseService.get_subnets_by_block_id(block_id)

        allocations = []
        for subnet in subnets:
            allocations.append(
                {
                    "id": subnet.id,
                    "network": subnet.cidr,
                    "description": subnet.name,
                    "vlan_tag": str(subnet.vlan_id) if subnet.vlan_id else "",
                    "created": datetime.now().isoformat(),
                }
            )

        segment_data = {"id": block.id, "name": block.name, "network": block.base_network, "allocations": allocations}

        return jsonify(segment_data)

    except Exception as e:
        logger.error(f"Error getting block segment {block_id}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@segment_bp.route("/api/block/<int:block_id>/usage")
def api_get_block_usage(block_id):
    """API endpoint to get block network usage"""
    try:
        block = DatabaseService.get_block_by_id(block_id)
        if not block or not block.base_network:
            return jsonify({"error": "Block not found or has no base network"}), 404

        subnets = DatabaseService.get_subnets_by_block_id(block_id)
        allocations = [{"cidr": subnet.cidr} for subnet in subnets]

        usage = calculate_network_usage(block.base_network, allocations)
        return jsonify(usage)

    except Exception as e:
        logger.error(f"Error getting block usage {block_id}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@segment_bp.route("/api/block/<int:block_id>/validate_allocation", methods=["POST"])
def api_validate_allocation(block_id):
    """API endpoint to validate if a new allocation would be valid"""
    try:
        data = request.json
        network = data.get("network")
        exclude_id = data.get("exclude_id")  # For updates

        if not network:
            return jsonify({"error": "Network is required"}), 400

        # Validate network format
        if not validate_cidr(network):
            return jsonify({"error": "Invalid network format"}), 400

        # Get block
        block = DatabaseService.get_block_by_id(block_id)
        if not block or not block.base_network:
            return jsonify({"error": "Block not found or has no base network"}), 404

        # Get existing subnets
        subnets = DatabaseService.get_subnets_by_block_id(block_id)
        allocations = [{"id": s.id, "cidr": s.cidr} for s in subnets]

        # Check for overlaps
        overlap_error = check_allocation_overlap(block.base_network, allocations, network, exclude_id)
        if overlap_error:
            return jsonify({"error": overlap_error}), 400

        return jsonify({"valid": True})

    except Exception as e:
        logger.error(f"Error validating allocation for block {block_id}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
