#!/bin/bash
# Simple script to regenerate screenshots for the README using existing application data

echo "Regenerating screenshots for Outlan IPAM using existing application data..."

# Check if the application is running
if ! curl -s http://localhost:5000/api/health > /dev/null; then
    echo "Error: Outlan IPAM application is not running on http://localhost:5000"
    echo "Please start the application first with: docker-compose up -d"
    exit 1
fi

echo "Note: Make sure you have the desired test data in your application for consistent screenshots."
echo "See screenshots/README.md for the recommended test data structure."

# Check if playwright is installed
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "Installing playwright..."
    pip install playwright
    playwright install chromium
fi

# Run the screenshot generation script
echo "Generating screenshots..."
cd screenshots
python3 generate_screenshots.py

if [ $? -eq 0 ]; then
    echo "Screenshots generated successfully!"
    echo "New screenshots:"
    ls -la *.png
else
    echo "Error generating screenshots"
    exit 1
fi 