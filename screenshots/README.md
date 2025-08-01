# Screenshots

This folder contains screenshots of the Outlan IPAM application for the main README.md file.

## Generating Screenshots

To regenerate the screenshots, use the new automated script that validates the database and takes screenshots:

```bash
# Option 1: Run with Docker (recommended)
python3 screenshots/run_screenshots.py

# Option 2: Run manually if app is already running
python3 screenshots/generate_screenshots.py

# Option 3: Use screenshots docker-compose directly
docker-compose -f screenshots/docker-compose.yml up -d --build
python3 screenshots/generate_screenshots.py
docker-compose -f screenshots/docker-compose.yml down
```

Or use the main regeneration script from the project root:

```bash
./regenerate_screenshots.sh
```

### Requirements

- Python 3.7+
- Playwright (`pip install playwright`)
- Chromium browser (`playwright install chromium`)
- Outlan IPAM application running on `http://localhost:5000`

### What the Script Does

1. **Validates the database** to ensure it has the expected structure and data:
   - 2 network blocks: "Home Networks" (3 subnets) and "Lab Networks" (2 subnets)
   - Proper table structure with network_blocks, subnets, and change_log tables
2. **Takes screenshots** of the main IPAM interface for each theme (light, dark, midnight)
3. **Takes a screenshot** of the audit page in dark mode with the "about snapshots" section collapsed
4. **Generates the following files**:
   - `main_interface_light.png`
   - `main_interface_dark.png`
   - `main_interface_midnight.png`
   - `audit_page.png`

### Database Requirements

The script expects the database (`data/ipam_screenshots.db`) to contain:

#### Home Networks Block (ID: 1)
- **Main user**: `10.0.10.0/24` (VLAN 10)
- **Guests**: `10.0.30.0/24` (VLAN 30)
- **Device Management**: `10.0.99.0/24` (VLAN 99)

#### Lab Networks Block (ID: 2)
- **Servers**: `172.16.100.0/24` (VLAN 100)
- **IOT**: `172.16.66.0/24` (VLAN 600)

### Advantages of This Approach

- **Automated validation**: Checks database structure and data before taking screenshots
- **Dedicated docker-compose**: Uses `screenshots/docker-compose.yml` with specific database path
- **Environment variable support**: Uses `DB_PATH` to set the correct database
- **Docker integration**: Can run with Docker containers automatically
- **Fast execution**: No complex database setup or API interactions
- **Consistent results**: Uses predefined test data for reliable screenshots
- **Proper audit page**: Successfully collapses the "about snapshots" section

### Notes

- The script validates the database structure and data before taking screenshots
- Screenshots are taken at 1200x800 resolution
- The script automatically handles theme switching via JavaScript
- The audit page screenshot properly collapses the "about snapshots" section
- The script can run with Docker containers or with an already running application
- Environment variable `DB_PATH` is used to specify the database location
- For consistent screenshots, the script expects specific test data in the database
- Uses dedicated `screenshots/docker-compose.yml` with database path `/app/data/ipam_screenshots.db` 