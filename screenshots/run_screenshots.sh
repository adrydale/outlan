#!/bin/bash

# Screenshot generation script for Outlan IPAM
set -e

echo "📸 Outlan IPAM Screenshot Generation"
echo "=================================================="

# Check if we're in the project root
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found. Run this from the project root."
    exit 1
fi

# Check if screenshot database exists
if [ ! -f "data/ipam_screenshots.db" ]; then
    echo "❌ Error: Screenshot database not found at data/ipam_screenshots.db"
    exit 1
fi

cleanup() {
    echo "🧹 Cleaning up..."
    docker-compose down
    echo "✅ Cleanup complete!"
}

# Set trap to ensure cleanup runs on exit
trap cleanup EXIT

echo "🛑 Stopping any running containers..."
docker-compose down || true

echo "🚀 Starting containers with screenshot database..."
DB_PATH="/app/data/ipam_screenshots.db" docker-compose up -d --build

echo "⏳ Waiting for application to start..."
for i in {1..15}; do
    if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
        echo "✅ Application is ready!"
        break
    fi
    echo "   Attempt $i/15..."
    sleep 2
done

# Check if app is actually ready
if ! curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "❌ Application failed to start properly"
    exit 1
fi

echo "📸 Generating screenshots..."
python3 screenshots/generate_screenshots.py

echo ""
echo "🎉 Screenshot generation completed successfully!"
echo "Generated files:"
ls -la screenshots/screenshot_*.png 2>/dev/null || echo "No screenshots found"