import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pytz
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_timezone
from app.models import ChangeLog, NetworkBlock, Subnet, db

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service class for database operations"""

    @staticmethod
    def get_session() -> Session:
        """Get database session"""
        return db.session

    @staticmethod
    def get_all_blocks() -> List[NetworkBlock]:
        """Get all network blocks ordered by position and name"""
        return NetworkBlock.query.order_by(NetworkBlock.position, NetworkBlock.name).all()

    @staticmethod
    def get_block_by_id(block_id: int) -> Optional[NetworkBlock]:
        """Get network block by ID"""
        return NetworkBlock.query.get(block_id)

    @staticmethod
    def get_block_by_name(name: str) -> Optional[NetworkBlock]:
        """Get network block by name"""
        return NetworkBlock.query.filter_by(name=name).first()

    @staticmethod
    def create_block(name: str) -> Tuple[bool, Optional[NetworkBlock], str]:
        """Create a new network block"""
        try:
            # Get max position
            max_position = db.session.query(db.func.max(NetworkBlock.position)).scalar()
            next_position = (max_position or 0) + 1

            block = NetworkBlock(name=name, position=next_position)
            db.session.add(block)
            db.session.commit()
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
            block = NetworkBlock.query.get(block_id)
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
            block = NetworkBlock.query.get(block_id)
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

    @staticmethod
    def get_all_subnets() -> List[Subnet]:
        """Get all subnets ordered by configured sort field"""
        from app.config import get_default_sort

        sort_field = get_default_sort()

        if sort_field == "Network":
            # Sort by CIDR (network)
            return Subnet.query.order_by(Subnet.block_id, Subnet.cidr).all()
        elif sort_field == "VLAN":
            # Sort by VLAN ID, with null values last
            return Subnet.query.order_by(Subnet.block_id, Subnet.vlan_id.nulls_last(), Subnet.cidr).all()
        elif sort_field == "Name":
            # Sort by name
            return Subnet.query.order_by(Subnet.block_id, Subnet.name).all()
        else:
            # Default to CIDR sorting
            return Subnet.query.order_by(Subnet.block_id, Subnet.cidr).all()

    @staticmethod
    def get_subnet_by_id(subnet_id: int) -> Optional[Subnet]:
        """Get subnet by ID"""
        return Subnet.query.get(subnet_id)

    @staticmethod
    def create_subnet(
        block_id: int, name: str, vlan_id: Optional[int], cidr: str
    ) -> Tuple[bool, Optional[Subnet], str]:
        """Create a new subnet"""
        try:
            subnet = Subnet(block_id=block_id, name=name, vlan_id=vlan_id, cidr=cidr)
            db.session.add(subnet)
            db.session.commit()
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
            subnet = Subnet.query.get(subnet_id)
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
            subnet = Subnet.query.get(subnet_id)
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
        """Export all data for snapshots"""
        blocks = [block.to_dict() for block in DatabaseService.get_all_blocks()]
        subnets = [subnet.to_dict() for subnet in DatabaseService.get_all_subnets()]
        return {"blocks": blocks, "subnets": subnets}

    @staticmethod
    def import_data(data: Dict[str, Any]) -> bool:
        """Import data from snapshot"""
        try:
            # Clear existing data
            Subnet.query.delete()
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
    """Get current timestamp in configured timezone"""
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
