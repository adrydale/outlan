import ipaddress
import re
from typing import Any, Dict, Optional, Tuple

from app.utils import DatabaseService


def sanitize_input(text: str, max_length: int = 100) -> str:
    """Sanitize user input by removing HTML and limiting length"""
    if not text:
        return ""
    # Remove HTML tags and limit length
    cleaned = re.sub(r"<[^>]+>", "", str(text))
    return cleaned[:max_length].strip()


def validate_block_name(name: str) -> Tuple[bool, str]:
    """Validate network block name"""
    if not name or not name.strip():
        return False, "Block name cannot be empty"

    if len(name) > 50:
        return False, "Block name must be 50 characters or less"

    # Check for invalid characters
    if re.search(r'[<>"\']', name):
        return False, "Block name contains invalid characters"

    return True, ""


def validate_subnet_name(name: str) -> Tuple[bool, str]:
    """Validate subnet name"""
    if not name or not name.strip():
        return False, "Subnet name cannot be empty"

    if len(name) > 50:
        return False, "Subnet name must be 50 characters or less"

    # Check for invalid characters
    if re.search(r'[<>"\']', name):
        return False, "Subnet name contains invalid characters"

    return True, ""


def validate_vlan_id(vlan_id: str) -> Tuple[bool, str, Optional[int]]:
    """Validate VLAN ID and return cleaned numeric value"""
    if not vlan_id:
        return True, "", None  # VLAN ID is optional

    # Allow only digits
    if not re.match(r"^\d+$", vlan_id):
        return False, "VLAN ID can only contain numbers", None

    try:
        vlan = int(vlan_id)
        if vlan < 1 or vlan > 4094:
            return False, "VLAN ID must be between 1 and 4094", None
        return True, "", vlan
    except ValueError:
        return False, "VLAN ID must be a valid number", None


def validate_cidr_format(cidr: str) -> Tuple[bool, str]:
    """Validate CIDR format"""
    if not cidr:
        return False, "CIDR cannot be empty"

    try:
        # Parse the CIDR
        ipaddress.IPv4Network(cidr, strict=False)
        return True, ""
    except ValueError as e:
        return False, f"Invalid CIDR format: {str(e)}"


def check_duplicate_block_name(name: str, exclude_id: Optional[int] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if block name already exists"""
    try:
        existing_block = DatabaseService.get_block_by_name(name)
        if existing_block and (exclude_id is None or existing_block.id != exclude_id):
            return True, {
                "id": existing_block.id,
                "name": existing_block.name,
                "position": existing_block.position,
                "collapsed": existing_block.collapsed,
            }
        return False, None
    except Exception:
        return False, None


def check_duplicate_vlan_in_block(
    vlan_id: Optional[int], block_id: int, exclude_id: Optional[int] = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if VLAN ID already exists in the same block"""
    try:
        # If vlan_id is None, allow multiple null entries
        if vlan_id is None:
            return False, None

        subnets = DatabaseService.get_all_subnets()
        for subnet in subnets:
            if (
                subnet.block_id == block_id
                and subnet.vlan_id == vlan_id
                and (exclude_id is None or subnet.id != exclude_id)
            ):
                return True, {
                    "id": subnet.id,
                    "block_id": subnet.block_id,
                    "name": subnet.name,
                    "vlan_id": subnet.vlan_id,
                    "cidr": subnet.cidr,
                    "block_name": subnet.block.name,
                    "conflict_fields": {"vlan_id": True},  # Only VLAN is conflicting
                }
        return False, None
    except Exception:
        return False, None


def check_overlapping_cidr_in_block(
    cidr: str, block_id: int, exclude_id: Optional[int] = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if CIDR overlaps with existing subnets in the same block"""
    try:
        new_net = ipaddress.IPv4Network(cidr)
        subnets = DatabaseService.get_all_subnets()

        for subnet in subnets:
            if subnet.block_id == block_id and (exclude_id is None or subnet.id != exclude_id):
                try:
                    existing_net = ipaddress.IPv4Network(subnet.cidr)
                    if new_net.overlaps(existing_net):
                        return True, {
                            "id": subnet.id,
                            "block_id": subnet.block_id,
                            "name": subnet.name,
                            "vlan_id": subnet.vlan_id,
                            "cidr": subnet.cidr,
                            "block_name": subnet.block.name,
                            "conflict_fields": {"cidr": True},  # Only CIDR is conflicting
                        }
                except ValueError:
                    continue
        return False, None
    except ValueError:
        return False, None


def is_overlapping_cidr(cidr: str, block_id: int = None, ignore_id: int = None) -> bool:
    """Check if CIDR overlaps with existing subnets"""
    try:
        new_net = ipaddress.IPv4Network(cidr)
    except ValueError:
        return False

    from app.utils import DatabaseService

    # Get existing subnets
    subnets = DatabaseService.get_all_subnets()

    for subnet in subnets:
        if ignore_id and subnet.id == ignore_id:
            continue
        if block_id and subnet.block_id != block_id:
            continue

        try:
            existing_net = ipaddress.IPv4Network(subnet.cidr)
            if new_net.overlaps(existing_net):
                return True
        except ValueError:
            continue

    return False
