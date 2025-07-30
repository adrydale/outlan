from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

# Initialize SQLAlchemy
db = SQLAlchemy()


class NetworkBlock(db.Model):
    """Model for network blocks"""

    __tablename__ = "network_blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    position = Column(Integer, default=0)
    collapsed = Column(Boolean, default=False)

    # Relationship
    subnets = relationship("Subnet", back_populates="block", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<NetworkBlock {self.name}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {"id": self.id, "name": self.name, "position": self.position, "collapsed": bool(self.collapsed)}


class Subnet(db.Model):
    """Model for subnets"""

    __tablename__ = "subnets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    block_id = Column(Integer, ForeignKey("network_blocks.id"), nullable=False)
    name = Column(String(255), nullable=False)
    vlan_id = Column(Integer)
    cidr = Column(String(50), nullable=False)

    # Relationship
    block = relationship("NetworkBlock", back_populates="subnets")

    def __repr__(self):
        return f"<Subnet {self.cidr} ({self.name})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "block_id": self.block_id,
            "name": self.name,
            "vlan_id": self.vlan_id,
            "cidr": self.cidr,
            "block_name": self.block.name if self.block else None,
        }


class ChangeLog(db.Model):
    """Model for audit log entries"""

    __tablename__ = "change_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String(100), nullable=False)
    block = Column(String(255))
    details = Column(Text)
    content = Column(Text)  # JSON content for snapshots

    def __repr__(self):
        return f"<ChangeLog {self.action} at {self.timestamp}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "action": self.action,
            "block": self.block,
            "details": self.details,
            "content": self.content,
        }
