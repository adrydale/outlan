# Outlan IPAM

A minimal IP Address Management (IPAM) system designed for small networks. Outlan IPAM provides a simple web interface for managing IP address blocks, subnets, and VLAN assignments with support for snapshots, audit logging, and data export capabilities.

Outlan does not manage individual IPs nor does it provide DNS or DHCP functions. The network-centric management approach is intended to provide network segment documentation primarily for home and lab environments.

Outlan was developed with the help of Cursor.

**Current Version**: 0.1.1

## Features

- **Network Block Management**: Organize IP addresses into logical blocks
- **Subnet Management**: Add and manage subnets within blocks with VLAN assignments (subnets cannot overlap within a block)
- **VLAN Support**: Assign VLAN IDs to subnets (1-4094 range) or use dash (-) for no VLAN
- **Snapshots**: Create point-in-time backups of your IPAM data
- **Audit Logging**: Track all changes and modifications
- **Data Export**: Export network data to CSV format
- **Responsive Web Interface**: Modern, themeable interface with light/dark/midnight themes
- **Docker Support**: Easy deployment using Docker and Docker Compose
- **REST API**: Programmatic access to IPAM data and operations

## Docker Deployment

### Quick Start with GitHub Container Registry (Recommended)

The easiest way to run Outlan is using the pre-built image from GitHub Container Registry:

```bash
# Pull and run the latest version
docker run -d \
  --name outlan \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config \
  -e TZ=America/Chicago \
  ghcr.io/adrydale/outlan:latest
```

### Quick Start with Docker Compose

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd outlan
   ```

2. Start the application using Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. Access the application at `http://localhost:5000`

4. Initialize the database by visiting the application URL and following the setup prompts.

### Available Docker Images

The following tags are available from GitHub Container Registry:

- `latest` - Latest stable release
- `develop` - Latest development build  
- `vX.Y.Z` - Specific version (e.g., `v0.1.16`)
- `vX.Y` - Latest patch version for minor version (e.g., `v0.1`)
- `vX` - Latest minor version for major version (e.g., `v0`)

### Basic Compose

Optional environment variables included in the next section.

```yaml
---
services:
  outlan:
    image: ghcr.io/adrydale/outlan:latest
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data # Must include to maintain DB across container rebuilds
      - ./logs:/app/logs # Optional
      - ./config:/app/config # Optional (default values can be used or you can use env vars
    environment:
      - FLASK_APP=app
```

### Environment Variables

The following environment variables can be configured to customize the application behavior.

**Note**: The order of priority for settings is: environment variables first, then settings.ini file, and finally default values.

| Variable | Default | Description |
|----------|---------|-------------|
| `TZ` | `Etc/GMT` | Timezone for logging and timestamps |
| `DB_PATH` | `/app/data/ipam.db` | Database file path |
| `DB_TIMEOUT` | `10` | Database connection timeout in seconds |
| `DEFAULT_SORT` | `VLAN` | Default sort field for network tables (Network, VLAN, or Name) |
| `THEME` | `dark` | UI theme (light, dark, or midnight) |
| `SNAPSHOT_LIMIT` | `200` | Maximum number of snapshots to keep |
| `SECRET_KEY` | `your-secret-key-change-in-production` | Flask secret key for CSRF protection |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_MAX_SIZE_MB` | `5` | Maximum size for log files in MB |
| `LOG_BACKUP_COUNT` | `5` | Number of rotated log files to keep |


### Configuration File

Alternatively, you can configure the application using the `/app/config/settings.ini` file. The file supports the same options as the environment variables listed above. Refer to [config/settings.ini.example](config/settings.ini.example) for an example. A `settings.ini` will be created by default if one doesn't exist.

### Volumes

The Docker Compose configuration mounts the following volumes:

- `./data:/app/data` - Database and application data
- `./logs:/app/logs` - Application logs
- `./config:/app/config` - Configuration files

## Basic Usage

### Adding Network Blocks

1. Navigate to the main IPAM interface
2. Enter a block name in the "New Block Name" field
3. Click "Add Block" to create a new network block

### Adding Subnets

1. Within a network block, use the subnet form at the bottom of the block
2. Enter the network in CIDR format (e.g., `192.168.1.0/24`)
3. Enter a VLAN ID (1-4094 range)
4. Enter a descriptive name for the subnet
5. Click "Add" to create the subnet

**Note**: To add a network with no VLAN tag, use a dash (`-`) in the VLAN field. This is useful for networks that don't require VLAN assignment. Networks with no VLAN will appear at the bottom when sorting by VLAN.

### Managing Subnets

- **Edit**: Click the "Edit" button next to a subnet to modify its properties
- **Delete**: Click the "Delete" button to remove a subnet
- **Export**: Use the "Export CSV" button to download subnet data

### Block Management

- **Rename**: Click "Rename" to modify block names
- **Delete**: Click "Delete Block" to remove entire blocks and their subnets
- **Reorder**: Use the up/down arrows to change block order
- **Collapse**: Click the collapse button to hide/show subnet details

## Snapshots

Snapshots provide point-in-time backups of your IPAM data, allowing you to restore the system to a previous state if needed.

Snapshots are automatically created on every CRUD (create, read, update, delete) action.

Snapshots can be reverted to by navigating to the Snapshot and Audit log page and clicking "Restore" on the appropriate snapshot. This can be undone by just restoring to the snapshot before the restore.

The system automatically maintains the configured snapshot limit (see environment varibles for the configurable limit).

## API

Outlan IPAM provides a basic REST API for programmatic access to IPAM data and operations.

### Available Endpoints

- `GET /api/health` - Health check endpoint
- `GET /api/version` - Application version information

## Security Considerations

- **Secret Key**: Change the default secret key in production environments
- **Network Access**: Consider firewall rules to restrict access to the IPAM interface
- **Backup**: Regularly backup the `/app/data` volume to preserve your IPAM data (snapshots are not backups)
- **Logs**: Monitor application logs (/app/logs) for events

## Security Warning: Secret Key

**Important:** If you change the secret key in production, all existing sessions may become invalid. Changing the security key *will not* affect the IPAM database. Always set the secret key securely using one of the following methods:

- Set the `SECRET_KEY` environment variable before starting the app.
- Set the `secret_key` value in `config/settings.ini` (ensure this file is not committed to version control).

The Flask secret key is used for session management and CSRF protection. It should be:
- At least 32 characters long
- Random (use letters, numbers, and symbols)


## Troubleshooting

### Common Issues

1. **Database Initialization**: Ensure the database is properly initialized on first run
2. **Permission Issues**: Verify Docker volumes have proper read/write permissions
3. **Port Conflicts**: Change the port mapping in `docker-compose.yml` if port 5000 is in use
4. **Timezone Issues**: Set the `TZ` environment variable to match your local timezone

### Logs

Application logs are stored in the `logs/` directory:
- `ipam.log` - General application logs
- `ipam_errors.log` - Error-level logs only

## Testing

Run the test suite:
```bash
pytest
```

**Note**: The current test suite includes basic functionality tests. Additional comprehensive tests are planned for future releases.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
