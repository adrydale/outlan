import ipaddress
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pytz
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_default_sort, get_timezone
from app.models import ChangeLog, NetworkBlock, NetworkContainer, Subnet, db

logger = logging.getLogger(__name__)


def sort_networks_by_ip(subnets: List[Subnet]) -> List[Subnet]:
    """Sort subnets by IP network address in ascending order.

    Args:
        subnets: List of Subnet objects to sort

    Returns:
        List[Subnet]: Subnets sorted by (block_id, network_address, prefix_length)

    Note:
        Invalid CIDR formats are sorted to the end of the list.
    """

    def get_network_key(subnet: Subnet) -> Tuple[int, int, int]:
        """Get sorting key for network: (block_id, network_address, prefix_length).

        Args:
            subnet: Subnet object to generate key for

        Returns:
            Tuple[int, int, int]: Sorting key tuple
        """
        try:
            network = ipaddress.IPv4Network(subnet.cidr, strict=False)
            return (subnet.block_id, int(network.network_address), network.prefixlen)
        except ValueError:
            # If CIDR is invalid, sort it to the end
            return (subnet.block_id, float("inf"), 0)

    return sorted(subnets, key=get_network_key)


def sort_networks_by_vlan_with_network(subnets: List[Subnet]) -> List[Subnet]:
    """Sort subnets by VLAN ID first, then by IP network address.

    Args:
        subnets: List of Subnet objects to sort

    Returns:
        List[Subnet]: Subnets sorted by (block_id, vlan_id, network_address, prefix_length)

    Note:
        Subnets with null VLAN IDs are sorted to the end.
        Invalid CIDR formats are sorted to the end within their VLAN group.
    """

    def get_vlan_network_key(subnet: Subnet) -> Tuple[int, Optional[int], int, int]:
        """Get sorting key for VLAN + network: (block_id, vlan_id, network_address, prefix_length).

        Args:
            subnet: Subnet object to generate key for

        Returns:
            Tuple[int, Optional[int], int, int]: Sorting key tuple
        """
        try:
            network = ipaddress.IPv4Network(subnet.cidr, strict=False)
            # Use a large number for null VLAN IDs to sort them last
            vlan_id = subnet.vlan_id if subnet.vlan_id is not None else float("inf")
            return (subnet.block_id, vlan_id, int(network.network_address), network.prefixlen)
        except ValueError:
            # If CIDR is invalid, sort it to the end
            return (subnet.block_id, subnet.vlan_id or float("inf"), float("inf"), 0)

    return sorted(subnets, key=get_vlan_network_key)


def sort_networks_by_name_with_network(subnets: List[Subnet]) -> List[Subnet]:
    """Sort subnets by name first, then by IP network address.

    Args:
        subnets: List of Subnet objects to sort

    Returns:
        List[Subnet]: Subnets sorted by (block_id, name_lowercase, network_address, prefix_length)

    Note:
        Names are compared case-insensitively.
        Invalid CIDR formats are sorted to the end within their name group.
    """

    def get_name_network_key(subnet: Subnet) -> Tuple[int, str, int, int]:
        """Get sorting key for name + network: (block_id, name, network_address, prefix_length).

        Args:
            subnet: Subnet object to generate key for

        Returns:
            Tuple[int, str, int, int]: Sorting key tuple with lowercase name
        """
        try:
            network = ipaddress.IPv4Network(subnet.cidr, strict=False)
            return (subnet.block_id, subnet.name.lower(), int(network.network_address), network.prefixlen)
        except ValueError:
            # If CIDR is invalid, sort it to the end
            return (subnet.block_id, subnet.name.lower(), float("inf"), 0)

    return sorted(subnets, key=get_name_network_key)


