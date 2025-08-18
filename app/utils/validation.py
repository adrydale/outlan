import ipaddress
import re
from typing import Any, Dict, Optional, Tuple

from app.utils import DatabaseService

# Validation constants
MAX_INPUT_LENGTH = 100
MAX_NAME_LENGTH = 50
MIN_VLAN_ID = 1
MAX_VLAN_ID = 4094


def sanitize_input(text: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """Sanitize user input by removing HTML tags and limiting length.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length (default: MAX_INPUT_LENGTH)

    Returns:
        str: Sanitized text with HTML removed and length limited
    """
    if not text:
        return ""
    # Remove HTML tags and limit length
    cleaned = re.sub(r"<[^>]+>", "", str(text))
    return cleaned[:max_length].strip()


def validate_block_name(name: str) -> Tuple[bool, str]:
    """Validate network block name for length and invalid characters.

    Args:
        name: Block name to validate

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Block name cannot be empty"

    if len(name) > MAX_NAME_LENGTH:
        return False, f"Block name must be {MAX_NAME_LENGTH} characters or less"

    # Check for invalid characters and SQL injection patterns
    if re.search(r'[<>"\']', name):
        return False, "Block name contains invalid characters"

    # Check for SQL injection patterns (not individual words)
    sql_injection_patterns = [
        r";\s*--",  # ; followed by SQL comment
        r";\s*(DROP|DELETE|INSERT|UPDATE)",  # ; followed by dangerous SQL commands
        r"/\*.*?\*/",  # SQL block comments
        r"--\s",  # SQL line comments
        r"'\s*(OR|AND)\s*'",  # Common injection patterns like ' OR '
        r"UNION\s+SELECT",  # UNION SELECT pattern
    ]

    for pattern in sql_injection_patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return False, "Block name contains potentially dangerous patterns"

    return True, ""


def validate_subnet_name(name: str) -> Tuple[bool, str]:
    """Validate subnet name for length and invalid characters.

    Args:
        name: Subnet name to validate

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Subnet name cannot be empty"

    if len(name) > MAX_NAME_LENGTH:
        return False, f"Subnet name must be {MAX_NAME_LENGTH} characters or less"

    # Check for invalid characters (only the most dangerous ones)
    if re.search(r'[<>"\']', name):
        return False, "Subnet name contains invalid characters"

    return True, ""


def validate_vlan_id(vlan_id: str) -> Tuple[bool, str, Optional[int]]:
    """Validate VLAN ID and return cleaned numeric value.

    Args:
        vlan_id: VLAN ID string to validate (1-4094 range)

    Returns:
        Tuple[bool, str, Optional[int]]: (is_valid, error_message, parsed_vlan_id)
    """
    if not vlan_id:
        return True, "", None  # VLAN ID is optional

    # Allow only digits
    if not re.match(r"^\d+$", vlan_id):
        return False, "VLAN ID can only contain numbers", None

    try:
        vlan = int(vlan_id)
        if vlan < MIN_VLAN_ID or vlan > MAX_VLAN_ID:
            return False, f"VLAN ID must be between {MIN_VLAN_ID} and {MAX_VLAN_ID}", None
        return True, "", vlan
    except ValueError:
        return False, "VLAN ID must be a valid number", None


def validate_cidr_format(cidr: str) -> Tuple[bool, str]:
    """Validate CIDR format using IPv4Network validation.

    Args:
        cidr: CIDR notation string (e.g., '192.168.1.0/24')

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not cidr:
        return False, "CIDR cannot be empty"

    # Require explicit subnet mask (must contain '/')
    if "/" not in cidr:
        return False, "CIDR must include subnet mask (e.g., 192.168.1.0/24)"

    try:
        # Parse the CIDR
        ipaddress.IPv4Network(cidr, strict=False)
        return True, ""
    except ValueError as e:
        return False, f"Invalid CIDR format: {str(e)}"


def check_duplicate_block_name(name: str, exclude_id: Optional[int] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if block name already exists in the database.

    Args:
        name: Block name to check for duplicates
        exclude_id: Block ID to exclude from duplicate check (for updates)

    Returns:
        Tuple[bool, Optional[Dict]]: (is_duplicate, existing_block_data)
    """
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
    """Check if VLAN ID already exists in the same block.

    Args:
        vlan_id: VLAN ID to check (None allowed for multiple null entries)
        block_id: Block ID to check within
        exclude_id: Subnet ID to exclude from duplicate check (for updates)

    Returns:
        Tuple[bool, Optional[Dict]]: (is_duplicate, conflicting_subnet_data)
    """
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
    """Check if CIDR overlaps with existing subnets in the same block.

    Args:
        cidr: CIDR notation to check for overlaps
        block_id: Block ID to check within
        exclude_id: Subnet ID to exclude from overlap check (for updates)

    Returns:
        Tuple[bool, Optional[Dict]]: (has_overlap, overlapping_subnet_data)
    """
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


def check_overlapping_container_networks(
    base_network: str, block_id: int, exclude_id: Optional[int] = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if container base network overlaps with existing containers within the same block.

    Args:
        base_network: Container base network CIDR to check for overlaps
        block_id: Block ID to check within
        exclude_id: Container ID to exclude from overlap check (for updates)

    Returns:
        Tuple[bool, Optional[Dict]]: (has_overlap, overlapping_container_data)
    """
    try:
        new_net = ipaddress.IPv4Network(base_network)
        containers = DatabaseService.get_all_containers()

        for container in containers:
            # Only check containers within the same block
            if container.block_id == block_id and (exclude_id is None or container.id != exclude_id):
                try:
                    existing_net = ipaddress.IPv4Network(container.base_network)
                    if new_net.overlaps(existing_net):
                        return True, {
                            "id": container.id,
                            "block_id": container.block_id,
                            "name": container.name,
                            "base_network": container.base_network,
                            "block_name": container.block.name if container.block else "Unknown",
                            "conflict_fields": {"base_network": True},
                        }
                except ValueError:
                    continue
        return False, None
    except ValueError:
        return False, None


def is_overlapping_cidr(cidr: str, block_id: int = None, ignore_id: int = None) -> bool:
    """Check if CIDR overlaps with existing subnets (legacy function).

    Args:
        cidr: CIDR notation to check for overlaps
        block_id: Optional block ID to limit search scope
        ignore_id: Optional subnet ID to ignore during check

    Returns:
        bool: True if CIDR overlaps with existing subnets

    Note:
        This function is maintained for backwards compatibility.
        Use check_overlapping_cidr_in_block for new code.
    """
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
