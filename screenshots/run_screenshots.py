#!/usr/bin/env python3
"""
Script to run the application with the correct database and generate screenshots.
"""

import subprocess
import sys
import time


def main():
    """Main function to run the application and generate screenshots"""

    print("🚀 Starting application with screenshots database...")
    print("📁 Database path: /app/data/ipam_screenshots.db (set in docker-compose.yml)")

    # Start the application in the background
    try:
        # Use screenshots docker-compose to start the app
        print("🐳 Starting containers with screenshots docker-compose...")
        subprocess.run(
            ["docker-compose", "-f", "screenshots/docker-compose.yml", "down"], check=True, capture_output=True
        )

        subprocess.run(["docker-compose", "-f", "screenshots/docker-compose.yml", "up", "-d", "--build"], check=True)

        print("⏳ Waiting for application to start...")
        time.sleep(10)  # Give the app time to start

        # Check if the app is running
        print("🔍 Checking if application is ready...")
        try:
            import requests

            response = requests.get("http://localhost:5000/", timeout=10)
            if response.status_code == 200:
                print("✅ Application is ready!")
            else:
                print(f"⚠️ Application responded with status {response.status_code}")
        except ImportError:
            print("⚠️ requests module not available, skipping health check")
        except Exception as e:
            print(f"⚠️ Could not check application health: {e}")

        # Run the screenshot generation
        print("📸 Starting screenshot generation...")
        subprocess.run([sys.executable, "screenshots/generate_screenshots.py"], check=True)

        print("✅ Screenshot generation completed!")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error running command: {e}")
        print(f"Command output: {e.stdout.decode() if e.stdout else 'No output'}")
        print(f"Command error: {e.stderr.decode() if e.stderr else 'No error'}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Interrupted by user")
        sys.exit(1)
    finally:
        print("🧹 Cleaning up...")
        try:
            subprocess.run(
                ["docker-compose", "-f", "screenshots/docker-compose.yml", "down"], check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            pass


if __name__ == "__main__":
    main()
