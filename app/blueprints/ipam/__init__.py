"""
IPAM (IP Address Management) Blueprint Package.

This package contains all IPAM-related functionality organized by domain:
- blocks: Block management operations
- subnets: Subnet management operations
- containers: Container management operations
- exports: CSV export functionality
- helpers: Shared utility functions

All blueprints are registered here for simplified import.
"""

from .blocks import blocks_bp
from .containers import containers_bp
from .exports import exports_bp
from .subnets import subnets_bp

# Export all blueprints for easy registration
__all__ = ["blocks_bp", "containers_bp", "exports_bp", "subnets_bp"]
