"""
Export functionality for IPAM operations.

This module handles CSV export operations for network blocks and subnets.
"""

import csv
import logging
from io import StringIO

from flask import Blueprint, Response, current_app, render_template

from app.utils import DatabaseService

from .helpers import _render_validation_error

logger = logging.getLogger(__name__)


exports_bp = Blueprint("ipam_exports", __name__)


@exports_bp.route("/export_csv/<int:block_id>")
def export_csv(block_id):
    try:
        # Get block
        block = DatabaseService.get_block_by_id(block_id)
        if not block:
            return _render_validation_error("Block not found", {"cidr": None, "vlan": None, "name": None}, 404)

        # Get subnets for this block
        subnets = [s for s in DatabaseService.get_all_subnets() if s.block_id == block_id]

        # Generate CSV
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Block", "Network", "VLAN", "Subnet Name"])

        for subnet in subnets:
            writer.writerow([block.name, subnet.cidr, subnet.vlan_id or "", subnet.name])

        output.seek(0)

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
