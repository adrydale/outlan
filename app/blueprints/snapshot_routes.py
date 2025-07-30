import json
import logging

from flask import Blueprint, current_app, redirect, render_template, url_for

from app.config import get_theme
from app.utils import DatabaseService

logger = logging.getLogger(__name__)
snapshot_bp = Blueprint("snapshot", __name__)


@snapshot_bp.route("/snapshots")
def snapshot_list():
    try:
        # Get snapshots using the service
        snaps = DatabaseService.get_snapshots()

        # Format timestamps
        formatted_snaps = []
        for snap in snaps:
            snap_dict = snap.to_dict()
            ts = snap.timestamp
            if ts:
                ts_fmt = ts.strftime("%Y-%m-%d %H:%M:%S")
            else:
                ts_fmt = "Unknown"
            snap_dict["timestamp"] = ts_fmt
            formatted_snaps.append(snap_dict)

        return render_template(
            "snapshots.html", snapshots=formatted_snaps, version=current_app.version, theme=get_theme()
        )
    except Exception as e:
        logger.error(f"Error loading snapshots: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="Error loading snapshots",
                attempted=None,
                traceback=str(e),
                version=current_app.version,
            ),
            500,
        )


@snapshot_bp.route("/restore_snapshot/<int:snap_id>", methods=["POST"])
def restore_snapshot(snap_id):
    try:
        # Get snapshot using the service
        snap = DatabaseService.get_snapshot_by_id(snap_id)
        if not snap:
            return (
                render_template(
                    "error.html",
                    message="Snapshot not found.",
                    attempted={"cidr": None, "vlan": None, "name": None},
                    version=current_app.version,
                ),
                404,
            )

        content = snap.content
        if not content:
            return (
                render_template(
                    "error.html",
                    message="Snapshot content missing.",
                    attempted={"cidr": None, "vlan": None, "name": None},
                    version=current_app.version,
                ),
                400,
            )

        # Parse and import data
        data = json.loads(content)
        success = DatabaseService.import_data(data)

        if not success:
            return (
                render_template(
                    "error.html",
                    message="Error restoring snapshot data.",
                    attempted={"cidr": None, "vlan": None, "name": None},
                    version=current_app.version,
                ),
                500,
            )

        # Log the restore action
        restored_content = json.dumps(DatabaseService.export_all_data())
        DatabaseService.add_change_log(
            action="RESTORE", block="-", details=f"Restored to snapshot {snap_id}", content=restored_content
        )

        # Redirect to confirmation page
        return redirect(url_for("snapshot.restore_confirmation", snap_id=snap.id))

    except Exception as e:
        logger.error(f"Unexpected error in restore_snapshot: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="An unexpected error occurred",
                attempted={"cidr": None, "vlan": None, "name": None},
                version=current_app.version,
            ),
            500,
        )


@snapshot_bp.route("/restore_confirmation/<int:snap_id>")
def restore_confirmation(snap_id):
    try:
        snap = DatabaseService.get_snapshot_by_id(snap_id)
        if not snap:
            return (render_template("error.html", message="Snapshot not found.", version=current_app.version), 404)

        return render_template(
            "restore_confirmation.html",
            snap_id=snap.id,
            details=snap.details,
            timestamp=(snap.timestamp.strftime("%Y-%m-%d %H:%M:%S") if snap.timestamp else "Unknown"),
            version=current_app.version,
        )
    except Exception as e:
        logger.error(f"Error in restore_confirmation: {str(e)}", exc_info=True)
        return (
            render_template("error.html", message="Error loading confirmation page.", version=current_app.version),
            500,
        )
