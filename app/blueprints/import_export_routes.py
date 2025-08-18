import csv
import io
import json
import logging

from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for

from app.config import get_theme
from app.utils import DatabaseService
from app.utils.validation import (
    sanitize_input,
    validate_block_name,
    validate_cidr_format,
    validate_subnet_name,
    validate_vlan_id,
)

logger = logging.getLogger(__name__)
import_export_bp = Blueprint("import_export", __name__)


@import_export_bp.route("/import_export")
def import_export():
    """Import/Export page"""
    try:
        # Get all blocks for the block selector dropdown
        blocks = DatabaseService.get_all_blocks()
        blocks_dict = [block.to_dict() for block in blocks]

        return render_template("import_export.html", blocks=blocks_dict, version=current_app.version, theme=get_theme())
    except Exception as e:
        logger.error(f"Error loading import/export page: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html",
                message="Error loading import/export page",
                attempted=None,
                traceback=str(e),
                version=current_app.version,
            ),
            500,
        )


@import_export_bp.route("/download_example_csv")
def download_example_csv():
    """Download example CSV template"""
    try:
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(["Block", "Network", "VLAN", "Subnet Name"])

        # Write example data
        writer.writerow(["Production", "10.0.1.0/24", "100", "Web Servers"])
        writer.writerow(["Production", "10.0.2.0/24", "101", "Database Servers"])
        writer.writerow(["Development", "10.1.0.0/24", "200", "Dev Environment"])
        writer.writerow(["Development", "10.1.1.0/24", "", "Test Environment"])

        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": 'attachment; filename="example_import_template.csv"'},
        )
    except Exception as e:
        logger.error(f"Error generating example CSV: {str(e)}", exc_info=True)
        flash("Error generating example CSV", "error")
        return redirect(url_for("import_export.import_export"))


@import_export_bp.route("/export_all_csv")
def export_all_csv():
    """Export all data to CSV or export specific block if block_id provided"""
    try:
        block_id = request.args.get("block_id")

        if block_id:
            # Export specific block
            try:
                block_id = int(block_id)
                block = DatabaseService.get_block_by_id(block_id)
                if not block:
                    flash("Block not found", "error")
                    return redirect(url_for("import_export.import_export"))

                subnets = [s for s in DatabaseService.get_all_subnets() if s.block_id == block_id]
                filename = f"{block.name}_export.csv"

            except ValueError:
                flash("Invalid block ID", "error")
                return redirect(url_for("import_export.import_export"))
        else:
            # Export all blocks
            subnets = DatabaseService.get_all_subnets()
            filename = "all_networks_export.csv"

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Block", "Network", "VLAN", "Subnet Name"])

        for subnet in subnets:
            block = DatabaseService.get_block_by_id(subnet.block_id)
            block_name = block.name if block else "Unknown"
            writer.writerow([block_name, subnet.cidr, subnet.vlan_id or "", subnet.name])

        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        logger.error(f"Error exporting CSV: {str(e)}", exc_info=True)
        flash("Error exporting CSV", "error")
        return redirect(url_for("import_export.import_export"))


