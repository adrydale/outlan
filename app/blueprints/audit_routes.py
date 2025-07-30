import logging

from flask import Blueprint, current_app, render_template

from app.config import get_theme
from app.utils import DatabaseService

logger = logging.getLogger(__name__)
audit_bp = Blueprint("audit", __name__)


@audit_bp.route("/audit")
def audit_log():
    try:
        # Get recent changes using the service
        change_entries = DatabaseService.get_recent_changes(100)

        # Format timestamps and enumerate snapshots
        formatted_entries = []
        snapshot_ids = [entry.id for entry in change_entries if entry.content]
        snapshot_index = {sid: idx + 1 for idx, sid in enumerate(snapshot_ids)}  # most recent = 1

        for entry in change_entries:
            entry_dict = entry.to_dict()
            ts = entry.timestamp
            if ts:
                ts_fmt = ts.strftime("%Y-%m-%d %H:%M:%S")
            else:
                ts_fmt = "Unknown"
            entry_dict["timestamp"] = ts_fmt
            formatted_entries.append(entry_dict)

        current_snapshot_id = snapshot_ids[0] if snapshot_ids else None

        return render_template(
            "audit.html",
            audit_entries=formatted_entries,
            snapshot_ids=snapshot_ids,
            current_snapshot_id=current_snapshot_id,
            snapshot_index=snapshot_index,
            version=current_app.version,
            theme=get_theme(),
        )
    except Exception as e:
        logger.error(f"Error accessing change log: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html", message="Error loading change log.", attempted=None, version=current_app.version
            ),
            500,
        )
