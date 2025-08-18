#!/usr/bin/env python3
"""
Screenshot generation script for Outlan IPAM.
Generates dark mode desktop screenshots using the existing screenshot database.
"""

import asyncio
import os
import sqlite3
import sys

from playwright.async_api import async_playwright


def validate_database(db_path: str) -> bool:
    """Validate that the database has the expected structure and data"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        expected_tables = {"network_blocks", "subnets", "change_log", "network_containers"}

        if not expected_tables.issubset(tables):
            print(f"❌ Missing tables. Expected: {expected_tables}, Found: {tables}")
            return False

        # Check network blocks
        cursor.execute("SELECT id, name FROM network_blocks ORDER BY position")
        blocks = cursor.fetchall()

        if len(blocks) < 2:
            print(f"❌ Expected at least 2 blocks, found {len(blocks)}")
            return False

        print(f"✅ Found {len(blocks)} blocks:")
        for block_id, name in blocks:
            print(f"   - {name} (ID: {block_id})")

        # Check for Lab networks container
        cursor.execute("SELECT id, name FROM network_containers WHERE name LIKE '%Lab%'")
        lab_containers = cursor.fetchall()

        if not lab_containers:
            print("❌ No 'Lab networks' container found")
            return False

        print(f"✅ Found Lab container: {lab_containers[0][1]} (ID: {lab_containers[0][0]})")

        # Check subnets exist
        cursor.execute("SELECT COUNT(*) FROM subnets")
        subnet_count = cursor.fetchone()[0]
        print(f"✅ Found {subnet_count} subnets in database")

        print("✅ Database validation passed!")
        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        if "conn" in locals():
            conn.close()


async def wait_for_app_ready(page, max_retries: int = 30) -> bool:
    """Wait for the application to be ready"""
    for i in range(max_retries):
        try:
            response = await page.goto("http://localhost:5000/")
            if response and response.status == 200:
                await page.wait_for_load_state("networkidle")
                return True
        except Exception:
            pass

        print(f"Waiting for app to be ready... ({i+1}/{max_retries})")
        await asyncio.sleep(2)

    return False


async def set_dark_theme(page):
    """Set dark theme for the page"""
    await page.evaluate(
        """
        localStorage.setItem('theme', 'dark');
        document.documentElement.setAttribute('data-theme', 'dark');
        """
    )
    await page.wait_for_timeout(500)


async def get_lab_container_id(db_path: str) -> int:
    """Get the ID of the Lab networks container"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM network_containers WHERE name LIKE '%Lab%' LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


async def generate_screenshots():
    """Generate dark mode desktop screenshots"""

    # Get database path
    db_path = os.environ.get("DB_PATH", "data/ipam_screenshots.db")

    # Validate database
    print(f"🔍 Validating database: {db_path}")

    if not validate_database(db_path):
        print("❌ Database validation failed!")
        return False

    # Get Lab container ID for segment view
    lab_container_id = await get_lab_container_id(db_path)
    if not lab_container_id:
        print("❌ Could not find Lab networks container ID")
        return False

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Set desktop viewport size
        await page.set_viewport_size({"width": 1400, "height": 900})

        try:
            # Wait for app to be ready
            print("🚀 Waiting for application to be ready...")
            if not await wait_for_app_ready(page):
                print("❌ Application failed to start")
                return False

            print("✅ Application is ready!")

            # Screenshot 1: Main IPAM Interface
            print("📸 Taking screenshot of main interface...")
            await page.goto("http://localhost:5000/")
            await page.wait_for_load_state("networkidle")
            await set_dark_theme(page)
            await page.wait_for_timeout(1000)  # Allow theme to apply

            await page.screenshot(path="screenshots/screenshot_main_interface.png")
            print("✅ Saved: screenshots/screenshot_main_interface.png")

            # Screenshot 2: Import/Export Page
            print("📸 Taking screenshot of import/export page...")
            await page.goto("http://localhost:5000/import_export")
            await page.wait_for_load_state("networkidle")
            await set_dark_theme(page)
            await page.wait_for_timeout(1000)

            await page.screenshot(path="screenshots/screenshot_import_export.png")
            print("✅ Saved: screenshots/screenshot_import_export.png")

            # Screenshot 3: Audit/Logging Page
            print("📸 Taking screenshot of audit page...")
            await page.goto("http://localhost:5000/audit")
            await page.wait_for_load_state("networkidle")
            await set_dark_theme(page)
            await page.wait_for_timeout(1000)

            # Try to collapse expandable sections for cleaner view
            try:
                # Hide snapshot info section if visible
                await page.evaluate(
                    """
                    const elements = document.querySelectorAll('.alert, .info-box, #snapshot-content');
                    elements.forEach(el => {
                        if (el && el.textContent.includes('snapshot') || el.textContent.includes('restore')) {
                            el.style.display = 'none';
                        }
                    });
                    """
                )
                await page.wait_for_timeout(500)
            except Exception as e:
                print(f"⚠️ Could not clean audit page layout: {e}")

            await page.screenshot(path="screenshots/screenshot_audit_page.png")
            print("✅ Saved: screenshots/screenshot_audit_page.png")

            # Screenshot 4: Segment View of Lab Networks Container
            print(f"📸 Taking screenshot of Lab networks container segment view (ID: {lab_container_id})...")
            await page.goto(f"http://localhost:5000/segment/container/{lab_container_id}")
            await page.wait_for_load_state("networkidle")
            await set_dark_theme(page)
            await page.wait_for_timeout(1000)

            await page.screenshot(path="screenshots/screenshot_segment_view.png")
            print("✅ Saved: screenshots/screenshot_segment_view.png")

            # Screenshot 5: Social Preview Banner
            print("📸 Taking screenshot of social preview banner...")
            await page.set_viewport_size({"width": 1280, "height": 640})

            # Navigate to local HTML file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            social_template_path = f"file://{current_dir}/social-preview-template.html"

            await page.goto(social_template_path)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(1000)  # Allow fonts and layout to settle

            await page.screenshot(path="screenshots/social-preview-banner.png", full_page=True)
            print("✅ Saved: screenshots/social-preview-banner.png")

            print("\n🎉 Screenshots completed successfully!")
            print("Generated screenshots:")
            print("  - screenshots/screenshot_main_interface.png (dark mode, 1400x900)")
            print("  - screenshots/screenshot_import_export.png (dark mode, 1400x900)")
            print("  - screenshots/screenshot_audit_page.png (dark mode, 1400x900)")
            print("  - screenshots/screenshot_segment_view.png (dark mode, 1400x900)")
            print("  - screenshots/social-preview-banner.png (1280x640, GitHub social preview)")

            return True

        except Exception as e:
            print(f"❌ Error taking screenshots: {e}")
            return False
        finally:
            await browser.close()


async def main():
    """Main function to orchestrate the screenshot generation"""
    try:
        success = await generate_screenshots()
        if success:
            print("✅ Screenshot generation completed successfully!")
        else:
            print("❌ Screenshot generation failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