class DatabaseService:
    """Service class for database operations providing CRUD functionality for network blocks, subnets, and containers.

    This class provides static methods for all database operations including:
    - Network block management (create, read, update, delete)
    - Subnet management with VLAN support
    - Container management for network segmentation
    - Change logging and snapshot functionality
    - Data export/import for backup and restore
    """

    @staticmethod
    def get_session() -> Session:
        """Get current SQLAlchemy database session.

        Returns:
            Session: Active database session
        """
        return db.session

    @staticmethod
    def get_all_blocks() -> List[NetworkBlock]:
        """Get all network blocks ordered by position and name.

        Returns:
            List[NetworkBlock]: All blocks sorted by position, then name
        """
        return NetworkBlock.query.order_by(NetworkBlock.position, NetworkBlock.name).all()

    @staticmethod
    def get_block_by_id(block_id: int) -> Optional[NetworkBlock]:
        """Get network block by ID.

        Args:
            block_id: Unique identifier for the block

        Returns:
            Optional[NetworkBlock]: Block if found, None otherwise
        """
        return db.session.get(NetworkBlock, block_id)

    @staticmethod
    def get_block_by_name(name: str) -> Optional[NetworkBlock]:
        """Get network block by name.

        Args:
            name: Block name to search for

        Returns:
            Optional[NetworkBlock]: Block if found, None otherwise
        """
        return NetworkBlock.query.filter_by(name=name).first()

    @staticmethod
    def create_block(name: str) -> Tuple[bool, Optional[NetworkBlock], str]:
        """Create a new network block with auto-assigned position.

        Args:
            name: Name for the new block

        Returns:
            Tuple[bool, Optional[NetworkBlock], str]: (success, created_block, error_message)
        """
        try:
            # Get max position
            max_position = db.session.query(db.func.max(NetworkBlock.position)).scalar()
            next_position = (max_position or 0) + 1

            block = NetworkBlock(name=name, position=next_position)
            db.session.add(block)
            db.session.commit()
            db.session.refresh(block)
            return True, block, ""
        except IntegrityError:
            db.session.rollback()
            return False, None, f"Block name '{name}' already exists"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating block: {str(e)}")
            return False, None, f"Error creating block: {str(e)}"

    @staticmethod
    def update_block_name(block_id: int, new_name: str) -> Tuple[bool, Optional[str], str]:
        """Update block name"""
        try:
            block = db.session.get(NetworkBlock, block_id)
            if not block:
                return False, None, "Block not found"

            # Check if name already exists
            existing = NetworkBlock.query.filter(NetworkBlock.name == new_name, NetworkBlock.id != block_id).first()
            if existing:
                return False, None, f"Block name '{new_name}' already exists"

            old_name = block.name
            block.name = new_name
            db.session.commit()
            return True, old_name, ""
        except IntegrityError:
            db.session.rollback()
            return False, None, f"Block name '{new_name}' already exists"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating block: {str(e)}")
            return False, None, f"Error updating block: {str(e)}"

    @staticmethod
    def delete_block(block_id: int) -> Tuple[bool, str]:
        """Delete network block and its subnets"""
        try:
            block = db.session.get(NetworkBlock, block_id)
            if not block:
                return False, "Block not found"

            block_name = block.name
            db.session.delete(block)
            db.session.commit()
            return True, block_name
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting block: {str(e)}")
            return False, f"Error deleting block: {str(e)}"

    # Container management methods
    @staticmethod
    def get_all_containers() -> List[NetworkContainer]:
        """Get all network containers ordered by block and position"""
        return (
            NetworkContainer.query.join(NetworkBlock)
            .order_by(NetworkBlock.position, NetworkContainer.position, NetworkContainer.name)
            .all()
        )

    @staticmethod
    def get_containers_by_block_id(block_id: int) -> List[NetworkContainer]:
        """Get all containers for a specific block"""
        return (
            NetworkContainer.query.filter_by(block_id=block_id)
            .order_by(NetworkContainer.position, NetworkContainer.name)
            .all()
        )

    @staticmethod
    def get_container_by_id(container_id: int) -> Optional[NetworkContainer]:
        """Get network container by ID"""
        return db.session.get(NetworkContainer, container_id)

    @staticmethod
    def create_container(block_id: int, name: str, base_network: str) -> Tuple[bool, Optional[NetworkContainer], str]:
        """Create a new network container"""
        try:
            # Validate base network
            try:
                ipaddress.ip_network(base_network, strict=False)
            except ValueError:
                return False, None, f"Invalid base network format: {base_network}"

            # Validate block exists
            block = db.session.get(NetworkBlock, block_id)
            if not block:
                return False, None, "Block not found"

            # Get max position for this block
            max_position = (
                db.session.query(db.func.max(NetworkContainer.position)).filter_by(block_id=block_id).scalar()
            )
            next_position = (max_position or 0) + 1

            container = NetworkContainer(
                block_id=block_id, name=name, base_network=base_network, position=next_position
            )
            db.session.add(container)
            db.session.commit()
            db.session.refresh(container)
            return True, container, ""
        except IntegrityError:
            db.session.rollback()
            return False, None, "Container creation failed - check constraints"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating container: {str(e)}")
            return False, None, f"Error creating container: {str(e)}"

    @staticmethod
    def update_container(container_id: int, name: str, base_network: str) -> Tuple[bool, str]:
        """Update container"""
        try:
            # Validate base network
            try:
                ipaddress.ip_network(base_network, strict=False)
            except ValueError:
                return False, f"Invalid base network format: {base_network}"

            container = db.session.get(NetworkContainer, container_id)
            if not container:
                return False, "Container not found"

            container.name = name
            container.base_network = base_network
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating container: {str(e)}")
            return False, f"Error updating container: {str(e)}"

    @staticmethod
    def delete_container(container_id: int) -> Tuple[bool, str]:
        """Delete container"""
        try:
            container = db.session.get(NetworkContainer, container_id)
            if not container:
                return False, "Container not found"

            container_name = container.name
            db.session.delete(container)
            db.session.commit()
            return True, container_name
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting container: {str(e)}")
            return False, f"Error deleting container: {str(e)}"

    @staticmethod
    def get_all_subnets() -> List[Subnet]:
        """Get all subnets ordered by configured sort field.

        Returns:
            List[Subnet]: All subnets sorted according to DEFAULT_SORT configuration

        Note:
            Sort options: 'Network' (IP address), 'VLAN' (VLAN ID then IP), 'Name' (name then IP)
        """
        sort_field = get_default_sort()

        if sort_field == "Network":
            # Get all subnets and sort by IP network properly
            subnets = Subnet.query.all()
            return sort_networks_by_ip(subnets)
        elif sort_field == "VLAN":
            # Sort by VLAN ID first, then by IP network address
            subnets = Subnet.query.all()
            return sort_networks_by_vlan_with_network(subnets)
        elif sort_field == "Name":
            # Sort by name first, then by IP network address
            subnets = Subnet.query.all()
            return sort_networks_by_name_with_network(subnets)
        else:
            # Default to CIDR sorting
            return Subnet.query.order_by(Subnet.block_id, Subnet.cidr).all()

    @staticmethod
    def get_subnet_by_id(subnet_id: int) -> Optional[Subnet]:
        """Get subnet by ID"""
        return db.session.get(Subnet, subnet_id)

    @staticmethod
    def get_subnets_by_block_id(block_id: int) -> List[Subnet]:
        """Get all subnets for a specific block"""
        return Subnet.query.filter_by(block_id=block_id).all()

    @staticmethod
    def create_subnet(
        block_id: int, name: str, vlan_id: Optional[int], cidr: str
    ) -> Tuple[bool, Optional[Subnet], str]:
        """Create a new subnet"""
        try:
            subnet = Subnet(block_id=block_id, name=name, vlan_id=vlan_id, cidr=cidr)
            db.session.add(subnet)
            db.session.commit()
            db.session.refresh(subnet)
            return True, subnet, ""
        except IntegrityError:
            db.session.rollback()
            return False, None, "Subnet creation failed - check constraints"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating subnet: {str(e)}")
            return False, None, f"Error creating subnet: {str(e)}"

    @staticmethod
    def update_subnet(subnet_id: int, name: str, vlan_id: Optional[int], cidr: str) -> Tuple[bool, str]:
        """Update subnet"""
        try:
            subnet = db.session.get(Subnet, subnet_id)
            if not subnet:
                return False, "Subnet not found"

            subnet.name = name
            subnet.vlan_id = vlan_id
            subnet.cidr = cidr
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating subnet: {str(e)}")
            return False, f"Error updating subnet: {str(e)}"

    @staticmethod
    def delete_subnet(subnet_id: int) -> Tuple[bool, str]:
        """Delete subnet"""
        try:
            subnet = db.session.get(Subnet, subnet_id)
            if not subnet:
                return False, "Subnet not found"

            subnet_name = subnet.name
            db.session.delete(subnet)
            db.session.commit()
            return True, subnet_name
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting subnet: {str(e)}")
            return False, f"Error deleting subnet: {str(e)}"

    @staticmethod
    def add_change_log(action: str, block: str, details: str, content: Optional[str] = None) -> bool:
        """Add change log entry"""
        try:
            change_log = ChangeLog(action=action, block=block or "-", details=details, content=content)
            db.session.add(change_log)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding change log: {str(e)}")
            return False

    @staticmethod
    def get_recent_changes(limit: int = 100) -> List[ChangeLog]:
        """Get recent change log entries"""
        return ChangeLog.query.order_by(ChangeLog.timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_snapshots() -> List[ChangeLog]:
        """Get all snapshot entries"""
        return ChangeLog.query.filter(ChangeLog.content.isnot(None)).order_by(ChangeLog.timestamp.desc()).all()

    @staticmethod
    def get_snapshot_by_id(snapshot_id: int) -> Optional[ChangeLog]:
        """Get snapshot by ID"""
        return ChangeLog.query.filter_by(id=snapshot_id).filter(ChangeLog.content.isnot(None)).first()

    @staticmethod
    def export_all_data() -> Dict[str, Any]:
        """Export all data for snapshots and backups.

        Returns:
            Dict[str, Any]: Complete database export with blocks, containers, and subnets
        """
        blocks = [block.to_dict() for block in DatabaseService.get_all_blocks()]
        containers = [container.to_dict() for container in DatabaseService.get_all_containers()]
        subnets = [subnet.to_dict() for subnet in DatabaseService.get_all_subnets()]
        return {"blocks": blocks, "containers": containers, "subnets": subnets}

    @staticmethod
    def import_data(data: Dict[str, Any]) -> bool:
        """Import data from snapshot, replacing all existing data.

        Args:
            data: Export data dictionary containing blocks, containers, and subnets

        Returns:
            bool: True if import successful, False otherwise

        Warning:
            This operation clears all existing data before importing.
        """
        try:
            # Clear existing data
            Subnet.query.delete()
            NetworkContainer.query.delete()
            NetworkBlock.query.delete()

            # Import blocks
            for block_data in data.get("blocks", []):
                block = NetworkBlock(
                    id=block_data["id"],
                    name=block_data["name"],
                    position=block_data.get("position", 0),
                    collapsed=block_data.get("collapsed", False),
                )
                db.session.add(block)

            # Import containers
            for container_data in data.get("containers", []):
                container = NetworkContainer(
                    id=container_data["id"],
                    block_id=container_data["block_id"],
                    name=container_data["name"],
                    base_network=container_data["base_network"],
                    position=container_data.get("position", 0),
                )
                db.session.add(container)

            # Import subnets
            for subnet_data in data.get("subnets", []):
                subnet = Subnet(
                    id=subnet_data["id"],
                    block_id=subnet_data["block_id"],
                    name=subnet_data["name"],
                    vlan_id=subnet_data.get("vlan_id"),
                    cidr=subnet_data["cidr"],
                )
                db.session.add(subnet)

            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error importing data: {str(e)}")
            return False


def get_timezone_timestamp() -> datetime:
    """Get current timestamp in configured timezone.

    Returns:
        datetime: Current timestamp in the configured timezone

    Note:
        Supports both named timezones (e.g., 'America/Chicago') and UTC offsets (e.g., 'UTC-5').
        Falls back to UTC if timezone configuration is invalid.
    """
    timezone_str = get_timezone()
    try:
        if timezone_str.startswith("UTC"):
            offset = int(timezone_str[3:])
            tz = pytz.FixedOffset(offset * 60)
        else:
            tz = pytz.timezone(timezone_str)
        return datetime.now(tz)
    except Exception:
        return datetime.now(pytz.UTC)
