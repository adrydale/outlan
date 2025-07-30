import logging
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from app.models import db
from app.utils import DatabaseService

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)


@api_bp.route("/api/health")
def health():
    try:
        # Test database connection by trying to get blocks
        DatabaseService.get_all_blocks()
        return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@api_bp.route("/api/version")
def version():
    return jsonify({"version": current_app.version, "name": "Outlan IPAM", "status": "alpha"})


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
