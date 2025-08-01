#!/usr/bin/env python3
"""
Screenshot generation script that uses the existing database.
Validates database has expected data and takes screenshots.
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
        expected_tables = {"network_blocks", "subnets", "change_log"}

        if not expected_tables.issubset(tables):
            print(f"❌ Missing tables. Expected: {expected_tables}, Found: {tables}")
            return False

        # Check network blocks
        cursor.execute("SELECT id, name FROM network_blocks ORDER BY position")
        blocks = cursor.fetchall()

        if len(blocks) != 2:
            print(f"❌ Expected 2 blocks, found {len(blocks)}")
            return False

        print(f"✅ Found {len(blocks)} blocks:")
        for block_id, name in blocks:
            print(f"   - {name} (ID: {block_id})")

        # Check subnets for each block
        for block_id, block_name in blocks:
            cursor.execute("SELECT COUNT(*) FROM subnets WHERE block_id = ?", (block_id,))
            subnet_count = cursor.fetchone()[0]
            print(f"   - {block_name}: {subnet_count} subnets")

        # Validate specific subnet counts
        cursor.execute("SELECT block_id, COUNT(*) FROM subnets GROUP BY block_id ORDER BY block_id")
        subnet_counts = cursor.fetchall()

        expected_counts = {1: 3, 2: 2}  # Block 1 should have 3 subnets, Block 2 should have 2
        for block_id, count in subnet_counts:
            if count != expected_counts.get(block_id, 0):
                print(f"❌ Block {block_id} has {count} subnets, expected {expected_counts.get(block_id, 0)}")
                return False

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


async def generate_screenshots():
    """Generate screenshots using the existing database"""

    # Get database path from environment or use local path
    db_path = os.environ.get("DB_PATH", "data/ipam_screenshots.db")

    # Validate database
    print(f"🔍 Validating database: {db_path}")

    if not validate_database(db_path):
        print("❌ Database validation failed!")
        return False

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Set viewport size
        await page.set_viewport_size({"width": 1200, "height": 800})

        try:
            # Wait for app to be ready
            print("🚀 Waiting for application to be ready...")
            if not await wait_for_app_ready(page):
                print("❌ Application failed to start")
                return False

            print("✅ Application is ready!")

            # Take screenshots for each theme
            themes = ["light", "dark", "midnight"]

            for theme in themes:
                print(f"📸 Taking screenshot for {theme} theme...")

                # Navigate to main page
                await page.goto("http://localhost:5000/")
                await page.wait_for_load_state("networkidle")

                # Set theme using JavaScript
                await page.evaluate(
                    f"""
                    localStorage.setItem('theme', '{theme}');
                    document.documentElement.setAttribute('data-theme', '{theme}');
                """
                )
                await page.wait_for_timeout(1000)

                # Take screenshot
                await page.screenshot(path=f"screenshots/main_interface_{theme}.png")
                print(f"✅ Saved: screenshots/main_interface_{theme}.png")

            # Take audit page screenshot in dark mode
            print("📸 Taking screenshot of audit page in dark mode...")
            await page.goto("http://localhost:5000/audit")
            await page.wait_for_load_state("networkidle")

            # Set dark theme for audit page
            await page.evaluate(
                """
                localStorage.setItem('theme', 'dark');
                document.documentElement.setAttribute('data-theme', 'dark');
            """
            )
            await page.wait_for_timeout(1000)

            # Try to collapse the "about snapshots" section
            try:
                snapshot_toggle = await page.query_selector("#snapshot-toggle")
                if snapshot_toggle:
                    print("🔽 Collapsing snapshot section...")
                    await snapshot_toggle.click()
                    await page.wait_for_timeout(1000)

                # Also try to hide the snapshot content directly
                snapshot_content = await page.query_selector("#snapshot-content")
                if snapshot_content:
                    await page.evaluate(
                        """
                        const content = document.getElementById('snapshot-content');
                        if (content) {
                            content.style.display = 'none';
                        }
                    """
                    )
                    await page.wait_for_timeout(500)

            except Exception as e:
                print(f"⚠️ Could not collapse sections: {e}")

            await page.screenshot(path="screenshots/audit_page.png")
            print("✅ Saved: screenshots/audit_page.png")

            print("\n🎉 Screenshots completed successfully!")
            print("Generated screenshots:")
            for theme in themes:
                print(f"  - screenshots/main_interface_{theme}.png")
            print("  - screenshots/audit_page.png")

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