@import_export_bp.route("/import_csv", methods=["POST"])
def import_csv():
    """Import CSV file"""
    try:
        # Get form data
        import_mode = request.form.get("import_mode", "merge")
        uploaded_file = request.files.get("csv_file")

        if not uploaded_file or uploaded_file.filename == "":
            flash("Please select a CSV file to import", "error")
            return redirect(url_for("import_export.import_export"))

        # Read file content
        try:
            file_content = uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            flash("Error: File must be UTF-8 encoded", "error")
            return redirect(url_for("import_export.import_export"))

        # Validate it's actually CSV data by trying to parse it
        try:
            reader = csv.reader(io.StringIO(file_content))
            rows = list(reader)
        except csv.Error as e:
            flash(f"Error: Invalid CSV format - {str(e)}", "error")
            return redirect(url_for("import_export.import_export"))

        if len(rows) < 2:
            flash("Error: CSV file must contain at least a header row and one data row", "error")
            return redirect(url_for("import_export.import_export"))

        # Validate header
        expected_headers = ["Block", "Network", "VLAN", "Subnet Name"]
        actual_headers = [h.strip() for h in rows[0]]

        if actual_headers != expected_headers:
            flash(f"Error: CSV headers must be exactly: {', '.join(expected_headers)}", "error")
            return redirect(url_for("import_export.import_export"))

        # Validate data rows and collect errors
        validation_errors = []
        processed_rows = []

        for row_idx, row in enumerate(rows[1:], start=2):  # Start from row 2 (skip header)
            row_errors = []
            field_errors = {}

            # Check column count
            if len(row) != 4:
                validation_errors.append(
                    {
                        "row_number": row_idx,
                        "data": {
                            "block_name": row[0] if len(row) > 0 else "",
                            "cidr": row[1] if len(row) > 1 else "",
                            "vlan_id": row[2] if len(row) > 2 else "",
                            "subnet_name": row[3] if len(row) > 3 else "",
                        },
                        "field_errors": {},
                        "error_message": f"Expected 4 columns, got {len(row)}",
                    }
                )
                continue

            block_name = sanitize_input(row[0].strip())
            cidr = sanitize_input(row[1].strip())
            vlan_id_raw = row[2].strip()
            subnet_name = sanitize_input(row[3].strip())

            # Validate each field
            if not block_name:
                row_errors.append("Block name cannot be empty")
                field_errors["block_name"] = True

            if not subnet_name:
                row_errors.append("Subnet name cannot be empty")
                field_errors["subnet_name"] = True

            if not cidr:
                row_errors.append("CIDR cannot be empty")
                field_errors["cidr"] = True

            # Validate block name
            if block_name:
                block_valid, block_error = validate_block_name(block_name)
                if not block_valid:
                    row_errors.append(f"Block name: {block_error}")
                    field_errors["block_name"] = True

            # Validate subnet name
            if subnet_name:
                subnet_valid, subnet_error = validate_subnet_name(subnet_name)
                if not subnet_valid:
                    row_errors.append(f"Subnet name: {subnet_error}")
                    field_errors["subnet_name"] = True

            # Validate CIDR
            if cidr:
                cidr_valid, cidr_error = validate_cidr_format(cidr)
                if not cidr_valid:
                    row_errors.append(f"CIDR: {cidr_error}")
                    field_errors["cidr"] = True

            # Validate VLAN ID if provided
            vlan_id = None
            if vlan_id_raw:
                vlan_valid, vlan_error, cleaned_vlan = validate_vlan_id(vlan_id_raw)
                if not vlan_valid:
                    row_errors.append(f"VLAN ID: {vlan_error}")
                    field_errors["vlan_id"] = True
                else:
                    vlan_id = cleaned_vlan

            # If there are errors for this row, add to validation errors
            if row_errors:
                validation_errors.append(
                    {
                        "row_number": row_idx,
                        "data": {
                            "block_name": block_name,
                            "cidr": cidr,
                            "vlan_id": vlan_id_raw,
                            "subnet_name": subnet_name,
                        },
                        "field_errors": field_errors,
                        "error_message": "; ".join(row_errors),
                    }
                )
            else:
                # Row is valid, add to processed rows
                processed_rows.append(
                    {
                        "line_number": row_idx,
                        "block_name": block_name,
                        "subnet_name": subnet_name,
                        "vlan_id": vlan_id,
                        "cidr": cidr,
                    }
                )

        # Show validation errors using the error template
        if validation_errors:
            return render_template(
                "import_error.html",
                validation_errors=validation_errors[:20],  # Show up to 20 errors
                error_count=len(validation_errors),
                version=current_app.version,
                theme=get_theme(),
            )

        # Handle import mode
        if import_mode == "replace":
            try:
                # Create a final snapshot before complete deletion
                content_before_replace = json.dumps(DatabaseService.export_all_data())
                DatabaseService.add_change_log(
                    action="PRE_REPLACE_SNAPSHOT",
                    block="All",
                    details="Snapshot before complete replace import",
                    content=content_before_replace,
                )

                # Delete all existing subnets first
                subnets = DatabaseService.get_all_subnets()
                for subnet in subnets:
                    DatabaseService.delete_subnet(subnet.id)

                # Delete all existing containers
                containers = DatabaseService.get_all_containers()
                for container in containers:
                    DatabaseService.delete_container(container.id)

                # Delete all existing blocks
                blocks = DatabaseService.get_all_blocks()
                for block in blocks:
                    DatabaseService.delete_block(block.id)

                logger.info(
                    f"Complete replace: deleted {len(subnets)} subnets, "
                    f"{len(containers)} containers, {len(blocks)} blocks"
                )

            except Exception as e:
                logger.error(f"Error during complete replace cleanup: {str(e)}")
                flash("Error occurred while clearing existing data. Import aborted.", "error")
                return redirect(url_for("import_export.import_export"))

        # Process the import
        success_count = 0
        error_count = 0
        blocks_created = set()

        for row_data in processed_rows:
            try:
                # Get or create block
                block = None
                existing_blocks = DatabaseService.get_all_blocks()
                for b in existing_blocks:
                    if b.name == row_data["block_name"]:
                        block = b
                        break

                if not block:
                    # Create new block
                    success, block, error_msg = DatabaseService.create_block(row_data["block_name"])
                    if not success:
                        logger.error(f"Failed to create block {row_data['block_name']}: {error_msg}")
                        error_count += 1
                        continue
                    blocks_created.add(row_data["block_name"])

                # Check if subnet already exists
                existing_subnets = [s for s in DatabaseService.get_all_subnets() if s.block_id == block.id]
                subnet_exists = False

                for subnet in existing_subnets:
                    if subnet.name == row_data["subnet_name"] or subnet.cidr == row_data["cidr"]:
                        subnet_exists = True
                        if import_mode == "merge":
                            # Skip existing subnets in merge mode
                            logger.info(f"Skipping existing subnet {row_data['subnet_name']} in merge mode")
                            break
                        elif import_mode == "override":
                            # Update existing subnet
                            success, error_msg = DatabaseService.update_subnet(
                                subnet.id, row_data["subnet_name"], row_data["vlan_id"], row_data["cidr"]
                            )
                            if success:
                                success_count += 1
                            else:
                                logger.error(f"Failed to update subnet: {error_msg}")
                                error_count += 1
                            break

                if not subnet_exists:
                    # Create new subnet
                    success, subnet, error_msg = DatabaseService.create_subnet(
                        block.id, row_data["subnet_name"], row_data["vlan_id"], row_data["cidr"]
                    )
                    if success:
                        success_count += 1
                    else:
                        logger.error(f"Failed to create subnet: {error_msg}")
                        error_count += 1

            except Exception as e:
                logger.error(f"Error processing row {row_data['line_number']}: {str(e)}")
                error_count += 1

        # Log the import action
        content = json.dumps(DatabaseService.export_all_data())
        blocks_created_str = ", ".join(blocks_created) if blocks_created else "none"
        DatabaseService.add_change_log(
            action="IMPORT_CSV",
            block="Multiple" if len(blocks_created) != 1 else list(blocks_created)[0] if blocks_created else "Existing",
            details=(
                f"CSV import: {success_count} subnets, {error_count} errors, "
                f"created blocks: {blocks_created_str}, mode: {import_mode}"
            ),
            content=content,
        )

        # Show results
        if success_count > 0:
            flash(f"Successfully imported {success_count} subnet(s)", "success")
        if error_count > 0:
            flash(f"{error_count} import error(s) occurred. Check logs for details.", "warning")
        if blocks_created:
            flash(f"Created new block(s): {', '.join(blocks_created)}", "info")

        return redirect(url_for("import_export.import_export"))

    except Exception as e:
        logger.error(f"Unexpected error in import_csv: {str(e)}", exc_info=True)
        flash("An unexpected error occurred during import", "error")
        return redirect(url_for("import_export.import_export"))
